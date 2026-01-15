---
description: How to setup the MOXIE environment and run the pipeline.
---

# setup_moxie_pipeline

This workflow initializes the MOXIE signal processing environment.

1.  **Clone/Pull Codebase**:
    Ensure `moxie_codebase` is present in the workspace.

2.  **Install Dependencies**:
    ```bash
    pip install -r moxie_codebase/requirements.txt
    ```

3.  **Generate Catalog**:
    // turbo
    ```bash
    python moxie_codebase/utils/generate_catalog.py
    ```

4.  **Extract Events (Layer 1)**:
    Run the event extraction layer.
    ```bash
    # Usage: run_events.sh <DATA_DIR> <OUTPUT_DIR>
    bash moxie_codebase/workflows/run_events.sh "N:/Aditya/Participant Data" "C:/Users/Aditya/Work/MOXIE/output" 
    ```

5.  **Run Processing (Layer 2)**:
    Submit jobs or run locally.
    ```bash
    # Local Test for Row 1
    bash moxie_codebase/workflows/run_processing.sh moxie_codebase/utils/processing_catalog.csv "C:/Users/Aditya/Work/MOXIE/output" 1
    ```
