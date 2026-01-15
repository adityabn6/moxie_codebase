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

## 🚀 Usage

The pipeline runs in **two sequential layers**, driven by a master catalog.

### Step 0: Generate Catalog
Scan your raw data directory to create a processing catalog. This catalog defines every "job" (one modality per participant/visit).

```bash
python utils/generate_catalog.py
```
*Output: `processing_catalog.csv`*

### Step 1: Layer 1 - Event Extraction
Extracts digital markers to create `events.csv` and sets up the output directory structure. This **must** run before signal processing.

```bash
bash workflows/run_events.sh <Data_Source_Root> <Output_Root>
```

### Step 2: Layer 2 - Signal Processing
Runs the specific processing script for each row in the catalog. Designed for Slurm Arrays but can run locally.

**Slurm Usage:**
```bash
sbatch --array=1-N workflows/run_processing.sh processing_catalog.csv <Output_Root>
```

**Local Usage:**
```bash
bash workflows/run_processing.sh processing_catalog.csv <Output_Root> <Catalog_Row_Index>
```

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
