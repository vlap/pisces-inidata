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
STAGE="${2:-all}"      # 'all' (default), 'stage1' (prepare sources), or 'stage2' (remap)

mkdir -p "${LOG_DIR}" "${SBATCH_DIR}"

echo "========================================================================"
echo " PISCES Inidata Batch Job Launcher (Nord4 / Slurm)"
echo " Target Grid:    ${GRID_NAME}"
echo " Active Preset:  ${PRESET}"
echo " Pipeline Stage: ${STAGE}"
echo " Account / QOS:  ${SLURM_ACCOUNT} / ${SLURM_PARTITION}"
echo " Submit mode:    ${SUBMIT}"
echo " Logs directory: ${LOG_DIR}"
echo " Jobs directory: ${SBATCH_DIR}"
echo "========================================================================"

# Template for individual sbatch worker jobs
read -r -d '' SBATCH_TEMPLATE << 'EOF' || true
#!/usr/bin/env bash

#SBATCH -A __ACCOUNT__
#SBATCH -q __PARTITION__
#SBATCH -n 1
#SBATCH -c __CPUS__
#SBATCH --mem=__MEM__
#SBATCH -t __TIME__
#SBATCH -J pisces.__JOBNAME__
#SBATCH -o __LOG_DIR__/slurm-pisces.__JOBNAME__-%j.out
#SBATCH -e __LOG_DIR__/slurm-pisces.__JOBNAME__-%j.err

set -e
echo "Starting job pisces.__JOBNAME__ on $(hostname) at $(date)"
export GRID_NAME="__GRID_NAME__"
export DOMAIN_BASE_DIR="__DOMAIN_BASE_DIR__"
export PRESET="__PRESET__"
export INIDATA_PRESET="__PRESET__"
export PISCES_WORKSPACE="__WORKSPACE__"
export PISCES_CONFIG="__PISCES_CONFIG__"
export OUTPUT_DIR="__OUTPUT_DIR__"
export SLURM_CPUS_PER_TASK="__CPUS__"
eval "__MODULE_LOAD__"

__COMMAND__

echo "Finished job pisces.__JOBNAME__ at $(date)"
EOF

submit_job() {
    local jobname="$1"
    local command="$2"
    local dependency="${3:-}"
    local script_path="${SBATCH_DIR}/sbatch_${jobname}.sh"

    local p_cfg="${PISCES_CONFIG:-${CONFIG_FILE:-}}"
    local script_content="${SBATCH_TEMPLATE}"
    script_content="${script_content//__ACCOUNT__/${SLURM_ACCOUNT}}"
    script_content="${script_content//__PARTITION__/${SLURM_PARTITION}}"
    script_content="${script_content//__CPUS__/${SLURM_CPUS_PER_TASK}}"
    script_content="${script_content//__MEM__/${SLURM_MEM}}"
    script_content="${script_content//__TIME__/${SLURM_TIME}}"
    script_content="${script_content//__JOBNAME__/${jobname}}"
    script_content="${script_content//__LOG_DIR__/${LOG_DIR}}"
    script_content="${script_content//__GRID_NAME__/${GRID_NAME}}"
    script_content="${script_content//__DOMAIN_BASE_DIR__/${DOMAIN_BASE_DIR}}"
    script_content="${script_content//__PRESET__/${PRESET}}"
    script_content="${script_content//__WORKSPACE__/${WORKSPACE}}"
    script_content="${script_content//__PISCES_CONFIG__/${p_cfg}}"
    script_content="${script_content//__OUTPUT_DIR__/${OUTPUT_DIR}}"
    script_content="${script_content//__MODULE_LOAD__/${MODULE_LOAD_CMD}}"
    script_content="${script_content//__COMMAND__/${command}}"

    echo "${script_content}" > "${script_path}"
    chmod +x "${script_path}"

    local job_id=""
    if [ "${SUBMIT}" = "submit" ]; then
        if command -v sbatch >/dev/null 2>&1; then
            local sbatch_cmd=(sbatch)
            if [ -n "${dependency}" ]; then
                sbatch_cmd+=(--dependency="afterok:${dependency}")
            fi
            sbatch_cmd+=("${script_path}")
            echo "Submitting: ${sbatch_cmd[*]}"
            local sbatch_out
            sbatch_out="$("${sbatch_cmd[@]}")"
            echo "${sbatch_out}"
            job_id="$(echo "${sbatch_out}" | awk '{print $NF}')"
        else
            echo "sbatch command not found (running locally or on non-Slurm node): ${script_path}"
            bash "${script_path}"
        fi
    else
        echo "[DRY-RUN] Created: ${script_path}"
        if [ -n "${dependency}" ]; then
            echo "[DRY-RUN] Would submit with dependency: afterok:${dependency}"
        fi
    fi
    echo "${job_id}"
}

# ------------------------------------------------------------------------------
# 1. Step 1: Target Grid & Weights Generation
# ------------------------------------------------------------------------------
WEIGHTS_JOB_ID=""
if [ "${STAGE}" = "all" ] || [ "${STAGE}" = "stage2" ] || [ "${STAGE}" = "remap" ]; then
    echo "--- [1/6] Checking / Generating Target Grid and Remapping Weights ---"
    TARGET_WEIGHTS="${WEIGHTS_DIR}/weights_r360x180_to_${GRID_NAME}_bilin.nc"
    if [ -f "${TARGET_WEIGHTS}" ] && [ -s "${TARGET_WEIGHTS}" ]; then
        echo "Target weights already exist at ${TARGET_WEIGHTS}. Skipping generation."
    elif [ "${GRID_NAME}" = "eORCA025" ] && command -v sbatch >/dev/null 2>&1 && [ "${SUBMIT}" = "submit" ]; then
        echo "eORCA025 target detected: Submitting weights generation as batch job (--mem=64G)..."
        WEIGHTS_JOB_ID=$(submit_job "gen_weights" "bash ${SCRIPT_DIR}/gen_grid_and_weights.sh")
        echo "Weights generation submitted with Job ID: ${WEIGHTS_JOB_ID}"
    else
        if [ "${SUBMIT}" = "submit" ]; then
            bash "${SCRIPT_DIR}/gen_grid_and_weights.sh"
        else
            echo "[DRY-RUN] Would run: bash ${SCRIPT_DIR}/gen_grid_and_weights.sh"
            if [ "${GRID_NAME}" = "eORCA025" ]; then
                WEIGHTS_JOB_ID="DRY_RUN_WEIGHTS_JOB_ID"
            fi
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 2. Step 2: Source Standardization (Stage 1: Grid-Agnostic ETL)
# ------------------------------------------------------------------------------
if [ "${STAGE}" = "all" ] || [ "${STAGE}" = "stage1" ] || [ "${STAGE}" = "prepare" ]; then
    echo "--- [2/6] Checking / Standardizing Source Datasets (Stage 1 ETL) ---"
    if [ "${SUBMIT}" = "submit" ]; then
        bash "${SCRIPT_DIR}/prepare_standard_sources.sh" all
    else
        echo "[DRY-RUN] Would run: bash ${SCRIPT_DIR}/prepare_standard_sources.sh all"
    fi
    if [ "${STAGE}" = "stage1" ] || [ "${STAGE}" = "prepare" ]; then
        echo "Stage 1 preparation completed. Exiting as requested."
        exit 0
    fi
fi

# ------------------------------------------------------------------------------
# 3. Step 3: Submit 3D Tracers in Parallel (Stage 2 Remap)
# ------------------------------------------------------------------------------
echo "--- [3/6] Submitting 3D Tracer Remapping Jobs ---"
for tracer in "${TRACERS_3D[@]}"; do
    job_cmd="bash ${SCRIPT_DIR}/remap_field.sh ${tracer} 3d"
    submit_job "tracer_${tracer}" "${job_cmd}" "${WEIGHTS_JOB_ID}" >/dev/null
done

# ------------------------------------------------------------------------------
# 4. Step 4: Submit Rivers Remapping Job (Stage 2 Remap)
# ------------------------------------------------------------------------------
echo "--- [4/6] Submitting River Nutrient Remapping Job ---"
job_cmd="bash ${SCRIPT_DIR}/remap_field.sh river river"
submit_job "rivers" "${job_cmd}" "${WEIGHTS_JOB_ID}" >/dev/null

# ------------------------------------------------------------------------------
# 5. Step 5: Submit Surface Forcings Jobs (Stage 2 Remap)
# ------------------------------------------------------------------------------
echo "--- [5/6] Submitting Surface Forcing Remapping Jobs ---"
submit_job "surf_dust" "bash ${SCRIPT_DIR}/remap_field.sh dust 2d" "${WEIGHTS_JOB_ID}" >/dev/null
submit_job "surf_ndep" "bash ${SCRIPT_DIR}/remap_field.sh ndep 2d" "${WEIGHTS_JOB_ID}" >/dev/null
submit_job "surf_par"  "bash ${SCRIPT_DIR}/remap_field.sh par 2d"  "${WEIGHTS_JOB_ID}" >/dev/null

# ------------------------------------------------------------------------------
# 6. Step 6: Submit Bathymetric Shelf & Hydrothermal Jobs (Stage 2 Remap)
# ------------------------------------------------------------------------------
echo "--- [6/6] Submitting Bathy & Hydrothermal Remapping Jobs ---"
submit_job "bathy"   "bash ${SCRIPT_DIR}/remap_field.sh bathy bathy"     "${WEIGHTS_JOB_ID}" >/dev/null
submit_job "hydrofe" "bash ${SCRIPT_DIR}/remap_field.sh hydrofe hydrofe" "${WEIGHTS_JOB_ID}" >/dev/null

echo "========================================================================"
echo " All batch jobs generated and submitted successfully!"
echo " Track your jobs with: squeue -u \$USER"
echo " Logs written to: ${LOG_DIR}"
echo " Final output will be in: ${OUTPUT_DIR}"
echo "========================================================================"
