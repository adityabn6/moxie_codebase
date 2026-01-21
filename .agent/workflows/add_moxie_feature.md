---
description: How to add or refine feature extraction logic for an existing modality.
---

# adding_moxie_feature_logic

This workflow guides you through implementing new physiological feature extraction logic (e.g., Breath Hold Detection, RSA, HRV metrics) to the existing `features_extraction` layer.

## 1. Feature Definition & Research

*   **Goal**: Define exactly what feature you want to extract (e.g., "RSP Breath Hold Ratio").
*   **Method**: Determine the mathematical or signal processing approach (e.g., "Slope analysis with adaptive threshold").
*   **Target Script**: Identify the relevant script in `features_extraction/` (e.g., `features_acq_rsp.py`).

## 2. Develop with Synthetic Data (Recommended)

Before running on massive datasets, verify your logic on controlled synthetic data.

1.  **Create Test Script**: Create a temporary test script (e.g., `tests/dev_rsp_slope.py`).
2.  **Generate Data**: Use `neurokit2` or `numpy` to generate a signal with known properties (e.g., a defined flatline for a breath hold).
    ```python
    # Example: 10s sine wave + 5s flatline
    rsp = np.concatenate([np.sin(x), np.zeros(500)])
    ```
3.  **Prototype Logic**: Write your function to process this synthetic array.
4.  **Visualize**: Plot the signal and your detection markers to confirm accuracy.

## 3. Implement in Codebase

Once the logic is solid, migrate it to the production script.

1.  **Open Script**: `moxie_codebase/features_extraction/features_[DEVICE]_[MODALITY].py`.
2.  **Add Helper Function**: Place your core calculation logic in a helper function or class method.
3.  **Update Main Loop**: Call this function within the processing loop (usually iterating over epochs or the whole signal).
4.  **Compute Metrics**: usage the raw detection (e.g., "Hold Vector") to compute summary metrics (e.g., "Hold_Duration_Total").
5.  **Update Output**: Add the new metrics to the dictionary/DataFrame that gets saved to CSV.

## 4. Verification on Real Data

1.  **Select Subject**: specific a PID with known/clean data (e.g., `126641`).
2.  **Run Local Extraction**:
    ```bash
    bash workflows/run_features.sh <PID> <VISIT> <PATH_TO_PROCESSED_CSV> <OUTPUT_DIR>
    ```
3.  **Inspect Output**: Check the generated CSV for the new columns.
4.  **Visualize**: It is often helpful to modify the script to save a debug plot for the single run to inspect the detection alignment with the real signal.

## 5. Deployment

1.  **Commit**: Push changes to GitHub.
2.  **Update Cluster**: Pull changes on Greatlakes.
3.  **Run**: Submit the batch processing job.
