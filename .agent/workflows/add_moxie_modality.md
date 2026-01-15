---
description: How to add a new sensor/modality to the MOXIE pipeline.
---

# adding_moxie_modality

This workflow guides you through adding a new physiological signal (modality) to the `moxie_codebase`.

1.  **Identify Device & Modality**:
    Determine the device name (e.g., `garmin`, `shimmer`) and modality (e.g., `temp`, `acc`).

2.  **Create Processing Script**:
    Create `moxie_codebase/processing/process_[DEVICE]_[MODALITY].py`.
    *   Template: Use `process_acq_ecg.py` as a base.
    *   **Arguments**: Ensure it accepts `--participant_id`, `--visit_type`, `--events_file`, and a file path argument.
    *   **Logic**: Load data, load events (handle missing), process using `neurokit2` or custom logic, save CSV.

3.  **Update Catalog Generator**:
    Edit `moxie_codebase/utils/generate_catalog.py`.
    *   Locate the scanning logic for the relevant visit/device.
    *   Add a block to append a new row to `catalog_data`:
        ```python
        catalog_data.append({
            "participant_id": pid,
            "visit_type": visit,
            "device": "YOUR_DEVICE",
            "modality": "YOUR_MODALITY",
            "file_path": file_path
        })
        ```

4.  **Update Processing Workflow (If New Device)**:
    If this is a *new device type* (not just a new modality for Acq/Hex), open `moxie_codebase/workflows/run_processing.sh`.
    *   Add a case to the `case "$DEVICE" in` block:
        ```bash
        "your_device")
            PYTHON_SCRIPT="$SCRIPT_DIR/process_yourdevice_${MODALITY}.py"
            CMD="$CMD --your_device_path \"$FILE_PATH\""
            ;;
        ```

5.  **Create Verification Script**:
    Create `moxie_codebase/verification/verify_[DEVICE]_[MODALITY].py`.
    *   Load the output CSV.
    *   Print `df.describe()`.
    *   Plot a 60s sample.

6.  **Verify**:
    *   Run `python utils/generate_catalog.py`.
    *   Run a local test: `bash workflows/run_processing.sh processing_catalog.csv <OUTPUT_ROOT> <ROW_ID>`.
