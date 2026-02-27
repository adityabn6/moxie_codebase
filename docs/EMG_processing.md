# EMG (Electromyography) Signal Processing

## Overview

EMG measures the electrical activity produced by skeletal muscles. In the MOXIE pipeline, surface EMG (sEMG) is used to detect facial muscle activity — commonly the **Zygomatic** (cheek/smile) and **Corrugator** (brow/frown) muscles — as indirect markers of emotional expression and stress responses.

EMG is recorded **only** via the **Acqknowledge (Biopac)** device in this pipeline. Feature extraction scripts for EMG are not yet implemented; only the signal processing (cleaning and amplitude extraction) step is currently available.

---

## Signal Processing

**Script:** `processing/process_acq_emg.py`
**Input:** `.acq` binary file (Biopac Acqknowledge format)
**Output:** `Processed_Data/<PID>/<Visit>/processed_emg_<PID>_<Visit>.csv`
**Typical Sampling Rate:** Auto-detected from file (commonly 2000 Hz)

### Step 1 — Channel Detection

The script scans **all** channels in the `.acq` file and collects every channel whose name contains `"EMG"` (case-insensitive). Multiple EMG channels are supported (e.g., separate channels for Zygomatic and Corrugator muscles).

```python
# Keyword: "EMG" (any channel containing this string)
emg_channels = [ch for ch in data.channels if "EMG" in ch.name.upper()]
```

Channel names found are printed to stdout for verification. If no EMG channels are found, the script exits gracefully (exit code 0).

### Step 2 — Per-Channel Processing

Each detected EMG channel is processed independently using NeuroKit2's `emg_process()` function:

```python
signals, info = nk.emg_process(channel.data, sampling_rate=fs)
```

`nk.emg_process()` performs the following internally:
1. **Cleaning (Bandpass filter):** Applies a bandpass filter appropriate for surface EMG. NeuroKit2 defaults are typically 100–500 Hz, which isolates the motor unit action potential frequencies while removing DC offset, motion artifacts (below 100 Hz), and high-frequency noise.
2. **Amplitude Envelope:** Computes the linear envelope of the cleaned signal (typically via full-wave rectification followed by low-pass filtering), representing the overall muscle activation level.
3. **Activity Detection:** Detects periods of significant muscle activation (EMG bursts) above a noise threshold, returning binary activity and onset markers.

### Step 3 — Column Renaming

To prevent column name collisions when multiple EMG channels are processed, each channel's output columns are suffixed with a channel identifier. The suffix is built from the channel index and a sanitized version of the channel name (alphanumeric characters only):

```python
safe_name = "".join([c for c in channel.name if c.isalnum() or c == '_'])
suffix = f"Channel_{i+1}_{safe_name}"

# Example suffixes for two channels:
# Channel_1_EMGZygomatic
# Channel_2_EMGCorrugator
```

If the raw signal column (`EMG_Raw_{suffix}`) is not included in NeuroKit2's output, it is added manually from the original channel data.

### Step 4 — Multi-Channel Concatenation

All per-channel DataFrames are concatenated horizontally (column-wise) into a single output DataFrame.

### Step 5 — Event Label Annotation

If an `events.csv` file is provided, event markers are mapped to sample indices and written to a single shared `Event_Label` column using the file's sampling rate.

### Output Columns (per channel, with suffix)

| Column (with suffix) | Description |
|---|---|
| `EMG_Raw_{suffix}` | Original raw EMG signal (in mV or μV depending on amplifier settings) |
| `EMG_Clean_{suffix}` | Bandpass-filtered signal (100–500 Hz surface EMG band) |
| `EMG_Amplitude_{suffix}` | Linear envelope of muscle activation (rectified + smoothed) |
| `EMG_Activity_{suffix}` | Binary indicator: 1 during detected muscle activation bursts, 0 at rest |
| `EMG_Onsets_{suffix}` | Binary indicator: 1 at the onset of each activation burst |
| `Event_Label` | Shared event marker annotations (one column for all channels) |

**Example column names for two channels:**

```
EMG_Raw_Channel_1_EMGZygomatic
EMG_Clean_Channel_1_EMGZygomatic
EMG_Amplitude_Channel_1_EMGZygomatic
EMG_Activity_Channel_1_EMGZygomatic
EMG_Onsets_Channel_1_EMGZygomatic
EMG_Raw_Channel_2_EMGCorrugator
EMG_Clean_Channel_2_EMGCorrugator
EMG_Amplitude_Channel_2_EMGCorrugator
EMG_Activity_Channel_2_EMGCorrugator
EMG_Onsets_Channel_2_EMGCorrugator
Event_Label
```

---

## Feature Extraction

Feature extraction for EMG is **not yet implemented** in the current pipeline. The processed EMG CSV (with amplitude envelopes and activity markers) is available for downstream analysis, but no automated feature extraction script (`features_acq_emg.py`) currently exists.

Planned features for future implementation include:

| Feature | Description |
|---|---|
| `EMG_Amplitude_Mean` | Mean muscle activation amplitude per condition/window |
| `EMG_Amplitude_SD` | Std of activation amplitude |
| `EMG_Activity_Ratio` | Proportion of time with active muscle bursts |
| `EMG_Burst_Count` | Number of activation bursts |
| `EMG_Burst_Duration_Mean` | Mean duration of each activation burst |

---

## Key Parameters

| Parameter | Description |
|---|---|
| Sampling rate | Auto-detected from `.acq` file (no override parameter) |
| Channel detection | All channels containing `"EMG"` (case-insensitive) |
| Processing method | NeuroKit2 defaults for surface EMG |

---

## Physiological Notes

- **Zygomatic muscle (zygomaticus major):** Controls the corners of the mouth. Activity correlates with smiling/positive affect.
- **Corrugator muscle (corrugator supercilii):** Controls eyebrow furrow. Activity correlates with negative affect, concentration, and discomfort.
- EMG signals are **biphasic and high-frequency** — the raw signal oscillates rapidly and must be bandpass filtered and rectified to produce a meaningful amplitude envelope.
- The **amplitude envelope** (`EMG_Amplitude`) is the primary signal of interest for most psychophysiology research, not the raw waveform.
- **Activity detection** provides a binary on/off signal indicating whether a muscle is meaningfully active above its baseline noise floor.

---

## Dependencies

- `neurokit2` — `emg_process()` for bandpass filtering, amplitude envelope, and activity detection
- `bioread` — Reading `.acq` files
- `pandas`, `numpy` — Data manipulation
