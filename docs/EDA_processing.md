# EDA (Electrodermal Activity) Signal Processing

## Overview

EDA (also called Galvanic Skin Response / GSR, or Skin Conductance / SC) measures the skin's electrical conductance, which is controlled by sweat gland activity driven by the sympathetic nervous system. It is a sensitive marker of emotional arousal and stress.

EDA is recorded **only** via the **Acqknowledge (Biopac)** device in this pipeline.

---

## Signal Processing

**Script:** `processing/process_acq_eda.py`
**Input:** `.acq` binary file (Biopac Acqknowledge format)
**Output:** `Processed_Data/<PID>/<Visit>/processed_eda_<PID>_<Visit>.csv`
**Typical Sampling Rate:** Auto-detected from file (commonly 2000 Hz)

### Step 1 — Channel Detection

The script scans all channels in the `.acq` file and selects the first channel whose name contains any of the following keywords (case-insensitive):

```
Search keywords (any match): "EDA", "GSR", "SC", "SKIN"
```

If no matching channel is found, the script exits gracefully (exit code 0) with a message listing available channels.

### Step 2 — Signal Cleaning and Decomposition

The raw EDA signal is processed using NeuroKit2's `eda_process()` function with the `"neurokit"` method. This single call handles:

1. **Cleaning:** Low-pass filtering to remove high-frequency noise while preserving slow tonic changes
2. **Decomposition:** Separates the signal into two physiologically distinct components:
   - **Tonic component (SCL — Skin Conductance Level):** The slow-moving baseline, reflecting sustained arousal
   - **Phasic component (SCR — Skin Conductance Response):** The fast-changing component, reflecting transient responses to stimuli
3. **SCR Peak Detection:** Identifies individual skin conductance responses (SCRs) in the phasic signal, computing onset, peak, amplitude, rise time, and recovery time for each response

```python
signals, info = nk.eda_process(channel.data, sampling_rate=fs, method="neurokit")
```

### Step 3 — Event Label Annotation

If an `events.csv` file is provided, event markers are mapped to the nearest sample index and annotated in an `Event_Label` column.

```python
start_idx = int(start_time * fs)
signals.at[start_idx, 'Event_Label'] = label
```

### Output Columns

| Column | Description |
|---|---|
| `EDA_Raw` | Original raw signal (in microsiemens, μS) |
| `EDA_Clean` | Noise-filtered signal |
| `EDA_Tonic` | Tonic component — slow-varying SCL baseline |
| `EDA_Phasic` | Phasic component — fast SCR responses above baseline |
| `SCR_Onsets` | Binary indicator: 1 at the onset of each SCR event |
| `SCR_Peaks` | Binary indicator: 1 at the peak of each SCR event |
| `SCR_Height` | Amplitude from onset to peak for each detected SCR |
| `SCR_Amplitude` | Amplitude of each SCR peak (may differ from height based on NK convention) |
| `SCR_RiseTime` | Time from SCR onset to peak (in seconds) |
| `SCR_RecoveryTime` | Time from SCR peak back to 50% amplitude recovery (in seconds) |
| `Event_Label` | Event marker label at the start sample of each event |

> If `eda_process()` raises an exception (e.g., signal too short or degenerate), the script returns an empty DataFrame and writes no output file.

---

## Feature Extraction

**Script:** `features_extraction/features_acq_eda.py`
**Input:** Processed EDA CSV + events CSV
**Outputs:**
- `features_eda_event_based_<PID>_<Visit>.csv`
- `features_eda_windowed_1_0s_<PID>_<Visit>.csv`

### Event Filtering by Visit Type

| Visit Type | Event Markers Used |
|---|---|
| **TSST** | Baseline Resting Period, Task Introduction, Speech Preperation, Speech Period, Arithmetic Period, Debrief Period, Recovery Period |
| **PDST** | Baseline Resting Period, Speech Period, Debrief Period, Recovery Period |

### Condition Labeling

Each sample in the processed file is assigned a `Condition` label. A condition spans from the start of one event marker to the start of the next. The last event spans to the end of the file.

### Features Computed (per segment or window)

#### Tonic Component (SCL — Skin Conductance Level)

| Feature | Source Column | Description |
|---|---|---|
| `EDA_SCL_Mean` | `EDA_Tonic` (or `EDA_Clean` as fallback) | Mean skin conductance level (μS) |
| `EDA_SCL_SD` | `EDA_Tonic` (or `EDA_Clean` as fallback) | Std of skin conductance level |

#### Phasic Component

| Feature | Source Column | Description |
|---|---|---|
| `EDA_Phasic_Mean` | `EDA_Phasic` | Mean phasic activity |
| `EDA_Phasic_SD` | `EDA_Phasic` | Std of phasic activity |
| `EDA_Phasic_Max` | `EDA_Phasic` | Peak phasic amplitude in the segment |

#### SCR (Skin Conductance Response) Features

| Feature | Source Column | Description |
|---|---|---|
| `EDA_SCR_Count` | `SCR_Peaks` | Total number of SCR peaks in the segment |
| `EDA_SCR_Freq_PerMin` | `SCR_Peaks` | SCR frequency, normalized to per-minute rate |
| `EDA_SCR_Amp_Mean` | `SCR_Amplitude` at peak locations | Mean amplitude of detected SCR peaks |
| `EDA_SCR_RiseTime_Mean` | `SCR_RiseTime` at peak locations | Mean rise time from onset to peak (seconds) |

> **Note:** `EDA_SCR_Amp_Mean` and `EDA_SCR_RiseTime_Mean` return `NaN` if no SCR peaks exist in the segment. `EDA_SCR_Freq_PerMin` is computed as `(n_peaks / duration_seconds) * 60`.

### Event-Based Output Columns

| Column | Description |
|---|---|
| `Condition` | Event marker name |
| `Start_Time` | Start time in seconds |
| `Duration` | Duration of the condition in seconds |
| `EDA_SCL_Mean` ... `EDA_SCR_RiseTime_Mean` | All features above |

### Windowed Output Columns

| Column | Description |
|---|---|
| `Time` | Start time of window in seconds |
| `Condition` | Dominant condition in window (mode) |
| `EDA_SCL_Mean` ... `EDA_SCR_RiseTime_Mean` | All features above |

---

## Key Parameters

| Parameter | Default | Description |
|---|---|---|
| `--sampling_rate` | 1000 | Sampling rate for feature extraction indexing |
| `--window_size` | 1.0 | Window duration in seconds for windowed extraction |

---

## Physiological Notes

- **SCL** reflects sustained autonomic nervous system (ANS) activity. Higher SCL = higher overall arousal.
- **SCR frequency** is the most commonly reported EDA measure in stress research. More SCRs per minute typically indicate higher sympathetic activation.
- **SCR amplitude** reflects the intensity of individual arousal responses.
- EDA is unidirectional — it can increase rapidly (phasic peak) but recovers slowly (tonic return). This asymmetry is captured by `SCR_RiseTime` vs `SCR_RecoveryTime`.

---

## Dependencies

- `neurokit2` — EDA cleaning, tonic/phasic decomposition, SCR peak detection
- `bioread` — Reading `.acq` files
- `pandas`, `numpy` — Data manipulation
