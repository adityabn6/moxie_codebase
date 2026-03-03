#!/usr/bin/env python3
"""
MOXIE batch issue creation (moxie_issues.py)
============================================
Creates ~43 GitHub issues across moxie-pipeline and moxie-analyses,
then adds them all to the MOXIE Research project board.

Run:
    GITHUB_TOKEN=<pat> python3 moxie_issues.py

Requires:
    pip install requests python-dateutil
"""

import os, sys, json, time, requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

TOKEN    = os.environ.get("GITHUB_TOKEN", "")
USERNAME = "adityabn6"
BASE     = "https://api.github.com"
HEADERS  = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
GQL_HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Project board node ID (MOXIE Research — ProjectV2)
PROJECT_ID = "PVT_kwHOBxMK_84BQnGq"

# ── helpers ─────────────────────────────────────────────────────────────────

def sleep(s=0.2):
    time.sleep(s)

def api(method, path, **kwargs):
    url = path if path.startswith("http") else f"{BASE}{path}"
    r = getattr(requests, method)(url, headers=HEADERS, **kwargs)
    sleep()
    return r

def graphql(query, variables=None):
    r = requests.post(
        "https://api.github.com/graphql",
        headers=GQL_HDRS,
        json={"query": query, "variables": variables or {}},
    )
    sleep()
    return r.json()

def months_ahead(n):
    today = datetime.utcnow()
    return (today + relativedelta(months=n)).strftime("%Y-%m-%dT00:00:00Z")


# ── milestone helpers ────────────────────────────────────────────────────────

def ensure_milestones(repo, specs):
    """
    specs = [(title, description, months_ahead), ...]
    Returns {title: milestone_number}
    """
    print(f"\n[milestones] {repo}")
    r = api("get", f"/repos/{USERNAME}/{repo}/milestones?state=all&per_page=100")
    existing = {}
    if r.status_code == 200:
        for m in r.json():
            existing[m["title"]] = m["number"]

    ms_map = {}
    ok = 0
    for title, desc, months in specs:
        if title in existing:
            ms_map[title] = existing[title]
            print(f"  → already exists: {title}")
            ok += 1
            continue
        r2 = api("post", f"/repos/{USERNAME}/{repo}/milestones",
                 json={"title": title, "description": desc,
                       "due_on": months_ahead(months)})
        if r2.status_code in (200, 201):
            ms_map[title] = r2.json()["number"]
            print(f"  ✓ created: {title}")
            ok += 1
        else:
            print(f"  ✗ FAILED: {title} — {r2.status_code} {r2.text[:120]}")
    print(f"  {ok}/{len(specs)} milestones ready")
    return ms_map


# ── issue helpers ────────────────────────────────────────────────────────────

def create_issues(repo, issue_specs, ms_map):
    """
    issue_specs = list of dicts with keys: title, body, labels, milestone (title str or None)
    Returns list of issue numbers created (or already existing).
    """
    print(f"\n[issues] {repo}")
    # fetch existing to deduplicate
    existing = {}
    page = 1
    while True:
        r = api("get", f"/repos/{USERNAME}/{repo}/issues?state=all&per_page=100&page={page}")
        if r.status_code != 200 or not r.json():
            break
        for i in r.json():
            existing[i["title"]] = i["number"]
        if len(r.json()) < 100:
            break
        page += 1

    numbers = []
    ok = skip = fail = 0

    for spec in issue_specs:
        title = spec["title"]
        if title in existing:
            print(f"  → skip (exists) #{existing[title]}: {title[:65]}")
            numbers.append(existing[title])
            skip += 1
            continue

        payload = {
            "title": title,
            "body":  spec.get("body", ""),
            "labels": spec.get("labels", []),
        }
        ms_title = spec.get("milestone")
        if ms_title and ms_title in ms_map:
            payload["milestone"] = ms_map[ms_title]

        r2 = api("post", f"/repos/{USERNAME}/{repo}/issues", json=payload)
        if r2.status_code in (200, 201):
            num = r2.json()["number"]
            numbers.append(num)
            ok += 1
            print(f"  ✓ #{num}: {title[:65]}")
        else:
            print(f"  ✗ FAILED: {title[:55]} — {r2.status_code} {r2.text[:100]}")
            fail += 1

    print(f"  created={ok}  skipped={skip}  failed={fail}  total={len(numbers)}")
    return numbers


# ── project board helpers ────────────────────────────────────────────────────

def add_issues_to_project(repo, issue_numbers):
    print(f"\n[project] Adding {len(issue_numbers)} issues from {repo} to MOXIE Research board")
    added = skip = fail = 0
    for num in issue_numbers:
        # resolve issue node ID
        q = """query($owner:String!, $repo:String!, $num:Int!) {
          repository(owner:$owner, name:$repo) {
            issue(number:$num) { id }
          }
        }"""
        d = graphql(q, {"owner": USERNAME, "repo": repo, "num": num})
        issue_id = (d.get("data") or {}).get("repository", {}).get("issue", {}).get("id")
        if not issue_id:
            print(f"  ✗ could not resolve #{num}")
            fail += 1
            continue

        # add to project
        m = """mutation($pid:ID!, $cid:ID!) {
          addProjectV2ItemById(input:{projectId:$pid, contentId:$cid}) {
            item { id }
          }
        }"""
        d2 = graphql(m, {"pid": PROJECT_ID, "cid": issue_id})
        if "errors" in d2:
            msg = d2["errors"][0].get("message", "")
            if "already" in msg.lower():
                print(f"  → already in project #{num}")
                skip += 1
            else:
                print(f"  ✗ #{num}: {msg}")
                fail += 1
        else:
            print(f"  ✓ added #{num}")
            added += 1
    print(f"  added={added}  already_there={skip}  failed={fail}")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — moxie-pipeline milestones
# ════════════════════════════════════════════════════════════════════════════

PIPELINE_MILESTONES = [
    (
        "PI-M1: Layer 1 Processing Complete",
        "All subjects from TSST and PDST cohorts have been run through Layer 1 "
        "(raw Biopac/Hexoskin → clean signals). QC pass done. Ready for Layer 2.",
        4,
    ),
    (
        "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
        "All three pipeline layers complete. Per-subject, per-condition feature CSVs "
        "exported and validated. Analysis repos can begin consuming pipeline output.",
        8,
    ),
]


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — moxie-pipeline issues
# ════════════════════════════════════════════════════════════════════════════

PIPELINE_ISSUES = [

    # ── Layer 1 batch runs ─────────────────────────────────────────────────
    {
        "title": "Batch run Layer 1 — TSST cohort (all subjects)",
        "body": """\
## Goal
Run the full Layer 1 pipeline (raw Biopac AcqKnowledge → NeuroKit2 cleaned signals)
on every subject in the TSST cohort.

## Inputs
- Raw `.acq` files from TSST sessions (all visits)
- Subject list from metadata sheet

## Outputs
- Per-subject, per-visit cleaned signal CSVs in `data/processed/tsst/`
- Run log with pass/fail per subject

## Acceptance Criteria
- [ ] All subjects attempted
- [ ] Failed subjects documented with error reason
- [ ] Run log committed to `logs/layer1_tsst_run.log`

## Notes
Use `workflows/run_pipeline.py` with `--cohort tsst --layer 1`.
Check memory usage — some .acq files exceed 2 GB.
""",
        "labels": ["track: pipeline", "layer: 1-raw-to-clean", "type: batch-run",
                   "signal: multi", "P1: critical"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },
    {
        "title": "Batch run Layer 1 — PDST cohort (all subjects)",
        "body": """\
## Goal
Run Layer 1 pipeline on every subject in the PDST cohort.

## Inputs
- Raw `.acq` files from PDST sessions
- PDST subject list

## Outputs
- Per-subject cleaned signal CSVs in `data/processed/pdst/`
- Run log

## Acceptance Criteria
- [ ] All subjects attempted
- [ ] Failed subjects documented
- [ ] Log committed

## Notes
PDST protocol differs from TSST in stressor structure — verify event marker alignment
after processing for a subset of subjects before full run.
""",
        "labels": ["track: pipeline", "layer: 1-raw-to-clean", "type: batch-run",
                   "signal: multi", "P1: critical"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },
    {
        "title": "EMG artifact removal — integrate Cote-Allard filter into Layer 1",
        "body": """\
## Goal
Surface EMG contamination bleeds into ECG and RSP channels for some subjects.
Integrate a validated EMG artifact removal step into the Layer 1 pipeline.

## Background
Current pipeline uses NeuroKit2 default signal cleaning, which does not specifically
address EMG artifact. Some subjects show high-frequency contamination in RSP_Clean
and in ECG during speech tasks.

## Approach Options
1. Wavelet decomposition filter (Cote-Allard et al. 2019)
2. ICA-based separation on multi-channel Biopac data
3. Frequency-domain bandstop filter tuned to EMG spectrum (~20–500 Hz)

## Acceptance Criteria
- [ ] Method selected and documented in `docs/emg_artifact_removal.md`
- [ ] Implementation added to `processing/clean_signals.py`
- [ ] Validated on 3 known-bad subjects (visual inspection before/after)
- [ ] Added to Layer 1 batch run flags (`--emg-filter`)

## References
Cote-Allard et al. (2019) Deep learning for EMG-based gesture recognition.
""",
        "labels": ["track: pipeline", "layer: 1-raw-to-clean", "type: feature",
                   "signal: EMG", "P2: high"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },
    {
        "title": "Hexoskin wearable integration — validate RSP and HR outputs",
        "body": """\
## Goal
Ensure Hexoskin-derived respiratory and cardiac signals are correctly ingested
and time-aligned with Biopac data in the pipeline.

## Background
A subset of subjects wore the Hexoskin smart shirt (thoracic RSP + HR at ~256 Hz)
alongside Biopac. These provide an independent breathing signal and can validate
RIP belt data quality.

## Tasks
- [ ] Confirm Hexoskin CSV export format and column names
- [ ] Implement `processing/ingest_hexoskin.py` to standardize timestamps
- [ ] Time-align Hexoskin signals to Biopac recording start (cross-correlation or event-marker sync)
- [ ] Output merged DataFrame with `_biopac` and `_hexoskin` suffixes for shared signals
- [ ] Compare RSP_Rate from both sources for 5 subjects — report correlation

## Acceptance Criteria
- [ ] `ingest_hexoskin.py` handles all known export formats
- [ ] Time alignment error < 500 ms on 95% of subjects
- [ ] Comparison report in `docs/hexoskin_validation.md`
""",
        "labels": ["track: pipeline", "layer: 1-raw-to-clean", "type: feature",
                   "signal: RSP", "P2: high"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },

    # ── Layer 2 feature extraction ─────────────────────────────────────────
    {
        "title": "Batch run Layer 2 — feature extraction TSST cohort",
        "body": """\
## Goal
Run Layer 2 (cleaned signals → per-epoch, per-condition feature CSVs) on all
TSST subjects that passed Layer 1 QC.

## Inputs
- `data/processed/tsst/<subject_id>/` — Layer 1 output
- Event marker mapping for TSST conditions

## Outputs
- `data/features/tsst/<subject_id>/features.csv` with columns:
  subject_id, visit, condition, RSP_*, ECG_HRV_*, EDA_*, BP_*

## Acceptance Criteria
- [ ] All Layer-1-passing subjects processed
- [ ] Feature CSV schema matches agreed spec (`docs/feature_schema.md`)
- [ ] Run log committed

## Dependencies
- Layer 1 TSST batch (#<link>)
- Feature schema agreed with PI
""",
        "labels": ["track: pipeline", "layer: 2-features", "type: batch-run",
                   "signal: multi", "P1: critical"],
        "milestone": "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
    },
    {
        "title": "Batch run Layer 2 — feature extraction PDST cohort",
        "body": """\
## Goal
Run Layer 2 on all PDST subjects that passed Layer 1 QC.

## Outputs
- `data/features/pdst/<subject_id>/features.csv`

## Acceptance Criteria
- [ ] All Layer-1-passing PDST subjects processed
- [ ] Feature CSV schema matches TSST output schema (same columns)
- [ ] Run log committed

## Dependencies
- Layer 1 PDST batch (#<link>)
""",
        "labels": ["track: pipeline", "layer: 2-features", "type: batch-run",
                   "signal: multi", "P1: critical"],
        "milestone": "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
    },
    {
        "title": "QC pass — validate Layer 2 feature outputs for outliers and artifacts",
        "body": """\
## Goal
Run a systematic quality-control pass on all Layer 2 feature CSVs to flag:
- Physiologically implausible values (e.g., HR < 30 or > 220 bpm, RSP_Rate < 2 or > 60)
- Missing epochs (subjects with < N conditions represented)
- Flat signals (zero variance features indicating sensor dropout)

## Deliverables
- [ ] `verification/qc_features.py` — automated flag script
- [ ] `verification/qc_report.md` — per-subject, per-signal QC summary
- [ ] List of subjects/epochs to exclude from analysis

## Acceptance Criteria
- Outlier thresholds defined and documented
- QC report reviewed with PI before finalizing exclusions
""",
        "labels": ["track: pipeline", "layer: 2-features", "type: verification",
                   "signal: multi", "P1: critical"],
        "milestone": "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
    },
    {
        "title": "Data availability report — missing subjects and signal channels",
        "body": """\
## Goal
Generate a comprehensive data availability matrix showing, for every subject and
visit: which signals are present, which are missing, and which failed QC.

## Format
A heatmap or table:
- Rows: subjects × visits
- Columns: signal channels (ECG, RSP_biopac, RSP_hexoskin, EDA, BP_systolic,
  BP_diastolic, EMG_trapezius, Audio)
- Cell: ✓ present / ✗ missing / ⚠ failed QC

## Deliverables
- [ ] `verification/data_availability.py`
- [ ] `figures/data_availability_matrix.pdf`
- [ ] Summary in `docs/data_availability.md`

## Use
This report drives decisions about which analyses are powered and guides imputation
or exclusion strategies.
""",
        "labels": ["track: pipeline", "type: verification", "signal: multi", "P2: high"],
        "milestone": "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
    },

    # ── Layer 3 export ─────────────────────────────────────────────────────
    {
        "title": "Batch run Layer 3 — export merged feature CSVs for analysis",
        "body": """\
## Goal
Run Layer 3 (merge per-subject feature CSVs into a single analysis-ready dataset)
for both cohorts.

## Outputs
- `data/features/moxie_features_tsst.csv` — all subjects, all conditions (TSST)
- `data/features/moxie_features_pdst.csv` — all subjects, all conditions (PDST)
- `data/features/moxie_features_combined.csv` — both cohorts with cohort column

## Acceptance Criteria
- [ ] Combined CSV has agreed schema
- [ ] No subject-level data duplication
- [ ] Row counts match QC-passing subject × condition counts

## Notes
This CSV is the primary input for all moxie-analyses scripts.
""",
        "labels": ["track: pipeline", "layer: 3-export", "type: batch-run",
                   "signal: multi", "P1: critical"],
        "milestone": "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
    },

    # ── Supporting pipeline tasks ──────────────────────────────────────────
    {
        "title": "Audio/speech segment annotation — TSST speech task timestamps",
        "body": """\
## Goal
Extract and annotate the speech task segment timestamps from TSST recordings
to enable speech-specific physiological analysis.

## Background
The TSST includes a 5-minute speech preparation phase and 5-minute speech delivery.
The audio channel (if present) can be used to verify active speaking periods and
remove off-task intervals.

## Tasks
- [ ] Check which subjects have audio channel in Biopac recording
- [ ] Implement `processing/annotate_speech.py` using audio energy threshold
- [ ] Output: per-subject speech segment timestamps CSV
- [ ] Validate on 5 subjects with manual review

## Stretch Goal
Integrate speech detection confidence scores into QC flagging for speech-task epochs.
""",
        "labels": ["track: pipeline", "layer: 1-raw-to-clean", "type: feature",
                   "signal: audio", "P3: backlog"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },
    {
        "title": "Edge case handling — subjects with partial or split recordings",
        "body": """\
## Goal
Several subjects have split Biopac files (recording stopped and resumed mid-session)
or partial data (equipment failure during one condition). Implement robust handling.

## Tasks
- [ ] Catalog all known split/partial cases from lab notes
- [ ] Implement `processing/merge_splits.py` — concatenate and re-align event markers
- [ ] Implement `processing/handle_partial.py` — flag partial conditions, set to NaN
- [ ] Add edge-case integration tests in `verification/test_edge_cases.py`

## Acceptance Criteria
- [ ] All known split cases handled without data loss
- [ ] Partial conditions flagged in QC report (not silently excluded)
""",
        "labels": ["track: pipeline", "layer: 1-raw-to-clean", "type: bug",
                   "signal: multi", "P2: high"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },
    {
        "title": "Subject metadata consolidation — demographics, exclusions, counterbalancing",
        "body": """\
## Goal
Create a single, authoritative subject metadata file for MOXIE to be used
by all analysis scripts.

## Contents (target schema)
| Column | Description |
|--------|-------------|
| subject_id | anonymized ID |
| cohort | TSST / PDST |
| age | years |
| sex | M/F/Other |
| bmi | kg/m² |
| excluded | True/False |
| exclusion_reason | string |
| tsst_visit_order | 1/2/3 |
| pdst_visit_order | 1/2/3 |
| hexoskin | True/False |
| notes | freeform |

## Deliverables
- [ ] `data/metadata/subjects.csv` (committed without PHI — use subject IDs only)
- [ ] `docs/subject_metadata.md` — data dictionary
- [ ] `shared/load_metadata.py` in moxie-analyses — loads and merges with features

## Notes
Source from PI's REDCap export and lab notebook. Remove all direct identifiers
(name, DOB, MRN) before committing.
""",
        "labels": ["track: pipeline", "type: infrastructure", "signal: multi", "P2: high"],
        "milestone": "PI-M1: Layer 1 Processing Complete",
    },
    {
        "title": "Pipeline documentation — update methods section draft for manuscripts",
        "body": """\
## Goal
Write a reusable 'Methods: Data Acquisition and Processing' section that can be
adapted for all three MOXIE manuscripts.

## Content to Cover
1. Study protocol overview (TSST/PDST, visit structure)
2. Physiological data acquisition (Biopac channels, sampling rates, sensor placement)
3. Hexoskin wearable (subset of subjects)
4. Signal processing pipeline (Layer 1 — cleaning, Layer 2 — feature extraction)
5. QC procedures and exclusion criteria
6. Statistical analysis software and libraries (Python, NeuroKit2, MNE, pingouin)

## Deliverable
- `docs/methods_draft.md` — ~1500 words, ready to copy into manuscript

## Notes
Check with PI on preferred style — APA vs AMA. Match the target journal's methods
section length norms.
""",
        "labels": ["track: pipeline", "type: documentation", "signal: multi", "P2: high"],
        "milestone": "PI-M2: Full Pipeline Complete — Feature CSVs Ready",
    },
]


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — moxie-analyses additional issues
# (supplements the 5 starter issues created by moxie_patch.py)
# ════════════════════════════════════════════════════════════════════════════

ANALYSIS_ISSUES = [

    # ── Shared utilities ───────────────────────────────────────────────────
    {
        "title": "Implement shared/load_features.py — pipeline feature CSV loader",
        "body": """\
## Goal
Create the primary data-loading utility used by all analysis scripts.

## API (target)
```python
from shared.load_features import load_moxie

df = load_moxie(
    cohorts=["tsst", "pdst"],        # or just one
    signals=["RSP", "ECG_HRV"],      # column prefix filter; None = all
    conditions=["Baseline", "Speech", "Arithmetic", "Recovery"],
    exclude_qc_fails=True,           # uses QC flag from pipeline
)
```

## Acceptance Criteria
- [ ] Returns a tidy DataFrame: one row per (subject, visit, condition)
- [ ] Signal prefix filtering works correctly
- [ ] QC exclusion flag respected
- [ ] Docstring with usage example
- [ ] Unit tests in `tests/test_load_features.py`
""",
        "labels": ["track: pipeline", "type: infrastructure", "P1: critical"],
        "milestone": None,
    },
    {
        "title": "Implement shared/condition_labels.py — TSST/PDST event marker mapping",
        "body": """\
## Goal
Centralize the mapping from raw Biopac event marker codes to human-readable
condition names. Prevent hardcoded magic numbers scattered across analysis scripts.

## Contents
```python
TSST_MARKERS = {
    10: "Baseline_Rest",
    20: "Speech_Prep",
    30: "Speech_Delivery",
    40: "Arithmetic",
    50: "Recovery_1",
    60: "Recovery_2",
}
PDST_MARKERS = { ... }  # to be filled from lab notebook

def condition_from_marker(marker_code, cohort):
    ...
```

## Acceptance Criteria
- [ ] All known marker codes mapped (verify with PI / lab notebook)
- [ ] Handles unknown codes gracefully (returns None, logs warning)
- [ ] Docstring with marker code table
""",
        "labels": ["track: pipeline", "type: infrastructure", "P1: critical"],
        "milestone": None,
    },
    {
        "title": "Implement shared/plotting.py — consistent figure style for manuscripts",
        "body": """\
## Goal
Define a shared matplotlib/seaborn theme and helper functions so all MOXIE
figures look consistent across the three manuscripts.

## Contents
- `set_moxie_style()` — applies rcParams (font size, line width, DPI, color palette)
- `CONDITION_COLORS` — dict mapping condition name → color
- `TRACK_COLORS` — dict mapping track name → color
- `save_fig(fig, name)` — saves to `figures/<name>.pdf` and `.png` at 300 DPI
- `add_significance_bar(ax, x1, x2, y, p)` — draw *** bars

## Acceptance Criteria
- [ ] Style applied consistently across at least 3 test figures
- [ ] Color palette is colorblind-friendly (viridis or similar)
- [ ] Docstring with usage example
""",
        "labels": ["track: pipeline", "type: infrastructure", "P2: high"],
        "milestone": None,
    },

    # ── Track 1: Breathing Characterization ───────────────────────────────
    {
        "title": "[Track 1] Implement jaggedness and breathing irregularity metrics",
        "body": """\
## Goal
Implement the first set of novel breathing features: metrics that capture
waveform smoothness and regularity, analogous to HRV metrics for cardiac signals.

## Features to Implement
| Feature | Description | Formula / Method |
|---------|-------------|-----------------|
| `RSP_Jaggedness` | Mean absolute second derivative of waveform | `mean(|d²x/dt²|)` |
| `RSP_SampleEntropy` | Sample entropy of breath-by-breath IBI | from `antropy` library |
| `RSP_DFA_alpha1` | Short-range fractal scaling exponent | DFA on IBI series |
| `RSP_CoV_Rate` | Coefficient of variation of breathing rate | `std/mean` of RSP_Rate |
| `RSP_CoV_Amplitude` | CV of breath amplitude | `std/mean` of RSP_Amplitude |

## Acceptance Criteria
- [ ] Implemented in `track1_breathing/features/irregularity.py`
- [ ] Validated against known values for synthetic sine wave (should → 0 for all)
- [ ] Integrated into the feature extraction call chain

## Notes
`antropy` and `nolds` libraries for entropy and DFA. Add to `requirements.txt`.
""",
        "labels": ["track: breathing", "type: feature", "signal: RSP",
                   "phase: analysis", "P1: critical"],
        "milestone": "B-M1: Feature Set Defined",
    },
    {
        "title": "[Track 1] Implement phase ratio and breath-hold detection features",
        "body": """\
## Goal
Build on the slope-based phase detection already in the pipeline to extract
robust phase ratio and breath-hold features.

## Features to Implement
| Feature | Description |
|---------|-------------|
| `RSP_IE_Ratio` | Inhale/Exhale duration ratio per breath |
| `RSP_Hold_Fraction` | Fraction of total cycle time spent in hold phase |
| `RSP_Hold_Count` | Number of detectable holds per 60-second window |
| `RSP_Phase_Consistency` | Circular variance of phase at fixed time points |

## Background
The existing slope-based method (positive slope → Inhale, near-zero → Hold,
negative → Exhale) is prototyped. This issue is about extracting summary
statistics from those phase labels.

## Acceptance Criteria
- [ ] Implemented in `track1_breathing/features/phase_ratios.py`
- [ ] Handles edge cases: no detectable holds, very short breaths
- [ ] Unit tests with at least 3 synthetic waveform cases
""",
        "labels": ["track: breathing", "type: feature", "signal: RSP",
                   "phase: analysis", "P1: critical"],
        "milestone": "B-M1: Feature Set Defined",
    },
    {
        "title": "[Track 1] Compile final breathing feature set — PI review and sign-off",
        "body": """\
## Goal
Aggregate all candidate breathing features, run them on a sample of subjects,
and prepare a feature set proposal for PI review to close B-M1.

## Inputs
- `irregularity.py` output
- `phase_ratios.py` output
- Pipeline RSP_Rate, RSP_Amplitude, RSP_Peaks, RSP_Troughs
- Literature review summary

## Deliverable
A summary document `analysis/track1_breathing/B-M1_feature_set_proposal.md`:
- Table of all features with description, units, rationale
- Sample distributions (histograms) for Baseline condition
- Correlation matrix to check redundancy
- Recommendation: which features to prioritize

## Acceptance Criteria
- [ ] Document reviewed in lab meeting
- [ ] PI approves feature set or requests specific changes
- [ ] Milestone B-M1 closed after PI sign-off
""",
        "labels": ["track: breathing", "type: milestone-task", "signal: RSP",
                   "phase: scoping", "P1: critical"],
        "milestone": "B-M1: Feature Set Defined",
    },
    {
        "title": "[Track 1] Breathing features under stress — condition-level statistics",
        "body": """\
## Goal
Compute per-condition (Baseline / Speech / Arithmetic / Recovery) summary
statistics for all B-M1 breathing features and test for condition effects.

## Analysis Plan
1. Descriptive stats: mean ± SD per condition per feature
2. Mixed ANOVA: within-subjects (condition) × between-subjects (cohort: TSST/PDST)
3. Post-hoc paired comparisons: each stress condition vs Baseline
4. Effect sizes: Cohen's d with 95% CI

## Outputs
- `figures/track1/condition_means_breathing.pdf` — bar plots with error bars
- `figures/track1/anova_results.pdf` — table of F-stats, p-values, η²
- `analysis/track1_breathing/condition_stats.ipynb`

## Dependencies
- B-M1 feature set finalized (#<link>)
- Layer 2 feature CSVs for both cohorts
""",
        "labels": ["track: breathing", "type: analysis", "signal: RSP",
                   "phase: analysis", "P2: high"],
        "milestone": "B-M2: Stress Response Analysis Complete",
    },
    {
        "title": "[Track 1] Biopac vs Hexoskin RSP comparison — signal quality and feature agreement",
        "body": """\
## Goal
For the subset of subjects with both Biopac RIP and Hexoskin RSP, compare:
1. Raw signal quality (correlation, RMSE)
2. Feature-level agreement (RSP_Rate, RSP_Amplitude, IE_Ratio)
3. Identify whether Hexoskin can substitute for Biopac in certain analyses

## Analysis
- Bland-Altman plots for RSP_Rate
- Pearson r and ICC for each shared feature
- Note any systematic bias (Hexoskin tends to over-smooth vs Biopac 2000 Hz)

## Deliverables
- `analysis/track1_breathing/hexoskin_comparison.ipynb`
- `figures/track1/bland_altman_RSP_Rate.pdf`
- `docs/hexoskin_agreement.md` — 1-page summary for methods

## Dependencies
- Hexoskin integration issue in moxie-pipeline (#<link>)
""",
        "labels": ["track: breathing", "type: analysis", "signal: RSP",
                   "phase: analysis", "P2: high"],
        "milestone": "B-M2: Stress Response Analysis Complete",
    },
    {
        "title": "[Track 1] Multi-signal integration — breathing + HRV congruence",
        "body": """\
## Goal
Quantify the relationship between breathing features and cardiac HRV features
under stress. Does breathing mediate HRV changes, or do they respond independently?

## Key Questions
- Is the RSP_Rate × RMSSD relationship condition-dependent?
- Does respiratory sinus arrhythmia (RSA) magnitude vary by stress condition?
- Can a combined breathing + HRV feature outperform either alone for stress detection?

## Analysis
1. Correlation matrix: all RSP features × all HRV features, by condition
2. RSA computation: bandpass HRV at breathing frequency
3. Simple classification comparison: RSP-only vs HRV-only vs RSP+HRV features

## Deliverables
- `analysis/track1_breathing/multi_signal_integration.ipynb`
- `figures/track1/rsp_hrv_correlation_heatmap.pdf`
""",
        "labels": ["track: breathing", "type: analysis", "signal: multi",
                   "phase: analysis", "P2: high"],
        "milestone": "B-M3: Multi-Signal Integration Complete",
    },
    {
        "title": "[Track 1] Multi-signal integration — breathing + EDA analysis",
        "body": """\
## Goal
Characterize how electrodermal activity (EDA) and breathing co-vary under
stress, and whether EDA adds information beyond breathing alone.

## Analysis
1. Time-lagged cross-correlation: EDA vs RSP_Rate by condition
2. EDA tonic level vs RSP_Jaggedness correlation
3. Joint feature importance in a simple stress prediction model

## Deliverables
- `analysis/track1_breathing/breathing_eda_integration.ipynb`
- `figures/track1/eda_rsp_crosscorr.pdf`

## Dependencies
- EDA features in Layer 2 pipeline output (EDA_Tonic, EDA_Phasic, EDA_SCR_Rate)
""",
        "labels": ["track: breathing", "type: analysis", "signal: multi",
                   "phase: analysis", "P3: backlog"],
        "milestone": "B-M3: Multi-Signal Integration Complete",
    },
    {
        "title": "[Track 1] Manuscript 1 outline — breathing characterization paper",
        "body": """\
## Goal
Draft the outline for Manuscript 1: Breathing Waveform Characterization Under
Psychological Stress (working title).

## Proposed Structure
1. Abstract
2. Introduction: Why breathing features matter; ECG analogy; gap in literature
3. Methods: Participants, Protocol (TSST/PDST), Acquisition, Pipeline, Features, Stats
4. Results:
   a. Feature distributions at Baseline
   b. Condition effects (ANOVA results)
   c. Multi-signal integration (RSA, EDA)
5. Discussion: Novel features, clinical relevance, limitations
6. Conclusion

## Tasks
- [ ] Draft outline in `analysis/track1_breathing/manuscript1_outline.md`
- [ ] Identify target journals with PI (Psychophysiology, NeuroImage, Frontiers)
- [ ] Create manuscript tracking issue using 'Manuscript' issue template

## Dependencies
- B-M3 complete
""",
        "labels": ["track: breathing", "type: manuscript", "phase: writing",
                   "P2: high"],
        "milestone": "B-M4: Manuscript 1 Submitted",
    },

    # ── Track 2: Arousal vs Valence ────────────────────────────────────────
    {
        "title": "[Track 2] Expert consultation — identify psychophysiology collaborator",
        "body": """\
## Goal
Identify and contact an external expert in psychophysiology / affective science to
consult on the arousal-valence framework for Track 2.

## Background
Disentangling arousal and valence from physiological signals is methodologically
challenging. Expert guidance on framework selection will strengthen the analysis.

## Tasks
- [ ] Compile list of candidate experts from literature (authors of key AV-framework papers)
- [ ] Discuss with PI — identify whether existing collaborators have this expertise
- [ ] Draft consultation agenda: specific methodological questions to answer
- [ ] Schedule call/meeting

## Definition of Done
Meeting completed. Key methodological decisions recorded in
`analysis/track2_arousal_valence/AV-M2_consultation_notes.md`.
""",
        "labels": ["track: arousal-valence", "type: milestone-task", "phase: scoping",
                   "P2: high"],
        "milestone": "AV-M2: Expert Consultation Complete",
    },
    {
        "title": "[Track 2] Signal profiling — arousal markers under TSST vs PDST",
        "body": """\
## Goal
Profile candidate arousal-related signals across TSST and PDST conditions.
Both protocols are stressful (high arousal) but differ in emotional character.

## Candidate Arousal Signals
- Heart rate (HR_Mean, HR_Max)
- Skin conductance level (EDA_Tonic)
- SCR rate (EDA_SCR_Rate)
- Respiratory rate (RSP_Rate)
- BP Systolic

## Analysis
For each signal:
1. Baseline-normalized response by condition (TSST vs PDST)
2. Statistical comparison: t-test / Wilcoxon across cohorts
3. Visualization: violin plots or time-series mean ± CI

## Deliverables
- `analysis/track2_arousal_valence/arousal_profiling.ipynb`
- `figures/track2/arousal_signals_tsst_vs_pdst.pdf`
""",
        "labels": ["track: arousal-valence", "type: analysis", "signal: multi",
                   "phase: analysis", "P2: high"],
        "milestone": "AV-M3: Exploratory Analysis Complete",
    },
    {
        "title": "[Track 2] Signal profiling — identify candidate valence markers",
        "body": """\
## Goal
Survey the literature and existing MOXIE signals to identify candidate markers
that may capture the valence dimension (positivity vs negativity of emotional experience).

## Background
TSST and PDST are both stressful but differ in the social-evaluative component.
TSST involves performance evaluation (potentially more threatening); PDST involves
different social context. This creates a natural valence-adjacent contrast.

## Tasks
- [ ] Literature review: which signals differentiate valence in controlled lab studies?
- [ ] Check MOXIE signal inventory for overlap with literature candidates
- [ ] Profile all candidate signals for TSST vs PDST differences (same analysis as arousal)
- [ ] Document findings in `analysis/track2_arousal_valence/valence_candidates.md`

## Key Challenge
Valence is often less tractable from peripheral physiology alone.
Document null results honestly — they're publishable in this context.
""",
        "labels": ["track: arousal-valence", "type: analysis", "signal: multi",
                   "phase: analysis", "P2: high"],
        "milestone": "AV-M3: Exploratory Analysis Complete",
    },
    {
        "title": "[Track 2] Dimensionality reduction — can MOXIE signals separate arousal & valence?",
        "body": """\
## Goal
Apply dimensionality reduction to the full MOXIE feature set to test whether
the data naturally separates along arousal and valence axes.

## Approach
1. PCA on all features — do PC1/PC2 correspond to arousal/valence?
2. UMAP (non-linear) — condition-level clusters
3. Label by condition and cohort — look for TSST/PDST separation
4. Compute silhouette score for TSST vs PDST separation

## Deliverables
- `analysis/track2_arousal_valence/dim_reduction_exploratory.ipynb`
- `figures/track2/umap_conditions.pdf`
- `figures/track2/pca_biplot.pdf`

## Interpretation
If TSST and PDST cluster separately in the reduced space → signals carry
valence-relevant information. If not → different approach needed.
""",
        "labels": ["track: arousal-valence", "type: analysis", "signal: multi",
                   "phase: analysis", "P2: high"],
        "milestone": "AV-M3: Exploratory Analysis Complete",
    },
    {
        "title": "[Track 2] Track 2 feasibility report — is a full arousal-valence study warranted?",
        "body": """\
## Goal
Based on the exploratory analyses (signal profiling, dimensionality reduction,
expert consultation), produce a formal feasibility report for PI decision-making.

## Contents
1. Summary of arousal signals: effect sizes and significance for TSST vs PDST
2. Summary of valence candidates: what we found, what we didn't
3. Dimensionality reduction findings
4. Expert consultation insights
5. Recommendation: (a) pursue full Track 2, (b) downscope to one manuscript,
   (c) deprioritize given pipeline/breathing timeline

## Deliverable
`analysis/track2_arousal_valence/AV-M3_feasibility_report.md` — ~2000 words.
Present at lab meeting. PI decision recorded as comment on this issue.
""",
        "labels": ["track: arousal-valence", "type: milestone-task", "phase: scoping",
                   "P2: high"],
        "milestone": "AV-M3: Exploratory Analysis Complete",
    },

    # ── Track 3: ANS Digital Twin ──────────────────────────────────────────
    {
        "title": "[Track 3] Literature review — ODE models of autonomic nervous system dynamics",
        "body": """\
## Goal
Survey existing ODE and computational models of ANS dynamics relevant to the
MOXIE digital twin concept.

## Key Papers to Cover
- Sturis et al. (1991) — oscillatory model of insulin-glucose
- deBoer et al. (1987) — closed-loop model of cardiovascular rhythms
- Heldt et al. (2002) — cardiovascular model
- Recent ANS-stress ODE literature (2015–2025)
- RL for physiological control (2018–2025)

## Deliverable
`analysis/track3_digital_twin/literature_review.md` — annotated bibliography
with a proposed modeling framework section.

## Key Question
What state variables and parameters are most tractable given MOXIE's signal set
(ECG, EDA, RSP, BP)?
""",
        "labels": ["track: digital-twin", "type: literature", "signal: multi",
                   "phase: scoping", "P3: backlog"],
        "milestone": "DT-M1: ODE Model Prototype",
    },
    {
        "title": "[Track 3] Prototype ANS ODE model — state: HRV+EDA, output: RSP+BP",
        "body": """\
## Goal
Implement a minimal ODE model of ANS dynamics that can be fit to MOXIE data.

## Proposed Model Structure
```
d/dt [sympathetic_tone] = f(stressor_input, HRV, EDA, RSP_Rate)
d/dt [parasympathetic_tone] = g(sympathetic_tone, RSP_Phase)

Output:
  BP_systolic   ~ h1(sympathetic_tone)
  HR            ~ h2(sympathetic_tone, parasympathetic_tone)
  RSP_Rate      ~ h3(parasympathetic_tone)
  EDA_Tonic     ~ h4(sympathetic_tone)
```

## Implementation
- `scipy.integrate.solve_ivp` for ODE integration
- Start with 2-compartment model (sympathetic + parasympathetic)
- Validate on synthetic data first

## Deliverables
- `analysis/track3_digital_twin/ode_model.py`
- `analysis/track3_digital_twin/ode_prototype.ipynb`

## Acceptance Criteria
- [ ] Model produces physiologically plausible trajectories for sine-wave stressor
- [ ] Parameters have intuitive physiological interpretation
""",
        "labels": ["track: digital-twin", "type: feature", "signal: multi",
                   "phase: analysis", "P3: backlog"],
        "milestone": "DT-M1: ODE Model Prototype",
    },
    {
        "title": "[Track 3] ODE model parameter fitting — calibrate on MOXIE data",
        "body": """\
## Goal
Fit ODE model parameters to MOXIE subject data using optimization.

## Approach
1. Define cost function: sum of squared residuals between model output and observed signals
2. Optimize using `scipy.optimize.minimize` (L-BFGS-B) or MCMC (`emcee`)
3. Fit per-subject parameters — compute population-level distributions
4. Validate: hold out one visit, fit on others, predict held-out

## Deliverables
- `analysis/track3_digital_twin/parameter_fitting.ipynb`
- `figures/track3/model_fit_examples.pdf` — 3 example subjects
- Table of mean ± SD for each parameter across subjects

## Dependencies
- ODE model prototype (#<link>)
- Layer 2 feature CSVs
""",
        "labels": ["track: digital-twin", "type: analysis", "signal: multi",
                   "phase: analysis", "P3: backlog"],
        "milestone": "DT-M1: ODE Model Prototype",
    },
    {
        "title": "[Track 3] RL state-action-reward formulation for MOXIE biofeedback",
        "body": """\
## Goal
Formally define the reinforcement learning MDP for the MOXIE digital twin:
State, Action, Reward, and episode structure.

## Proposed MDP
| Component | Definition |
|-----------|------------|
| **State** | [HRV_RMSSD, EDA_Tonic, RSP_Rate, RSP_Phase, BP_Systolic_t-1] |
| **Action** | RSP_Phase target: {Inhale, Hold, Exhale} or continuous rate target |
| **Reward** | Δ(BP_Systolic) × -1 — decrease in BP = positive reward |
| **Episode** | One stress task condition window (~5 min) |
| **Transition** | ODE model integration (1 time step = 10 seconds) |

## Deliverable
`analysis/track3_digital_twin/rl_mdp_definition.md` — formal MDP description
with justification for each component choice. Present to PI for feedback.

## Questions to Resolve
- Should reward include EDA as a secondary objective?
- Continuous vs discrete action space?
- Single-subject or population-level RL?
""",
        "labels": ["track: digital-twin", "type: milestone-task", "signal: multi",
                   "phase: scoping", "P3: backlog"],
        "milestone": "DT-M2: RL Agent Baseline",
    },
    {
        "title": "[Track 3] RL feature dataset preparation — State/Action/Reward extraction",
        "body": """\
## Goal
Construct the tabular dataset needed to train the offline RL agent from MOXIE
physiological recordings.

## Dataset Schema
```
subject_id | condition | time_step | state_hrv | state_eda | state_rsp_rate |
state_rsp_phase | state_bp | action_rsp_phase | reward_bp_delta | next_state_...
```

## Steps
1. Segment all Layer 2 feature CSVs into 10-second time steps
2. Extract state features at each step (from feature CSVs)
3. Infer action from RSP_Phase label at that step
4. Compute reward: delta in BP_Systolic (next step minus current)
5. Stack into offline RL dataset

## Deliverables
- `analysis/track3_digital_twin/build_rl_dataset.py`
- `data/features/moxie_rl_dataset.csv` (generated, not committed — add to .gitignore)

## Dependencies
- MDP formulation issue (#<link>)
- Layer 2 + Layer 3 pipeline complete
""",
        "labels": ["track: digital-twin", "type: feature", "signal: multi",
                   "phase: analysis", "P3: backlog"],
        "milestone": "DT-M2: RL Agent Baseline",
    },
    {
        "title": "[Track 3] Train baseline RL agent — offline Q-learning on MOXIE dataset",
        "body": """\
## Goal
Train an initial offline RL agent on the MOXIE RL dataset and establish baseline
performance metrics.

## Approach
1. Start with Conservative Q-Learning (CQL) for offline RL (avoids out-of-distribution actions)
2. Use `d3rlpy` library for offline RL implementation
3. Evaluate: average return per episode, BP reduction vs behavior policy
4. Ablation: state features vs reward formulation

## Deliverables
- `analysis/track3_digital_twin/rl_training.ipynb`
- `analysis/track3_digital_twin/rl_baseline_results.md`
- Saved model checkpoints (if size permits)

## Acceptance Criteria
- [ ] Agent achieves positive return on held-out subjects
- [ ] Performance exceeds random policy baseline
- [ ] Results interpretable: which state features drive action selection?

## Dependencies
- RL dataset preparation (#<link>)
""",
        "labels": ["track: digital-twin", "type: analysis", "signal: multi",
                   "phase: analysis", "P3: backlog"],
        "milestone": "DT-M2: RL Agent Baseline",
    },
    {
        "title": "[Track 3] Biofeedback simulation prototype — closed-loop demo",
        "body": """\
## Goal
Build an end-to-end demo: given a simulated physiological state, the RL agent
recommends a breathing action, the ODE model simulates the response, and the
loop continues for one episode.

## Demo Components
1. ODE model as environment (from DT-M1)
2. RL agent policy (from DT-M2)
3. Simple visualization: state trajectories under agent vs random policy
4. Optional: interactive Jupyter widget for real-time simulation

## Deliverables
- `analysis/track3_digital_twin/biofeedback_demo.ipynb`
- `figures/track3/biofeedback_simulation.pdf` — trajectory comparison

## Milestone Criterion
Demo presentable to PI and/or at conference. Sufficient for a Demo track submission.
""",
        "labels": ["track: digital-twin", "type: feature", "signal: multi",
                   "phase: analysis", "P3: backlog"],
        "milestone": "DT-M3: Biofeedback Simulation Demo",
    },
    {
        "title": "[Track 3] Digital twin paper outline — define scope and target venue",
        "body": """\
## Goal
Draft the manuscript outline for the Track 3 digital twin paper and identify
the appropriate publication venue.

## Proposed Scope
- Introduce the ANS digital twin concept for biofeedback
- Describe ODE model and RL formulation
- Results: model fit, RL performance, simulation demo
- Discussion: biofeedback applications, limitations, future directions

## Target Venues (to discuss with PI)
- IEEE EMBC (Engineering in Medicine and Biology)
- Journal of Physiology / American Journal of Physiology
- npj Digital Medicine
- ICLR (if framed as offline RL contribution)

## Deliverable
`analysis/track3_digital_twin/manuscript_outline.md`
""",
        "labels": ["track: digital-twin", "type: manuscript", "phase: scoping",
                   "P3: backlog"],
        "milestone": "DT-M3: Biofeedback Simulation Demo",
    },
]


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.")
        print("Run:  GITHUB_TOKEN=<your-pat> python3 moxie_issues.py")
        sys.exit(1)

    print("=" * 60)
    print("  MOXIE Batch Issue Creation")
    print("=" * 60)
    print(f"  Pipeline issues : {len(PIPELINE_ISSUES)}")
    print(f"  Analysis issues : {len(ANALYSIS_ISSUES)}")
    print(f"  Total           : {len(PIPELINE_ISSUES) + len(ANALYSIS_ISSUES)}")
    print()

    all_pipeline_nums = []
    all_analysis_nums = []

    # ── moxie-pipeline ────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  REPO: moxie-pipeline")
    print("─" * 60)

    pipeline_ms = ensure_milestones("moxie-pipeline", PIPELINE_MILESTONES)
    pipeline_nums = create_issues("moxie-pipeline", PIPELINE_ISSUES, pipeline_ms)
    all_pipeline_nums.extend(pipeline_nums)

    # ── moxie-analyses ────────────────────────────────────────────────────
    # milestones already created by moxie_patch.py — just fetch them
    print("\n" + "─" * 60)
    print("  REPO: moxie-analyses  (milestones already exist)")
    print("─" * 60)

    # We need the milestone numbers for issues that reference them
    ANALYSIS_MILESTONE_SPECS = [
        ("B-M1: Feature Set Defined",                 "", 0),
        ("B-M2: Stress Response Analysis Complete",   "", 0),
        ("B-M3: Multi-Signal Integration Complete",   "", 0),
        ("B-M4: Manuscript 1 Submitted",              "", 0),
        ("AV-M1: Literature Review Complete",         "", 0),
        ("AV-M2: Expert Consultation Complete",       "", 0),
        ("AV-M3: Exploratory Analysis Complete",      "", 0),
        ("DT-M1: ODE Model Prototype",                "", 0),
        ("DT-M2: RL Agent Baseline",                  "", 0),
        ("DT-M3: Biofeedback Simulation Demo",        "", 0),
    ]
    # just fetch existing — months=0 means "today" but ensure_milestones will
    # skip creation if already present (all these exist from moxie_patch.py)
    analysis_ms = ensure_milestones("moxie-analyses", ANALYSIS_MILESTONE_SPECS)

    analysis_nums = create_issues("moxie-analyses", ANALYSIS_ISSUES, analysis_ms)
    all_analysis_nums.extend(analysis_nums)

    # ── Add all to project board ──────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  PROJECT BOARD: MOXIE Research")
    print("─" * 60)

    if all_pipeline_nums:
        add_issues_to_project("moxie-pipeline", all_pipeline_nums)
    if all_analysis_nums:
        add_issues_to_project("moxie-analyses", all_analysis_nums)

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  DONE")
    print("=" * 60)
    print(f"  moxie-pipeline issues : {len(all_pipeline_nums)}")
    print(f"  moxie-analyses issues  : {len(all_analysis_nums)}")
    print(f"  Total on project board : {len(all_pipeline_nums) + len(all_analysis_nums)}")
    print()
    print("  Next steps:")
    print("  1. Visit https://github.com/users/adityabn6/projects/8")
    print("     and verify all issues appear in the board")
    print("  2. Set Track field values on each issue card")
    print("  3. Assign issues to team members")
    print("  4. Share project with PI (Settings → Manage access)")
    print("=" * 60)


if __name__ == "__main__":
    main()
