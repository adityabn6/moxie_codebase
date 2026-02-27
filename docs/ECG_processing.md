# ECG (Electrocardiogram) Signal Processing

## Overview

ECG measures the electrical activity of the heart. The MOXIE pipeline supports ECG from two devices: **Acqknowledge (Biopac)** and **Hexoskin**. Both devices use the same NeuroKit2-based processing logic, differing only in input format and sampling rate.

---

## Device 1: Acqknowledge ECG

**Script:** `processing/process_acq_ecg.py`
**Input:** `.acq` binary file (Biopac Acqknowledge format)
**Output:** `Processed_Data/<PID>/<Visit>/processed_ecg_<PID>_<Visit>.csv`
**Typical Sampling Rate:** Auto-detected from file (commonly 2000 Hz)

### Step 1 — Channel Detection

The script scans all channels in the `.acq` file and selects the first channel whose name contains `"ECG"` or `"EKG"` (case-insensitive).

```python
# Channel keywords searched (in priority order):
["ECG", "EKG"]
```

If no ECG/EKG channel is found, available channel names are printed and the script exits with an error.

### Step 2 — Signal Cleaning

The raw ECG signal is cleaned using NeuroKit2's `ecg_clean()` function with the `"neurokit"` method. This applies:
- A **0.5 Hz high-pass filter** to remove baseline wander
- A **powerline noise filter** (50/60 Hz notch)

```python
ecg_cleaned = nk.ecg_clean(channel.data, sampling_rate=fs, method="neurokit")
```

### Step 3 — Peak Detection & Full Processing

The cleaned signal is passed to `nk.ecg_process()`, which performs:
- **R-peak detection** using the NeuroKit2 pan-tompkins variant (robust QRS detector)
- **Heart rate calculation** (instantaneous, in BPM) from R-R intervals
- **Signal quality index** estimation per sample

```python
signals, info = nk.ecg_process(ecg_cleaned, sampling_rate=fs)
```

### Step 4 — Event Label Annotation

If an `events.csv` file is provided, event markers are mapped to the nearest sample index and written into an `Event_Label` column. Each event occupies exactly one sample (the start sample of that event).

```python
start_idx = int(start_time * fs)
signals.at[start_idx, 'Event_Label'] = label
```

### Output Columns

| Column | Description |
|---|---|
| `ECG_Raw` | Original raw signal from the amplifier |
| `ECG_Clean` | Baseline-corrected, noise-filtered signal |
| `ECG_Rate` | Instantaneous heart rate (BPM), interpolated per sample |
| `ECG_R_Peaks` | Binary indicator: 1 at R-peak locations, 0 elsewhere |
| `ECG_Quality` | Per-sample signal quality index (0–1) |
| `Event_Label` | Event marker label at the start sample of each event |

---

## Device 2: Hexoskin ECG

**Script:** `processing/process_hexoskin_ecg.py`
**Input:** Hexoskin directory or specific CSV/WAV file
**Output:** `Processed_Data/<PID>/<Visit>/processed_hex_ecg_<PID>_<Visit>.csv`
**Sampling Rate:** Fixed at **256 Hz**

### Step 1 — Data Loading

The script searches for ECG data using a two-tier priority:

**Priority 1 — CSV files:**
Scans all `.csv` files in the directory recursively. Reads only the header of each file for speed, then loads the full file when a matching column is found.

```
Column priority:
  1. 'ecg_1'  (Hexoskin standard export)
  2. 'ecg1'   (alternative export format)
```

**Priority 2 — WAV files (fallback):**
If no CSV with ECG columns is found, searches for files matching `*ECG*.wav` and reads via `scipy.io.wavfile`.

### Step 2 — Signal Cleaning

Identical to Acqknowledge processing:

```python
ecg_cleaned = nk.ecg_clean(data, sampling_rate=256, method="neurokit")
```

### Step 3 — Peak Detection & Full Processing

```python
signals, info = nk.ecg_process(ecg_cleaned, sampling_rate=256)
```

### Step 4 — Event Label Annotation

Same as Acqknowledge: event start times are converted to sample indices at 256 Hz and written to `Event_Label`.

### Output Columns

Identical to Acqknowledge output:

| Column | Description |
|---|---|
| `ECG_Raw` | Raw ECG signal |
| `ECG_Clean` | Cleaned ECG signal |
| `ECG_Rate` | Instantaneous heart rate (BPM) |
| `ECG_R_Peaks` | Binary R-peak indicator |
| `ECG_Quality` | Signal quality index |
| `Event_Label` | Event marker annotations |

---

## Feature Extraction

**Script:** `features_extraction/features_acq_ecg.py`
**Input:** Processed ECG CSV + events CSV
**Outputs:**
- `features_ecg_event_based_<PID>_<Visit>.csv`
- `features_ecg_windowed_1_0s_<PID>_<Visit>.csv`

### Event Filtering by Visit Type

| Visit Type | Event Markers Used |
|---|---|
| **TSST** | Baseline Resting Period, Task Introduction, Speech Preperation, Speech Period, Arithmetic Period, Debrief Period, Recovery Period |
| **PDST** | Baseline Resting Period, Speech Period, Debrief Period, Recovery Period |

### Condition Labeling

Each sample in the processed file is assigned a `Condition` label. A condition spans from the start of one event marker to the start of the next. The last event spans to the end of the file.

### Features Computed (per segment or window)

| Feature | Description | Formula |
|---|---|---|
| `ECG_Rate_Mean` | Mean heart rate (BPM) | `mean(ECG_Rate)` |
| `ECG_Rate_SD` | Std of heart rate | `std(ECG_Rate)` |
| `HRV_RMSSD` | Root Mean Square of Successive Differences | `sqrt(mean(diff(RR)^2))` — vagal tone marker |
| `HRV_SDNN` | Std of NN (R-R) intervals | `std(RR)` — overall HRV |
| `HRV_CVSD` | Coefficient of variation (RMSSD-based) | `RMSSD / mean(RR)` |
| `HRV_CVNN` | Coefficient of variation (SDNN-based) | `SDNN / mean(RR)` |
| `HRV_MeanNN` | Mean R-R interval (ms) | `mean(RR)` |
| `HRV_MedianNN` | Median R-R interval (ms) | `median(RR)` |
| `HRV_pNN50` | % of successive RR intervals differing > 50 ms | `(count(abs(diff(RR)) > 50) / N) * 100` |

> **Note:** Frequency-domain HRV features (LF, HF, LF/HF) are not currently computed. At least 2 R-peaks are required for any HRV calculation; features return `NaN` if insufficient peaks are found.

### Event-Based Output Columns

| Column | Description |
|---|---|
| `Condition` | Event marker name (e.g., "Baseline Resting Period") |
| `Start_Time` | Start time in seconds |
| `Duration` | Duration of the condition in seconds |
| `ECG_Rate_Mean` ... `HRV_pNN50` | All features above |

### Windowed Output Columns

| Column | Description |
|---|---|
| `Time` | Start time of window in seconds |
| `Condition` | Dominant condition in window (mode) |
| `ECG_Rate_Mean` ... `HRV_pNN50` | All features above |

---

## Key Parameters

| Parameter | Default | Description |
|---|---|---|
| `--sampling_rate` | 1000 | Sampling rate for feature extraction indexing |
| `--window_size` | 1.0 | Window duration in seconds for windowed extraction |

---

## Dependencies

- `neurokit2` — ECG cleaning, peak detection, rate calculation
- `bioread` — Reading `.acq` files (Acqknowledge only)
- `scipy.io.wavfile` — Reading WAV files (Hexoskin fallback)
- `pandas`, `numpy` — Data manipulation
