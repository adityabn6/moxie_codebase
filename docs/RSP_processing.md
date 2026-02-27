# RSP (Respiration) Signal Processing

## Overview

Respiration signals capture the mechanical movement of the chest and abdomen during breathing cycles. They are used to compute breathing rate, tidal amplitude, and respiratory phase (inhale/exhale/hold). The MOXIE pipeline supports respiration from two devices: **Acqknowledge (Biopac)** and **Hexoskin**.

---

## Device 1: Acqknowledge Respiration

**Script:** `processing/process_acq_rsp.py`
**Input:** `.acq` binary file (Biopac Acqknowledge format)
**Output:** `Processed_Data/<PID>/<Visit>/processed_rsp_<PID>_<Visit>.csv`
**Typical Sampling Rate:** Auto-detected from file (commonly 2000 Hz)

### Step 1 — Channel Detection

The script scans **all** channels in the `.acq` file and collects every channel whose name contains `"RSP"` (case-insensitive). Unlike ECG/EDA which take only the first match, RSP collects all matching channels to support multi-channel setups (e.g., both thoracic and abdominal belts recorded simultaneously).

```python
# Keyword: "RSP" (any channel containing this string)
rsp_channels = [ch for ch in data.channels if "RSP" in ch.name.upper()]
```

If no RSP channels are found, the script exits gracefully (exit code 0).

### Step 2 — Per-Channel Processing

Each detected RSP channel is processed independently using NeuroKit2's `rsp_process()` function with the `"khodadad2018"` method, which is optimized for ambulatory recordings and noisy signals.

```python
signals, info = nk.rsp_process(channel.data, sampling_rate=fs, method="khodadad2018")
```

The `khodadad2018` method performs:
- **Bandpass filtering** to isolate the respiratory frequency band (typically 0.05–3 Hz)
- **Peak/trough detection** for identifying individual breath cycles
- **Breath-by-breath rate computation** interpolated to a continuous signal
- **Amplitude estimation** per breath cycle
- **Phase assignment** (inhale = 1, exhale = 0) per sample

### Step 3 — Column Renaming

To prevent column name collisions when multiple RSP channels are processed, each channel's output columns are suffixed with a channel identifier derived from the channel index and name:

```
suffix = "Channel_{i+1}_{channel_name_sanitized}"

Example columns:
  RSP_Clean_Channel_1_RSPThoracic
  RSP_Rate_Channel_1_RSPThoracic
  RSP_Clean_Channel_2_RSPAbdominal
  RSP_Rate_Channel_2_RSPAbdominal
```

### Step 4 — Multi-Channel Concatenation

All per-channel DataFrames are concatenated horizontally (column-wise) into a single output DataFrame, so all channels are in one file.

### Step 5 — Event Label Annotation

If an `events.csv` file is present, event markers are annotated in a single shared `Event_Label` column using sample index mapping at the file's sampling rate.

### Output Columns (per channel, with suffix)

| Column (with suffix) | Description |
|---|---|
| `RSP_Raw_{suffix}` | Original raw respiration signal |
| `RSP_Clean_{suffix}` | Bandpass-filtered respiration signal |
| `RSP_Amplitude_{suffix}` | Tidal amplitude per sample (interpolated from breath-by-breath estimates) |
| `RSP_Rate_{suffix}` | Breathing rate (breaths per minute), interpolated per sample |
| `RSP_Phase_{suffix}` | Respiratory phase: 1 = inhale, 0 = exhale |
| `RSP_Peaks_{suffix}` | Binary: 1 at inhalation peak (top of each breath) |
| `RSP_Troughs_{suffix}` | Binary: 1 at exhalation trough (bottom of each breath) |
| `Event_Label` | Shared event marker annotations (one column for all channels) |

---

## Device 2: Hexoskin Respiration

**Script:** `processing/process_hexoskin_rsp.py`
**Input:** Hexoskin directory or specific CSV file
**Output:** `Processed_Data/<PID>/<Visit>/processed_hex_rsp_<PID>_<Visit>.csv`
**Sampling Rate:** Fixed at **256 Hz**

### Step 1 — Data Loading

The script recursively scans all `.csv` files in the provided directory. For each file, it reads only the header row (for speed), then loads the full column if a match is found. It independently searches for:

```
Thoracic component:  column 'respiration_thoracic'
Abdominal component: column 'respiration_abdominal'
```

Both components can come from the same file or from separate files. The first file containing each column is used. If a component is not found in any CSV, it is silently skipped.

### Step 2 — Per-Component Processing

Each found component is processed independently using the same method as Acqknowledge:

```python
signals, info = nk.rsp_process(data, sampling_rate=256, method="khodadad2018")
```

### Step 3 — Column Renaming

Columns are suffixed with `"Thoracic"` or `"Abdominal"` to distinguish between the two components:

```
RSP_Clean_Thoracic,  RSP_Rate_Thoracic,  RSP_Amplitude_Thoracic  ...
RSP_Clean_Abdominal, RSP_Rate_Abdominal, RSP_Amplitude_Abdominal ...
```

### Step 4 — Multi-Component Concatenation

Thoracic and abdominal DataFrames are concatenated horizontally into a single output file.

### Step 5 — Event Label Annotation

Event markers are annotated in a shared `Event_Label` column using 256 Hz sample index mapping.

### Output Columns (per component, with suffix)

| Column (with suffix) | Description |
|---|---|
| `RSP_Raw_{Thoracic\|Abdominal}` | Raw respiration signal |
| `RSP_Clean_{Thoracic\|Abdominal}` | Cleaned signal |
| `RSP_Amplitude_{Thoracic\|Abdominal}` | Tidal amplitude per sample |
| `RSP_Rate_{Thoracic\|Abdominal}` | Breathing rate (breaths per minute) |
| `RSP_Phase_{Thoracic\|Abdominal}` | Respiratory phase (1=inhale, 0=exhale) |
| `RSP_Peaks_{Thoracic\|Abdominal}` | Inhalation peaks |
| `RSP_Troughs_{Thoracic\|Abdominal}` | Exhalation troughs |
| `Event_Label` | Shared event marker annotations |

---

## Feature Extraction

**Script:** `features_extraction/features_acq_rsp.py`
**Input:** Processed RSP CSV + events CSV
**Outputs:**
- `features_rsp_event_based_<PID>_<Visit>.csv`
- `features_rsp_windowed_1_0s_<PID>_<Visit>.csv`

### Event Filtering by Visit Type

| Visit Type | Event Markers Used |
|---|---|
| **TSST** | Baseline Resting Period, Task Introduction, Speech Preperation, Speech Period, Arithmetic Period, Debrief Period, Recovery Period |
| **PDST** | Baseline Resting Period, Speech Period, Debrief Period, Recovery Period |

### Condition Labeling

Each sample is assigned a `Condition` label spanning from the start of one event marker to the start of the next.

### Global Gradient Threshold (Pre-computation)

Before extracting any features, the script computes a **global gradient threshold** from the entire RSP_Clean signal. This threshold is used consistently across all windows to detect "hold breath" periods (flat segments):

```python
gradient = np.gradient(rsp_clean_values)
grad_std = np.std(gradient)
gradient_threshold = 0.05 * grad_std   # 5% of global gradient standard deviation
```

This ensures the hold-breath detection is calibrated to each individual recording's signal characteristics rather than using a fixed absolute threshold.

### Features Computed (per segment or window)

#### Basic Respiratory Metrics

| Feature | Source Column | Description |
|---|---|---|
| `RSP_Rate_Mean` | `RSP_Rate_*` (first match) | Mean breathing rate (breaths/min) |
| `RSP_Rate_SD` | `RSP_Rate_*` (first match) | Std of breathing rate |
| `RSP_Amp_Mean` | `RSP_Amplitude_*` (first match) | Mean tidal amplitude |
| `RSP_Amp_SD` | `RSP_Amplitude_*` (first match) | Std of tidal amplitude |

> Column names are resolved dynamically using `startswith()` matching, so they work for both Acqknowledge channel suffixes and Hexoskin component suffixes.

#### Gradient-Based Phase Classification (Slope Method)

Computed from the `RSP_Clean_*` signal using the global gradient threshold:

| Feature | Description |
|---|---|
| `RSP_Slope_Inhale_Ratio` | Fraction of samples where slope > threshold (positive slope = inhaling) |
| `RSP_Slope_Exhale_Ratio` | Fraction of samples where slope < -threshold (negative slope = exhaling) |
| `RSP_Slope_Hold_Ratio` | Fraction of samples where \|slope\| ≤ threshold (flat = breath hold) |
| `RSP_Slope_Dominant` | Most dominant phase by sample count: `"Inhale"`, `"Exhale"`, or `"Hold"` |

#### NeuroKit-Based Phase Classification

Derived from the `RSP_Phase_*` column (1 = inhale, 0 = exhale, set by NeuroKit2):

| Feature | Description |
|---|---|
| `RSP_Inhale_Ratio` | Fraction of samples labeled as inhale (phase == 1.0) |
| `RSP_Exhale_Ratio` | Fraction of samples labeled as exhale (phase == 0.0) |
| `RSP_Phase_Dominant` | Dominant phase: `"Inhale"` or `"Exhale"` |

> The slope-based method can detect three phases (including Hold), while the NeuroKit method only distinguishes inhale vs. exhale.

### Event-Based Output Columns

| Column | Description |
|---|---|
| `Condition` | Event marker name |
| `Start_Time` | Start time in seconds |
| `Duration` | Duration of the condition in seconds |
| `RSP_Rate_Mean` ... `RSP_Phase_Dominant` | All features above |

### Windowed Output Columns

| Column | Description |
|---|---|
| `Time` | Start time of window in seconds |
| `Condition` | Dominant condition in window (mode) |
| `RSP_Rate_Mean` ... `RSP_Phase_Dominant` | All features above |

---

## Key Parameters

| Parameter | Default | Description |
|---|---|---|
| `--sampling_rate` | 1000 | Sampling rate for feature extraction indexing |
| `--window_size` | 1.0 | Window duration in seconds for windowed extraction |

---

## Physiological Notes

- **Thoracic respiration** reflects chest wall movement and is more sensitive to upper-body tension.
- **Abdominal respiration** reflects diaphragmatic movement and is associated with relaxed, deep breathing.
- **Breathing rate** decreases during calm/relaxed states and increases during stress or anxiety.
- **Hold detection** (slope-based) can identify voluntary or involuntary breath-holding, which may correlate with anticipatory stress.

---

## Dependencies

- `neurokit2` — RSP cleaning (`khodadad2018` method), peak/trough detection, rate and amplitude computation
- `bioread` — Reading `.acq` files (Acqknowledge only)
- `pandas`, `numpy` — Data manipulation
