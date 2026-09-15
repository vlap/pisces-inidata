# HPC Execution Guide

`pisces-inidata` is designed to run efficiently both on local workstations and on high-performance computing (HPC) clusters such as **MareNostrum 5 (MN5)** and **Nord3** at the Barcelona Supercomputing Center (BSC).

---

## 1. Environment & Module Loading (BSC MN5 & Nord3)

On BSC clusters using LMOD/Tcl environment modules, load the pre-compiled CDO, NCO, and Python modules:

```bash
# Load compilers and netCDF tooling
module load cdo
module load nco
module load python/3.11

# Verify tools
cdo --version
ncks --version
python3 --version
```

If using a custom virtual environment or Conda on HPC:
```bash
conda activate /gpfs/projects/bsc32/repository/apps/conda_envs/ecearth4_env
```

---

## 2. Slurm Batch Job Submission

For high-resolution target grids (e.g. `eORCA1` or `eORCA025`), submitting as a Slurm batch job is recommended:

```bash
#!/bin/bash
#SBATCH --job-name=pisces_inidata
#SBATCH --output=pisces_inidata_%j.log
#SBATCH --error=pisces_inidata_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --qos=gp_debug
#SBATCH --account=bsc32

set -e

module load cdo nco python/3.11

# Set openmp threads for CDO
export OMP_NUM_THREADS=8

# Execute pipeline
bash scripts/launcher_pisces_inidata.sh --orca ORCA2
```

Submit with:
```bash
sbatch run_inidata.slurm
```

---

## 3. Integration with Autosubmit (EC-Earth4)

To integrate `pisces-inidata` into an automated EC-Earth4 workflow managed by **Autosubmit**:

1. Define an inidata task in your Autosubmit experiment `jobs_expid.conf`:
```ini
[INIDATA_PISCES]
FILE = templates/inidata_pisces.sh
PLATFORM = MARENOSTRUM4
WALLCLOCK = 01:30
CPUS = 8
```

2. In `templates/inidata_pisces.sh`, call the launcher script:
```bash
export ROOT_EXP=%EXPID%
source %PROJDIR%/scripts/config.sh
bash %PROJDIR%/scripts/launcher_pisces_inidata.sh --orca %OCEAN_RESOL%
```
