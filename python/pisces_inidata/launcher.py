"""
Pipeline Launcher & Slurm Job Array Generator for PISCES Inidata.
Pure Python module replacing scripts/launcher_pisces_inidata.sh.

Orchestrates execution of PISCES initial conditions generation across platforms:
  - Local Workstation: Sequential or ProcessPoolExecutor execution.
  - HPC Clusters (Nord4, MN5, Slurm): Generates and submits clean Slurm Job Arrays (#SBATCH --array=0-14%4).
"""

import os
import shutil
import subprocess
from typing import Optional, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

from pisces_inidata.platforms import load_platform_config
from pisces_inidata.weights import ensure_grid_and_weights
from pisces_inidata.etl import standardize_all_sources
from pisces_inidata.remap import remap_field, get_output_dir


PIPELINE_FIELDS = [
    "NO3", "PO4", "Si", "O2", "TALK", "TDIC", "PiDIC", "DOC", "Fer",
    "dust", "ndep", "par", "bathy", "hydrofe", "river"
]


def generate_slurm_array_script(
    grid_name: str,
    pack: str = "ece4",
    preset: Optional[str] = None,
    convention: str = "nemo4_ece4",
    platform_name: Optional[str] = None,
    jobs_dir: Optional[str] = None,
    log_dir: Optional[str] = None,
    concurrency_limit: int = 4,
    custom_slurm: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates a Slurm Job Array script (.sbatch) to remap all 15 PISCES fields concurrently.
    Returns path to the generated script.
    """
    active_pack = preset if preset else pack
    plat_cfg = load_platform_config(platform_name)
    slurm_cfg = plat_cfg.get("slurm", {})
    if custom_slurm:
        slurm_cfg.update(custom_slurm)

    account = slurm_cfg.get("account") or os.environ.get("SLURM_ACCOUNT", "")
    partition = slurm_cfg.get("partition") or os.environ.get("SLURM_PARTITION", "")
    cpus = slurm_cfg.get("cpus_per_task", 4)
    mem = slurm_cfg.get("mem", "16G")
    walltime = slurm_cfg.get("time", "01:00:00")
    module_load = plat_cfg.get("module_load", "")

    workspace = os.environ.get("PISCES_WORKSPACE")
    effective_jobs_dir = jobs_dir or (
        os.path.join(workspace, "jobs") if workspace else os.path.join(os.getcwd(), "jobs")
    )
    effective_log_dir = log_dir or (
        os.path.join(workspace, "logs") if workspace else os.path.join(os.getcwd(), "logs")
    )
    os.makedirs(effective_jobs_dir, exist_ok=True)
    os.makedirs(effective_log_dir, exist_ok=True)

    script_path = os.path.join(effective_jobs_dir, f"remap_array_{grid_name}.sbatch")
    max_idx = len(PIPELINE_FIELDS) - 1
    fields_str = " ".join(PIPELINE_FIELDS)

    account_header = f"#SBATCH -A {account}" if account else "# (no SLURM account specified)"
    qos_header = f"#SBATCH -q {partition}" if partition else "# (no SLURM partition/qos specified)"
    module_block = f"eval '{module_load}'" if module_load else "# (no environment module load needed)"

    content = f"""#!/usr/bin/env bash
# ==============================================================================
# Slurm Job Array: Remap all PISCES inidata fields to {grid_name}
# Generated automatically by pisces-inidata produce
# ==============================================================================
{account_header}
{qos_header}
#SBATCH -n 1
#SBATCH -c {cpus}
#SBATCH --mem={mem}
#SBATCH -t {walltime}
#SBATCH -J pisces.remap.{grid_name}
#SBATCH --array=0-{max_idx}%{concurrency_limit}
#SBATCH -o {effective_log_dir}/slurm-pisces.remap-{grid_name}-%A_%a.out
#SBATCH -e {effective_log_dir}/slurm-pisces.remap-{grid_name}-%A_%a.err

set -euo pipefail
echo "Starting PISCES remap task $SLURM_ARRAY_TASK_ID on $(hostname) at $(date)"
{module_block}

FIELDS=({fields_str})
VAR="${{FIELDS[$SLURM_ARRAY_TASK_ID]}}"

echo "Field: $VAR | Grid: {grid_name} | Pack: {active_pack} | Convention: {convention}"
pisces-inidata remap --grid "{grid_name}" --variable "$VAR" --pack "{active_pack}" --convention "{convention}"

echo "Finished task $SLURM_ARRAY_TASK_ID ($VAR) at $(date)"
"""

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(script_path, 0o755)

    return script_path


def _remap_worker(args_dict: Dict[str, Any]) -> str:
    """Helper worker function for ProcessPoolExecutor."""
    return remap_field(**args_dict)


def launch_pipeline(
    grid_name: str,
    pack: str = "ece4",
    preset: Optional[str] = None,
    convention: str = "nemo4_ece4",
    stage: str = "all",
    force: bool = False,
    dry_run: bool = False,
    executor: str = "auto",
    jobs: int = 1,
    no_submit: bool = False,
    platform_name: Optional[str] = None,
    domain_dir: Optional[str] = None,
    weights_dir: Optional[str] = None,
    raw_dir: Optional[str] = None,
    out_dir: Optional[str] = None,
    jobs_dir: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entrypoint for pisces-inidata produce.
    Manages grid & weights generation, Stage 1 ETL, and Stage 2 target remapping.
    """
    active_pack = preset if preset is not None else pack
    print("========================================================================")
    print(" PISCES Inidata Production Pipeline")
    print(f" Target Grid:     {grid_name}")
    print(f" Source Pack:     {active_pack}")
    print(f" Convention:      {convention}")
    print(f" Pipeline Stage:  {stage}")
    print(f" Executor Mode:   {executor} (workers={jobs})")
    print(f" Dry Run:         {dry_run}")
    print("========================================================================")

    results: Dict[str, Any] = {
        "grid": grid_name,
        "pack": active_pack,
        "preset": active_pack,
        "stage": stage,
        "submitted_job_id": None,
        "remapped_files": [],
    }

    # Step 1: Ensure Target Grid and Remap Weights
    if stage in ("weights", "gen-weights", "stage2", "all"):
        print("\n--- [Step 1/3] Ensuring Target Grid and Remap Weights ---")
        if dry_run:
            print(f"[DRY-RUN] Would ensure grid coordinates and weights for {grid_name}")
        else:
            w_info = ensure_grid_and_weights(
                grid_name=grid_name,
                domain_dir=domain_dir,
                weights_dir=weights_dir,
                raw_dir=raw_dir,
                force=force,
            )
            print(f"Target grid:    {w_info['target_grid_nc']}")
            print(f"Target weights: {w_info['weights_bilin_nc']}")

        if stage in ("weights", "gen-weights"):
            print("Weights generation stage complete. Exiting.")
            return results

    # Step 2: Source Standardization (Stage 1 Grid-Agnostic ETL)
    if stage in ("stage1", "prepare", "all"):
        print("\n--- [Step 2/3] Source Standardization (Stage 1 ETL) ---")
        if dry_run:
            print(f"[DRY-RUN] Would run Stage 1 ETL standardization for all fields (pack={active_pack})")
        else:
            std_files = standardize_all_sources(
                pack=active_pack,
                force=force,
                raw_dir=raw_dir,
            )
            print(f"Standardized {len(std_files)} source files successfully.")

        if stage in ("stage1", "prepare"):
            print("Stage 1 preparation complete. Exiting.")
            return results

    # Step 3: Target Grid Remapping (Stage 2)
    print("\n--- [Step 3/3] Target Grid Remapping (Stage 2) ---")
    is_slurm_available = bool(shutil.which("sbatch"))
    should_use_slurm = (executor == "slurm") or (executor == "auto" and is_slurm_available)

    if should_use_slurm:
        script_path = generate_slurm_array_script(
            grid_name=grid_name,
            pack=active_pack,
            convention=convention,
            platform_name=platform_name,
            jobs_dir=jobs_dir,
            log_dir=log_dir,
            concurrency_limit=max(jobs, 4),
        )
        print(f"Generated Slurm Job Array script: {script_path}")

        if dry_run or no_submit:
            print(f"[{'DRY-RUN' if dry_run else 'NO-SUBMIT'}] Would submit job array: sbatch {script_path}")
            results["submitted_job_id"] = "DRY_RUN_ARRAY_ID"
            return results

        print(f"Submitting Slurm Job Array: sbatch {script_path} ...")
        sub_res = subprocess.run(["sbatch", script_path], capture_output=True, text=True, check=True)
        job_id = sub_res.stdout.strip().split()[-1]
        print(f"Submitted Slurm Job Array successfully: Job ID {job_id}")
        print(f"Track progress with: squeue -j {job_id}")
        results["submitted_job_id"] = job_id
        return results

    # Local / Workstation Execution
    if dry_run:
        for field in PIPELINE_FIELDS:
            print(f"[DRY-RUN] Would remap field '{field}' to grid '{grid_name}'")
        return results

    if jobs > 1:
        print(f"Executing {len(PIPELINE_FIELDS)} fields concurrently with {jobs} workers...")
        tasks = []
        for field in PIPELINE_FIELDS:
            task_kwargs = {
                "var_name": field,
                "grid_name": grid_name,
                "pack": active_pack,
                "convention": convention,
                "force": force,
                "domain_dir": domain_dir,
                "weights_dir": weights_dir,
                "raw_dir": raw_dir,
                "out_dir": out_dir,
            }
            tasks.append(task_kwargs)

        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(_remap_worker, t): t["var_name"] for t in tasks}
            for fut in as_completed(futures):
                var = futures[fut]
                try:
                    res_path = fut.result()
                    results["remapped_files"].append(res_path)
                except Exception as exc:
                    print(f"ERROR: Worker failed for variable '{var}': {exc}")
                    raise
    else:
        print("Executing 15 fields sequentially...")
        for field in PIPELINE_FIELDS:
            res_path = remap_field(
                var_name=field,
                grid_name=grid_name,
                pack=active_pack,
                convention=convention,
                force=force,
                domain_dir=domain_dir,
                weights_dir=weights_dir,
                raw_dir=raw_dir,
                out_dir=out_dir,
            )
            results["remapped_files"].append(res_path)

    print("\n========================================================================")
    print(f" Pipeline execution completed successfully for {grid_name}!")
    print(f" Output files located in: {get_output_dir(grid_name, out_dir)}")
    print("========================================================================")
    return results
