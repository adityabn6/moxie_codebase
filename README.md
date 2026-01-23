# MOXIE Signal Processing Pipeline

This repository contains the signal processing codebase for the MOXIE study. It provides a modular, sequential pipeline for processing physiological data from **Acqknowledge** (Biopac) and **Hexoskin** devices.

## 📂 Repository Structure

```
moxie_codebase/
├── processing/              # Core Python scripts for signal analysis
│   ├── extract_events.py    # Extracts digital markers from .acq files
│   ├── process_acq_*.py     # Acqknowledge processing (ECG, EDA, RSP, BP, EMG)
│   └── process_hexoskin_*.py# Hexoskin processing (ECG, RSP)
│
├── features_extraction/     # Feature extraction scripts for RL Analysis
│   └── features_acq_*.py    # Extract State (ECG/EDA), Action (RSP), Reward (BP) features
│
├── workflows/               # Bash automation scripts (Pipeline Layers)
│   ├── run_events.sh        # Layer 1: Extraction & Directory Setup
│   ├── run_processing.sh    # Layer 2: Signal Processing (Slurm Array compatible)
│   └── run_features.sh      # Layer 3: Feature Extraction
│
├── verification/            # Quality Control & Verification tools
│   └── verify_*.py          # Scripts to generate QC plots and stats
│
└── utils/                   # Helper utilities
    └── generate_catalog.py  # Generates the 'processing_catalog.csv'
```

## 🛠️ Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-org/moxie_codebase.git
    cd moxie_codebase
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Cluster Execution (Greatlakes)
The pipeline is designed to run on the University of Michigan Greatlakes cluster using the Open OnDemand Job Composer. It operates in two sequential layers.

### 1. Configuration
The workflow paths are defined in `workflows/cluster_config.sh`.
*   **PROJECT_ROOT**: `/home/adityabn/Projects/moxie_codebase`
*   **VENV_PATH**: `$PROJECT_ROOT/.venv`

### 2. Execution Steps
Do NOT run python scripts manually. Use the Bash workflows.

**Step 1: Generate Catalog (One-time)**
Ensure `processing_catalog.csv` exists in the project root. If not, run:
```bash
python utils/generate_catalog.py
 ```

**Step 2: Layer 1 - Event Extraction**
1.  Open OnDemand **Job Composer**.
2.  Create a new job and upload `workflows/run_events.sh`.
3.  Click **Submit**.
    *   *What it does:* Scans all Acqknowledge files, extracts event markers, and creates the folder structure in `Processed_Data/`.

**Step 3: Layer 2 - Signal Processing**
1.  Wait for Layer 1 to finish.
2.  Create a new job and upload `workflows/run_processing.sh`.
3.  Click **Submit**.
    *   *What it does:* Reads `processing_catalog.csv` and launches a parallel Array Job (up to 200 tasks) to process every modality (ECG, EDA, RSP, etc.) independently.
    *   *Output:* CSV files are saved to `Processed_Data/<PID>/<Visit>/`.

**Step 4: Layer 3 - Feature Extraction**
1.  Wait for Layer 2 to finish.
2.  Create a new job and upload `workflows/run_features.sh`.
3.  Click **Submit**.
    *   *What it does:* extracts windowed (1s) and event-based features from the processed signals.
    *   *Output:* CSV feature files are saved to `Processed_Data/<PID>/<Visit>/`.

**Step 5: Analysis Data Collection**
To gather all feature CSVs into a single directory for analysis (e.g., RL training):
```bash
python utils/collect_features.py <Source_Dir> <Dest_Dir>
# Example:
# python utils/collect_features.py Processed_Data Analysis_Ready
```

### 3. Monitoring
 *   Check the `.log` files in your job folder for progress.
 *   If a row in the catalog is empty (job index > number of files), the job will exit successfully with "End of Catalog".

## 📊 Output Format
Data is saved to `<Output_Root>/<Participant_ID>/<Visit_Type>/`:
*   `events.csv`: Extracted event markers and timestamps.
*   `processed_ecg_*.csv`: Cleaned ECG, R-peaks, Heart Rate.
*   `processed_eda_*.csv`: Phasic/Tonic components, SCR peaks.
*   `processed_rsp_*.csv`: Respiration rate, clean signals (Thoracic/Abdominal).
*   `processed_bp_*.csv`: Systolic/Diastolic peaks, BP rate.
*   `processed_emg_*.csv`: EMG amplitude envelopes, activity bursts.
*   `features_*_*.csv`: Extracted feature sets (Event-based and Windowed).

## ✅ Verification
To verify the quality of processed data, use the scripts in `verification/`.
Example:
```bash
python verification/verify_ecg_quality.py <Processed_File_Path>
```
Generates a visualization plot and statistics summary.

## Supported Modalities
*   **Acqknowledge**: ECG, EDA, Respiration, Blood Pressure, EMG
*   **Hexoskin**: ECG, Respiration (Thoracic, Abdominal)
