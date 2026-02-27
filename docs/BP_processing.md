# BP (Blood Pressure) Signal Processing

## Overview

Blood pressure is recorded as a continuous waveform from a non-invasive blood pressure (NIBP) cuff. Unlike ECG-derived heart rate, this signal captures the actual pressure waveform (in mmHg), oscillating between systolic (peak) and diastolic (trough) values with each heartbeat. The pipeline treats this signal as a **PPG-like continuous pressure waveform** rather than applying standard PPG cleaning that would remove the DC (absolute pressure) offset.

BP is recorded **only** via the **Acqknowledge (Biopac)** device in this pipeline.

---

## Signal Processing

**Script:** `processing/process_acq_bp.py`
**Input:** `.acq` binary file (Biopac Acqknowledge format)
**Output:** `Processed_Data/<PID>/<Visit>/processed_bp_<PID>_<Visit>.csv`
**Typical Sampling Rate:** Auto-detected from file (commonly 2000 Hz)

### Step 1 — Channel Detection

The script scans all channels in the `.acq` file and returns the first channel whose name contains any of the following keywords (case-insensitive):

```
Search keywords (any match): "NIBP", "BLOOD PRESSURE", "BP"
```

If no matching channel is found, the script exits gracefully (exit code 0). Only the first matching channel is used.

### Step 2 — Signal Cleaning (Low-Pass Filter Only)

**Critical design decision:** Standard PPG cleaning applies a high-pass filter, which would remove the DC component (absolute pressure offset) and make the signal oscillate around zero rather than the true mmHg values. For NIBP data, absolute pressure values must be preserved.

Instead, only a **low-pass Butterworth filter** is applied:

```python
bp_cleaned = nk.signal_filter(
    channel.data,
    sampling_rate=fs,
    lowcut=None,      # No high-pass — preserves absolute mmHg offset
    highcut=8,        # 8 Hz low-pass — removes high-frequency noise
    method='butterworth',
    order=4
)
```

An 8 Hz cutoff preserves the pulse waveform morphology (heart rate is typically 1–3 Hz) while removing electrical noise.

### Step 3 — Systolic Peak Detection

Systolic peaks (highest pressure per beat) are detected by treating the cleaned BP signal as a PPG:

```python
info = nk.ppg_findpeaks(bp_cleaned, sampling_rate=fs)
peaks = info['PPG_Peaks']  # Array of sample indices for each systolic peak
```

### Step 4 — Heart Rate Calculation

From the detected systolic peak locations, an instantaneous rate signal (in BPM) is computed and interpolated to match the full signal length:

```python
rate = nk.signal_rate(peaks, sampling_rate=fs, desired_length=len(bp_cleaned))
```

### Step 5 — Diastolic Trough Detection

Between each pair of consecutive systolic peaks, the minimum value of the cleaned signal is identified as the diastolic trough:

```python
for i in range(len(peaks) - 1):
    segment = bp_cleaned[peaks[i] : peaks[i+1]]
    min_loc = np.argmin(segment)
    troughs.append(peaks[i] + min_loc)   # absolute index
```

### Step 6 — Continuous Systolic and Diastolic Interpolation

To create continuous estimate curves of systolic and diastolic pressure (sample-and-hold style), sparse peak/trough values are linearly interpolated across all samples. Back-fill is applied to handle samples before the first detected event:

```python
# Systolic interpolation
sbp_series = pd.Series(np.nan, index=np.arange(len(signals)))
sbp_series.iloc[peaks] = bp_cleaned[peaks]      # mmHg value at each systolic peak
signals['BP_Systolic_Interp'] = sbp_series.interpolate(method='linear').bfill()

# Diastolic interpolation
dbp_series = pd.Series(np.nan, index=np.arange(len(signals)))
dbp_series.iloc[troughs] = bp_cleaned[troughs]  # mmHg value at each diastolic trough
signals['BP_Diastolic_Interp'] = dbp_series.interpolate(method='linear').bfill()
```

### Step 7 — Event Label Annotation

If an `events.csv` file is provided, event markers are mapped to sample indices and written to an `Event_Label` column.

### Output Columns

| Column | Description |
|---|---|
| `BP_Raw` | Original raw signal (in mmHg) |
| `BP_Clean` | Low-pass filtered signal (8 Hz cutoff, absolute mmHg values preserved) |
| `BP_Rate` | Instantaneous heart rate (BPM) derived from systolic peak intervals |
| `BP_Systolic_Peak` | Binary indicator: 1 at systolic peak locations, 0 elsewhere |
| `BP_Diastolic_Peak` | Binary indicator: 1 at diastolic trough locations, 0 elsewhere |
| `BP_Systolic_Interp` | Continuously interpolated systolic pressure estimate (mmHg) |
| `BP_Diastolic_Interp` | Continuously interpolated diastolic pressure estimate (mmHg) |
| `Event_Label` | Event marker label at the start sample of each event |

> The `BP_Clean` column IS the continuous pressure waveform oscillating between SBP and DBP values. `BP_Systolic_Interp` and `BP_Diastolic_Interp` provide smoother, per-sample estimates of the envelope.

---

## Feature Extraction

**Script:** `features_extraction/features_acq_bp.py`
**Input:** Processed BP CSV + events CSV
**Outputs:**
- `features_bp_event_based_<PID>_<Visit>.csv`
- `features_bp_windowed_1_0s_<PID>_<Visit>.csv`

### Event Filtering by Visit Type

| Visit Type | Event Markers Used |
|---|---|
| **TSST** | Baseline Resting Period, Task Introduction, Speech Preperation, Speech Period, Arithmetic Period, Debrief Period, Recovery Period |
| **PDST** | Baseline Resting Period, Speech Period, Debrief Period, Recovery Period |

### Condition Labeling

Each sample is assigned a `Condition` label spanning from the start of one event marker to the start of the next.

### Features Computed (per segment or window)

#### Systolic Blood Pressure

| Feature | Source Column | Description |
|---|---|---|
| `BP_Systolic_Mean` | `BP_Systolic_Interp` | Mean systolic pressure (mmHg) |
| `BP_Systolic_SD` | `BP_Systolic_Interp` | Std of systolic pressure |

#### Diastolic Blood Pressure

| Feature | Source Column | Description |
|---|---|---|
| `BP_Diastolic_Mean` | `BP_Diastolic_Interp` | Mean diastolic pressure (mmHg) |
| `BP_Diastolic_SD` | `BP_Diastolic_Interp` | Std of diastolic pressure |

#### Mean Arterial Pressure (MAP)

| Feature | Source Column | Description |
|---|---|---|
| `BP_MAP_Mean` | `BP_Clean` (continuous waveform) | Mean of the full pressure waveform — approximates MAP |
| `BP_MAP_SD` | `BP_Clean` | Std of the pressure waveform |

> **Note:** `BP_MAP_Mean` uses the continuous `BP_Clean` waveform mean directly. If `BP_Clean` is unavailable, a fallback formula is applied: `MAP = (SBP + 2×DBP) / 3`.

#### Pulse Pressure

| Feature | Source Column | Description |
|---|---|---|
| `BP_PulsePressure_Mean` | `BP_Systolic_Interp - BP_Diastolic_Interp` | Mean pulse pressure (SBP - DBP, in mmHg) |
| `BP_PulsePressure_SD` | `BP_Systolic_Interp - BP_Diastolic_Interp` | Std of pulse pressure |

#### Heart Rate (from BP waveform)

| Feature | Source Column | Description |
|---|---|---|
| `BP_Rate_Mean` | `BP_Rate` | Mean heart rate derived from systolic peak intervals (BPM) |
| `BP_Rate_SD` | `BP_Rate` | Std of heart rate |

### Event-Based Output Columns

| Column | Description |
|---|---|
| `Condition` | Event marker name |
| `Start_Time` | Start time in seconds |
| `Duration` | Duration of the condition in seconds |
| `BP_Systolic_Mean` ... `BP_Rate_SD` | All features above |

### Windowed Output Columns

| Column | Description |
|---|---|
| `Time` | Start time of window in seconds |
| `Condition` | Dominant condition in window (mode) |
| `BP_Systolic_Mean` ... `BP_Rate_SD` | All features above |

---

## Key Parameters

| Parameter | Default | Description |
|---|---|---|
| `--sampling_rate` | 1000 | Sampling rate for feature extraction indexing |
| `--window_size` | 1.0 | Window duration in seconds for windowed extraction |

---

## Physiological Notes

- **Systolic BP** reflects the maximum pressure when the heart contracts (systole). Elevated SBP is a primary marker of cardiovascular stress response.
- **Diastolic BP** reflects the minimum pressure when the heart is at rest between beats. It reflects peripheral vascular resistance.
- **Pulse Pressure (SBP - DBP)** is a measure of arterial stiffness and stroke volume.
- **MAP** is the average arterial pressure throughout the cardiac cycle. It is the best single-number indicator of perfusion pressure.
- All pressure values are in **mmHg** because the low-pass-only cleaning approach preserves the absolute pressure offset of the NIBP signal.

---

## Dependencies

- `neurokit2` — `ppg_findpeaks()` for systolic peak detection, `signal_filter()` for low-pass filtering, `signal_rate()` for rate computation
- `bioread` — Reading `.acq` files
- `pandas`, `numpy` — Data manipulation and interpolation
