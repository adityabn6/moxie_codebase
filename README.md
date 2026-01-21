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
├── workflows/               # Bash automation scripts (Pipeline Layers)
│   ├── run_events.sh        # Layer 1: Extraction & Directory Setup
│   └── run_processing.sh    # Layer 2: Signal Processing (Slurm Array compatible)
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
40: 
41: The pipeline is designed to run on the University of Michigan Greatlakes cluster using the Open OnDemand Job Composer. It operates in two sequential layers.
42: 
43: ### 1. Configuration
44: The workflow paths are defined in `workflows/cluster_config.sh`.
45: *   **PROJECT_ROOT**: `/home/adityabn/Projects/moxie_codebase`
46: *   **VENV_PATH**: `$PROJECT_ROOT/.venv`
47: 
48: ### 2. Execution Steps
49: Do NOT run python scripts manually. Use the Bash workflows.
50: 
51: **Step 1: Generate Catalog (One-time)**
52: Ensure `processing_catalog.csv` exists in the project root. If not, run:
53: ```bash
54: python utils/generate_catalog.py
55: ```
56: 
57: **Step 2: Layer 1 - Event Extraction**
58: 1.  Open OnDemand **Job Composer**.
59: 2.  Create a new job and upload `workflows/run_events.sh`.
60: 3.  Click **Submit**.
61:     *   *What it does:* Scans all Acqknowledge files, extracts event markers, and creates the folder structure in `Processed_Data/`.
62: 
63: **Step 3: Layer 2 - Signal Processing**
64: 1.  Wait for Layer 1 to finish.
65: 2.  Create a new job and upload `workflows/run_processing.sh`.
66: 3.  Click **Submit**.
67:     *   *What it does:* Reads `processing_catalog.csv` and launches a parallel Array Job (up to 200 tasks) to process every modality (ECG, EDA, RSP, etc.) independently.
68:     *   *Output:* CSV files are saved to `Processed_Data/<PID>/<Visit>/`.
69: 
70: ### 3. Monitoring
71: *   Check the `.log` files in your job folder for progress.
72: *   If a row in the catalog is empty (job index > number of files), the job will exit successfully with "End of Catalog".

## 📊 Output Format
Data is saved to `<Output_Root>/<Participant_ID>/<Visit_Type>/`:
*   `events.csv`: Extracted event markers and timestamps.
*   `processed_ecg_*.csv`: Cleaned ECG, R-peaks, Heart Rate.
*   `processed_eda_*.csv`: Phasic/Tonic components, SCR peaks.
*   `processed_rsp_*.csv`: Respiration rate, clean signals (Thoracic/Abdominal).
*   `processed_bp_*.csv`: Systolic/Diastolic peaks, BP rate.
*   `processed_emg_*.csv`: EMG amplitude envelopes, activity bursts.

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
