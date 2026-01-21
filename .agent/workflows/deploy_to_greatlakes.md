---
description: How to adapt and submit processing workflows to the Greatlakes Slurm cluster.
---

# Deploying to Greatlakes Cluster

This workflow outlines the steps to deploy and run the MOXIE signal processing pipeline on the Greatlakes Slurm cluster using the Open OnDemand Job Composer.

## 1. Script Adaptation

The Job Composer has specific constraints, primarily that it is difficult to pass dynamic command-line arguments to the main script entry point. Therefore, your shell scripts (`run_events.sh`, `run_processing.sh`) must be self-contained or use hardcoded paths for the cluster environment.

### Required Header Changes
Ensure your scripts include the necessary `#SBATCH` directives.

```bash
#!/bin/bash
#SBATCH --job-name=moxie_processing
#SBATCH --mail-user=your_email@umich.edu
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4GB
#SBATCH --time=10:00:00
#SBATCH --account=your_account
#SBATCH --partition=standard
#SBATCH --output=%x-%j.log
```

### Environment Setup
You must explicitly load modules and activate the virtual environment within the script.

```bash
module load python
source /home/unique_name/path/to/venv/bin/activate
```

### Hardcoded Paths (Job Composer Specific)
Since arguments aren't easily passed via the UI, define your roots at the top of the script:

```bash
# Cluster Paths
PROJECT_ROOT="/home/unique_name/moxie_codebase"
OUTPUT_ROOT="/nfs/turbo/path/to/output"
CATALOG_FILE="$PROJECT_ROOT/processing_catalog.csv"
```

## 2. Job Submission via Job Composer

1.  **Access**: Login to Greatlakes Open OnDemand.
2.  **Create Job**: Go to `Jobs` -> `Job Composer` -> `New Job` -> `From Default Template`.
3.  **Edit Script**:
    *   Click `Open Editor`.
    *   Replace the content with your local `workflows/run_processing.sh` (or `run_events.sh`) content.
    *   **Crucial**: Ensure the paths in the script point to the valid cluster locations (see above).
4.  **Edit Options** (Optional): You can modify Slurm options in the Right-Hand Panel, but putting them in the script (Step 1) is safer and more reproducible.
5.  **Submit**: Click the green `Submit` button.

## 3. Monitoring

*   **Status**: The Job Composer shows `Queued`, `Running`, or `Completed`.
*   **Logs**:
    *   STDOUT/STDERR are redirected to the file specified in `#SBATCH --output`.
    *   Click on the file in the File Manager to view logs live.

## 4. Updates & Syncing

When you make changes locally:
1.  **Push** changes to GitHub.
2.  **Pull** changes on the cluster (`git pull`).
3.  **Re-submit** the job in Job Composer (or create a new one if script logic changed significantly).
