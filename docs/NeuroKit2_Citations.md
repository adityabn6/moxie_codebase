# NeuroKit2 Method Citations

This document lists the academic references underlying each NeuroKit2 function called in the MOXIE signal processing pipeline, organized by physiological modality.

**Primary NeuroKit2 Reference:**

> Makowski, D., Pham, T., Lau, Z. J., Brammer, J. C., Lespinasse, F., Pham, H., Schölzel, C., & Chen, S. H. A. (2021). NeuroKit2: A Python toolbox for neurophysiological signal processing. *Behavior Research Methods*, 53(4), 1689–1696. https://doi.org/10.3758/s13428-020-01516-y

---

## ECG — Electrocardiogram

**Scripts:** `processing/process_acq_ecg.py`, `processing/process_hexoskin_ecg.py`
**Functions:** `nk.ecg_clean()`, `nk.ecg_process()`
**Method parameter:** `method="neurokit"`

### Signal Cleaning (`ecg_clean`)

The `"neurokit"` method applies a 0.5 Hz high-pass Butterworth filter to remove baseline wander, followed by a 50 Hz powerline notch filter. The filtering approach draws from the following foundational QRS preprocessing literature:

> Engelse, W. A. H., & Zeelenberg, C. (1979). A single scan algorithm for QRS-detection and feature extraction. *Computers in Cardiology*, 6, 37–42.

> Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm. *IEEE Transactions on Biomedical Engineering*, 32(3), 230–236.

> Hamilton, P. (2002). Open source ECG analysis. *Computers in Cardiology*, 101–104. IEEE.

> Elgendi, M., Jonkman, M., & De Boer, F. (2010). Frequency bands effects on QRS detection. In *Biosignals, Proceedings of the Third International Conference on Bio-inspired Systems and Signal Processing* (pp. 428–431).

### R-Peak Detection (`ecg_process` → `ecg_peaks`)

`nk.ecg_process()` internally calls `ecg_peaks()` with the `"neurokit"` method, which is NeuroKit2's own adaptive-threshold algorithm drawing from multiple QRS detectors:

> Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm. *IEEE Transactions on Biomedical Engineering*, 32(3), 230–236.

> Hamilton, P. (2002). Open source ECG analysis. *Computers in Cardiology* (pp. 101–104). IEEE.

> Christov, I. I. (2004). Real time electrocardiogram QRS detection using combined adaptive threshold. *Biomedical Engineering Online*, 3(1), 1–9.

> Gamboa, H. (2008). *Multi-modal behavioral biometrics based on HCI and electrophysiology* [Doctoral dissertation, Universidade Técnica de Lisboa]. http://www.lx.it.pt/~afred/pub/thesisHugoGamboa.pdf

> Elgendi, M., Jonkman, M., & De Boer, F. (2010). Frequency bands effects on QRS detection. In *Biosignals, Third International Conference on Bio-inspired Systems and Signal Processing* (pp. 428–431).

> Koka, T., & Muma, M. (2022). Fast and sample accurate R-peak detection for noisy ECG using visibility graphs. In *2022 44th Annual International Conference of the IEEE Engineering in Medicine & Biology Society (EMBC)* (pp. 121–126).

> Emrich, J., Koka, T., Wirth, S., & Muma, M. (2023). Accelerated sample-accurate R-peak detectors based on visibility graphs. In *31st European Signal Processing Conference (EUSIPCO)* (pp. 1090–1094). https://doi.org/10.23919/EUSIPCO58844.2023.10290007

### Signal Quality Assessment (`ecg_process` → `ecg_quality`)

`nk.ecg_process()` computes an ECG signal quality index using heuristics from:

> Zhao, Z., & Zhang, Y. (2018). SQI quality evaluation mechanism of single-lead ECG signal based on simple heuristic fusion and fuzzy comprehensive evaluation. *Frontiers in Physiology*, 9, 727.

> Orphanidou, C., Bonnici, T., Charlton, P., Clifton, D., Vallance, D., & Tarassenko, L. (2015). Signal-quality indices for the electrocardiogram and photoplethysmogram: derivation and applications to wireless monitoring. *IEEE Journal of Biomedical and Health Informatics*, 19(3), 832–838.

> Sabeti, E., Katebi, N., Boyle, J., & Clifford, G. D. (2019). Signal quality measure for pulsatile physiological signals using morphological features: Applications in reliability measure for pulse oximetry. *Informatics in Medicine Unlocked*, 16, 100222.

---

## RSP — Respiration

**Scripts:** `processing/process_acq_rsp.py`, `processing/process_hexoskin_rsp.py`
**Function:** `nk.rsp_process()`
**Method parameter:** `method="khodadad2018"`

### Signal Cleaning (`rsp_process` → `rsp_clean`)

The `"khodadad2018"` method applies a bandpass Butterworth filter (0.1–0.35 Hz) optimised for ambulatory respiration recordings. The default biosppy bandpass reference is:

> Khodadad, D., Nordebo, S., Müller, B., Waldmann, A., Yerworth, R., Becher, T., Frerichs, I., Sophocleous, L., van Kaam, A., Miedema, M., Seifnaraghi, N., & Bayford, R. (2018). Optimized breath detection algorithm in electrical impedance tomography. *Physiological Measurement*, 39(9), 094001. https://doi.org/10.1088/1361-6579/aad7e6

> Charlton, P. H., Birrenkott, D. A., Bonnici, T., Pimentel, M. A. F., Johnson, A. E. W., Alastruey, J., Tarassenko, L., Watkinson, P. J., Beale, R., & Clifton, D. A. (2021). An impedance pneumography signal quality index: Design, assessment and application to respiratory rate monitoring. *Biomedical Signal Processing and Control*, 65, 102339. https://doi.org/10.1016/j.bspc.2020.102339

> Power, J. D., Lynch, C. J., Dubin, M. J., Silver, B. M., Martin, A., & Jones, R. M. (2020). Characteristics of respiratory measures in young adults scanned at rest, including systematic changes and 'missed' deep breaths. *NeuroImage*, 204, 116234.

### Peak/Trough Detection (`rsp_process` → `rsp_peaks`)

Respiratory peak and trough detection, and breath rate computation, use the Khodadad algorithm and secondary RSA-based rate estimation:

> Khodadad, D., et al. (2018). Optimized breath detection algorithm in electrical impedance tomography. *Physiological Measurement*, 39(9), 094001. https://doi.org/10.1088/1361-6579/aad7e6

> Schafer, A., & Kratky, K. W. (2008). Estimation of breathing rate from respiratory sinus arrhythmia: comparison of various methods. *Annals of Biomedical Engineering*, 36(3), 476–485.

---

## EDA — Electrodermal Activity

**Script:** `processing/process_acq_eda.py`
**Function:** `nk.eda_process()`
**Method parameter:** `method="neurokit"`

### Signal Cleaning (`eda_process` → `eda_clean`)

The `"neurokit"` EDA cleaning method applies a 3 Hz low-pass Butterworth filter, adapted from the BioSPPy EDA preprocessing pipeline:

> Carreiras, C., Alves, A. P., Lourenço, A., Canento, F., Silva, H., Fred, A., et al. (2015). *BioSPPy: Biosignal Processing in Python* [Software]. https://github.com/PIA-Group/BioSPPy

### Tonic/Phasic Decomposition (`eda_process` → `eda_phasic`)

EDA is decomposed into tonic (SCL) and phasic (SCR) components using the `"neurokit"` high-pass filtering method. The cvxEDA and SparsEDA methods (also available in NeuroKit2) are underpinned by:

> Greco, A., Valenza, G., & Scilingo, E. P. (2016). Evaluation of CDA and CvxEDA models. In *Advances in Electrodermal Activity Processing with Applications for Mental Health* (pp. 35–43). Springer International Publishing.

> Greco, A., Valenza, G., Lanata, A., Scilingo, E. P., & Citi, L. (2016). cvxEDA: A convex optimization approach to electrodermal activity processing. *IEEE Transactions on Biomedical Engineering*, 63(4), 797–804.

> Hernando-Gallego, F., Luengo, D., & Artés-Rodríguez, A. (2017). Feature extraction of galvanic skin responses by nonnegative sparse deconvolution. *IEEE Journal of Biomedical and Health Informatics*, 22(5), 1385–1394.

### SCR Peak Detection (`eda_process` → `eda_peaks`)

Skin conductance response (SCR) onset and peak detection uses adaptive thresholding methods from:

> Gamboa, H. (2008). *Multi-modal behavioral biometrics based on HCI and electrophysiology* [Doctoral dissertation, Universidade Técnica de Lisboa]. http://www.lx.it.pt/~afred/pub/thesisHugoGamboa.pdf

> Kim, K. H., Bang, S. W., & Kim, S. R. (2004). Emotion recognition system using short-term monitoring of physiological signals. *Medical and Biological Engineering and Computing*, 42(3), 419–427.

> Nabian, M., Yin, Y., Wormwood, J., Quigley, K. S., Barrett, L. F., & Ostadabbas, S. (2018). An open-source feature extraction tool for the analysis of peripheral physiological data. *IEEE Journal of Translational Engineering in Health and Medicine*, 6, 2800711.

> van Halem, S., Van Roekel, E., Kroencke, L., Kuper, N., & Denissen, J. (2020). Moments that matter? On the complexity of using triggers based on skin conductance to sample arousing events within an experience sampling framework. *European Journal of Personality*.

---

## EMG — Electromyography

**Script:** `processing/process_acq_emg.py`
**Function:** `nk.emg_process()`

### Signal Cleaning (`emg_process` → `emg_clean`)

The default EMG cleaning applies a 4th-order 100 Hz high-pass Butterworth filter followed by constant detrending, adapted from BioSPPy:

> Carreiras, C., Alves, A. P., Lourenço, A., Canento, F., Silva, H., Fred, A., et al. (2015). *BioSPPy: Biosignal Processing in Python* [Software]. https://github.com/PIA-Group/BioSPPy

### Amplitude Envelope (`emg_process` → `emg_amplitude`)

The linear amplitude envelope is computed using the Teager–Kaiser Energy operator:

> Li, X., Zhou, P., & Aruin, A. S. (2007). Teager–Kaiser energy operation of surface EMG improves muscle activity onset detection. *Annals of Biomedical Engineering*, 35(9), 1532–1538.

### Muscle Activation Detection (`emg_process` → `emg_activation`)

Muscle burst/activation detection uses an adaptive thresholding method from:

> Silva, H., Scherer, R., Sousa, J., & Londral, A. (2012). Towards improving the usability of electromyographic interfaces. In *Proceedings of the International Workshop on Symbiotic Interaction* (pp. 1–2).

---

## BP — Blood Pressure (treated as continuous waveform)

**Script:** `processing/process_acq_bp.py`
**Functions:** `nk.signal_filter()`, `nk.ppg_findpeaks()`, `nk.signal_rate()`

### Low-pass Filtering (`signal_filter`)

The BP signal is low-pass filtered (8 Hz cut-off, 4th-order Butterworth) to smooth noise while preserving absolute mmHg pressure values. The Savitzky–Golay filter variant available in `signal_filter` references:

> Sadeghi, M., & Behnia, F. (2018). Optimum window length of Savitzky-Golay filters with arbitrary order. *arXiv preprint*. https://arxiv.org/abs/1808.10489

### Systolic Peak Detection (`ppg_findpeaks`)

The BP waveform is treated as a PPG-like signal for systolic peak detection. The default `"elgendi"` method and multi-scale methods used by `ppg_findpeaks` are from:

> Elgendi, M., Norton, I., Brearley, M., Abbott, D., & Schuurmans, D. (2013). Systolic peak detection in acceleration photoplethysmograms measured from emergency responders in tropical conditions. *PLoS ONE*, 8(10), e76585. https://doi.org/10.1371/journal.pone.0076585

> Bishop, S. M., & Ercole, A. (2018). Multi-scale peak and trough detection optimised for periodic and quasi-periodic neuroscience data. In *Intracranial Pressure & Neuromonitoring XVI* (pp. 189–195). Springer International Publishing. https://doi.org/10.1007/978-3-319-65798-1_39

> Charlton, P. H., Pimentel, M. A. F., Couceiro, R., Mant, J., & Alastruey, J. (2025). The MSPTDfast photoplethysmography beat detection algorithm: design, benchmarking, and open-source distribution. *Physiological Measurement*, 46, 035002. https://doi.org/10.1088/1361-6579/adb89e

### Heart Rate from Peak Intervals (`signal_rate`)

`nk.signal_rate()` converts inter-peak intervals to an instantaneous rate signal using monotone cubic interpolation (to prevent physiologically implausible overshoots). No additional external citation is required beyond the primary NeuroKit2 paper above.

---

## Summary Table

| Modality | NK2 Function | Method | Key Citations |
|----------|-------------|--------|---------------|
| ECG | `ecg_clean` | `neurokit` | Pan & Tompkins (1985); Engelse & Zeelenberg (1979) |
| ECG | `ecg_process` → peaks | `neurokit` | Christov (2004); Gamboa (2008); Koka & Muma (2022) |
| ECG | `ecg_process` → quality | — | Zhao & Zhang (2018); Orphanidou et al. (2015) |
| RSP | `rsp_process` → clean | `khodadad2018` | Khodadad et al. (2018) |
| RSP | `rsp_process` → peaks | `khodadad2018` | Khodadad et al. (2018); Schafer & Kratky (2008) |
| EDA | `eda_process` → clean | `neurokit` | BioSPPy (Carreiras et al., 2015) |
| EDA | `eda_process` → phasic | `neurokit` | Greco et al. (2016); Hernando-Gallego et al. (2017) |
| EDA | `eda_process` → peaks | — | Gamboa (2008); Kim et al. (2004); Nabian et al. (2018) |
| EMG | `emg_process` → clean | default | BioSPPy (Carreiras et al., 2015) |
| EMG | `emg_process` → amplitude | — | Li et al. (2007) |
| EMG | `emg_process` → activation | — | Silva et al. (2012) |
| BP | `signal_filter` | butterworth | — |
| BP | `ppg_findpeaks` | default | Elgendi et al. (2013); Bishop & Ercole (2018) |
| BP | `signal_rate` | — | Makowski et al. (2021) |
