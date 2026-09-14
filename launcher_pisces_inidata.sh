#!/usr/bin/env bash
# ==============================================================================
# launcher_pisces_inidata.sh
# Generates and submits small, parallel sbatch jobs on Nord4 to format all
# PISCES inidata components simultaneously.
# Follows the architecture and conventions of wmo2025_gcp launchers.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

SUBMIT="${1:-submit}" # 'submit' (default) or 'dry-run'

mkdir -p "${LOG_DIR}" "${WORK_DIR}/sbatch_scripts"

echo "========================================================================"
echo " PISCES Inidata Batch Job Launcher (Nord4 / Slurm)"
echo " Target Grid:    ${GRID_NAME}"
echo " Account / QOS:  ${SLURM_ACCOUNT} / ${SLURM_PARTITION}"
echo " Submit mode:    ${SUBMIT}"
echo " Logs directory: ${LOG_DIR}"
echo "========================================================================"

# Template for individual sbatch worker jobs
read -r -d '' SBATCH_TEMPLATE << 'EOF' || true
#!/usr/bin/env bash

#SBATCH -A __ACCOUNT__
#SBATCH -q __PARTITION__
#SBATCH -n 1
#SBATCH -c __CPUS__
#SBATCH -t __TIME__
#SBATCH -J pisces.__JOBNAME__
#SBATCH -o __LOG_DIR__/slurm-pisces.__JOBNAME__-%j.out
#SBATCH -e __LOG_DIR__/slurm-pisces.__JOBNAME__-%j.err

set -e
echo "Starting job pisces.__JOBNAME__ on $(hostname) at $(date)"
eval "__MODULE_LOAD__"

__COMMAND__

echo "Finished job pisces.__JOBNAME__ at $(date)"
EOF

submit_job() {
    local jobname="$1"
    local command="$2"
    local script_path="${WORK_DIR}/sbatch_scripts/sbatch_${jobname}.sh"

    local script_content="${SBATCH_TEMPLATE}"
    script_content="${script_content//__ACCOUNT__/${SLURM_ACCOUNT}}"
    script_content="${script_content//__PARTITION__/${SLURM_PARTITION}}"
    script_content="${script_content//__CPUS__/${SLURM_CPUS_PER_TASK}}"
    script_content="${script_content//__TIME__/${SLURM_TIME}}"
    script_content="${script_content//__JOBNAME__/${jobname}}"
    script_content="${script_content//__LOG_DIR__/${LOG_DIR}}"
    script_content="${script_content//__MODULE_LOAD__/${MODULE_LOAD_CMD}}"
    script_content="${script_content//__COMMAND__/${command}}"

    echo "${script_content}" > "${script_path}"
    chmod +x "${script_path}"

    if [ "${SUBMIT}" = "submit" ]; then
        if command -v sbatch >/dev/null 2>&1; then
            echo "Submitting: sbatch ${script_path}"
            sbatch "${script_path}"
        else
            echo "sbatch command not found (running locally or on non-Slurm node): ${script_path}"
            bash "${script_path}"
        fi
    else
        echo "[DRY-RUN] Created: ${script_path}"
    fi
}

# ------------------------------------------------------------------------------
# 1. Step 1: Target Grid & Weights Generation
# ------------------------------------------------------------------------------
echo "--- [1/5] Submitting Grid and Remapping Weights Job ---"
job_cmd="bash ${SCRIPT_DIR}/gen_grid_and_weights.sh"
submit_job "gen_grid_weights" "${job_cmd}"

# ------------------------------------------------------------------------------
# 2. Step 2: Submit 3D Tracers in Parallel
# ------------------------------------------------------------------------------
echo "--- [2/5] Submitting 3D Tracer Jobs ---"
for tracer in "${TRACERS_3D[@]}"; do
    job_cmd="bash ${SCRIPT_DIR}/format_tracers_3d.sh ${tracer} offline"
    submit_job "tracer_${tracer}" "${job_cmd}"
done

# ------------------------------------------------------------------------------
# 3. Step 3: Submit Rivers Conservative Remapping Job
# ------------------------------------------------------------------------------
echo "--- [3/5] Submitting River Nutrient Job ---"
job_cmd="bash ${SCRIPT_DIR}/format_rivers.sh"
submit_job "rivers" "${job_cmd}"

# ------------------------------------------------------------------------------
# 4. Step 4: Submit Surface Forcings Jobs (Dust, N-dep, PAR)
# ------------------------------------------------------------------------------
echo "--- [4/5] Submitting Surface Forcing Jobs ---"
submit_job "surf_dust" "bash ${SCRIPT_DIR}/format_surface_forcings.sh dust"
submit_job "surf_ndep" "bash ${SCRIPT_DIR}/format_surface_forcings.sh ndep"
submit_job "surf_par"  "bash ${SCRIPT_DIR}/format_surface_forcings.sh par"

# ------------------------------------------------------------------------------
# 5. Step 5: Submit Bathymetric Shelf & Hydrothermal Iron Jobs
# ------------------------------------------------------------------------------
echo "--- [5/5] Submitting Bathy & Hydrothermal Jobs ---"
submit_job "bathy"   "bash ${SCRIPT_DIR}/format_bathy_hydrofe.sh bathy"
submit_job "hydrofe" "bash ${SCRIPT_DIR}/format_bathy_hydrofe.sh hydrofe"

echo "========================================================================"
echo " All batch jobs generated and submitted successfully!"
echo " Track your jobs with: squeue -u \$USER"
echo " Logs written to: ${LOG_DIR}"
echo " Final output will be in: ${OUTPUT_DIR}"
echo "========================================================================"
