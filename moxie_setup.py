#!/usr/bin/env python3
"""
MOXIE GitHub Research Infrastructure Setup
Sets up moxie-pipeline and moxie-analysis repos with labels, milestones,
issue templates, folder structure, starter issues, and a GitHub Project board.
"""

import os
import sys
import json
import time
import base64
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = "adityabn6"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
BASE = "https://api.github.com"

# ── tracking ──────────────────────────────────────────────────────────────────
results = {
    "pipeline_repo": None,
    "analysis_repo": None,
    "labels_pipeline": {"ok": 0, "total": 28},
    "labels_analysis": {"ok": 0, "total": 28},
    "milestones": {"ok": 0, "total": 10, "map": {}},  # title → number
    "templates": {"research_question": False, "milestone_task": False, "manuscript": False},
    "issues": [],
    "project": {"id": None, "url": None, "fields": 0, "views": 0, "linked": 0, "issues_added": 0},
}


def sleep(s=0.15):
    time.sleep(s)


def api(method, path, **kwargs):
    url = path if path.startswith("http") else f"{BASE}{path}"
    r = getattr(requests, method)(url, headers=HEADERS, **kwargs)
    sleep()
    return r


def graphql(query, variables=None):
    r = requests.post(
        "https://api.github.com/graphql",
        headers={**HEADERS, "Accept": "application/json"},
        json={"query": query, "variables": variables or {}},
    )
    sleep()
    return r.json()


def b64(s):
    return base64.b64encode(s.encode()).decode()


def months_from_today(n):
    today = datetime(2026, 3, 2)
    future = today + relativedelta(months=n)
    return future.strftime("%Y-%m-%dT00:00:00Z")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — REPOSITORIES
# ══════════════════════════════════════════════════════════════════════════════

PIPELINE_README = """# MOXIE Pipeline

Signal processing, QC, and feature extraction pipeline for the MOXIE physiological data study.

## Devices Supported
- **Acqknowledge (Biopac):** ECG, EDA, Respiration (Thoracic + Abdominal), Blood Pressure, EMG
- **Hexoskin:** ECG, Respiration (Thoracic + Abdominal)

## Pipeline Layers
1. **Layer 1 — Event Extraction:** Extract digital markers from .acq files, create output directory structure
2. **Layer 2 — Signal Processing:** Clean and process raw signals (filtering, peak detection, artifact removal)
3. **Layer 3 — Feature Extraction:** Extract windowed (1s) and event-based physiological features
4. **Layer 4 — QC:** Verification scripts and quality plots per modality

## Execution
Pipeline is designed for the University of Michigan Greatlakes Slurm cluster using Open OnDemand Job Composer. See `workflows/` for submission scripts.

## Setup
```bash
pip install -r requirements.txt
python utils/generate_catalog.py
```
"""

ANALYSIS_README = """# MOXIE Analysis

Research analysis, statistical modeling, and manuscript code for the MOXIE stress physiology study.

## Research Tracks

### Track 1: Breathing Characterization (Highest Priority)
Developing an ECG-like understanding of the breathing waveform, stress-related changes, and multi-signal integration.

### Track 2: Arousal vs Valence Distinction
Disentangling stress arousal across the range of valence using psychophysiological signals.

### Track 3: ANS Digital Twin (Longer Horizon)
Differential equations, agent-based modeling, RL-based biofeedback for autonomic nervous system simulation.

## Structure
```
analysis/
├── track1_breathing/
├── track2_arousal_valence/
├── track3_digital_twin/
├── shared/               # Shared utilities across tracks
└── notebooks/            # Exploratory analysis notebooks
```
"""


def create_repo(name, description, topics):
    print(f"\n[Step 1] Checking/creating repo: {name}")
    r = api("get", f"/repos/{USERNAME}/{name}")
    if r.status_code == 200:
        print(f"  → repo already exists, skipping creation")
        return r.json()["html_url"]

    payload = {
        "name": name,
        "description": description,
        "private": True,
        "has_issues": True,
        "has_projects": True,
        "auto_init": False,
    }
    r = api("post", "/user/repos", json=payload)
    if r.status_code not in (200, 201):
        print(f"  ✗ Failed to create {name}: {r.status_code} {r.text}")
        return None
    url = r.json()["html_url"]
    print(f"  ✓ Created: {url}")
    sleep(1)

    # Set topics
    topics_headers = {**HEADERS, "Accept": "application/vnd.github.mercy-preview+json"}
    r2 = requests.put(
        f"{BASE}/repos/{USERNAME}/{name}/topics",
        headers=topics_headers,
        json={"names": topics},
    )
    sleep()
    if r2.status_code == 200:
        print(f"  ✓ Topics set")

    return url


def init_readme(name, content):
    print(f"  Initializing README for {name}...")
    r = api("get", f"/repos/{USERNAME}/{name}/contents/README.md")
    if r.status_code == 200:
        print(f"  → README already exists")
        return
    payload = {
        "message": "chore: initialize repository with README",
        "content": b64(content),
    }
    r = api("put", f"/repos/{USERNAME}/{name}/contents/README.md", json=payload)
    if r.status_code in (200, 201):
        print(f"  ✓ README created")
    else:
        print(f"  ✗ README failed: {r.status_code} {r.text[:200]}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — LABELS
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_LABELS = [
    "bug", "documentation", "duplicate", "enhancement",
    "good first issue", "help wanted", "invalid", "question", "wontfix"
]

MOXIE_LABELS = [
    # TRACK
    ("track: breathing",        "0D3B66", "Project 1 — Breathing characterization & stress response"),
    ("track: arousal-valence",  "7B2D8B", "Project 2 — Arousal vs valence distinction"),
    ("track: digital-twin",     "1A5C38", "Project 3 — ANS digital twin (ODE, RL, biofeedback)"),
    ("track: pipeline",         "4A4A4A", "Data processing, QC, and infrastructure work"),
    # TYPE
    ("type: research-question", "E05C00", "A specific scientific question to be answered"),
    ("type: manuscript",        "C0392B", "A paper being planned, written, or submitted"),
    ("type: analysis",          "E67E22", "Code, statistics, or modeling work"),
    ("type: literature",        "F39C12", "Literature review or reading task"),
    ("type: infrastructure",    "D4AC0D", "Pipeline, tooling, or compute setup"),
    ("type: meeting-outcome",   "B7950B", "Action item arising from a meeting"),
    # PHASE
    ("phase: scoping",    "AED6F1", "Question not yet fully defined — in planning"),
    ("phase: data-prep",  "5DADE2", "Waiting on or actively preparing data/pipeline output"),
    ("phase: analysis",   "2E86C1", "Active analysis or coding in progress"),
    ("phase: writing",    "1A5276", "Manuscript, report, or documentation writing"),
    ("phase: review",     "0E3460", "Under internal or external review"),
    # SIGNAL
    ("signal: RSP",   "A9DFBF", "Respiration (Acqknowledge thoracic/abdominal or Hexoskin)"),
    ("signal: ECG",   "52BE80", "Electrocardiogram / HRV (Acqknowledge or Hexoskin)"),
    ("signal: EDA",   "1E8449", "Electrodermal activity / skin conductance"),
    ("signal: BP",    "145A32", "Blood pressure (NIBP continuous waveform)"),
    ("signal: EMG",   "7DCEA0", "Electromyography (zygomatic / corrugator)"),
    ("signal: multi", "0B5345", "Analysis involving 2 or more signals together"),
    # PRIORITY
    ("P1: critical", "B03A2E", "Must happen now — blocks other work or upcoming deadline"),
    ("P2: high",     "E59866", "Important, scheduled for current quarter"),
    ("P3: backlog",  "F9E79F", "Planned but not yet scheduled"),
    # FLAGS
    ("blocked: waiting-data",   "D7BDE2", "Blocked — needs pipeline output or raw data to exist first"),
    ("blocked: waiting-person", "C39BD3", "Blocked — waiting on collaborator, PI, or external party"),
    ("needs-decision",          "F1948A", "Requires supervisor input or team decision before proceeding"),
    ("cherry-pick",             "F8C8D4", "High-potential opportunity to revisit when resources allow"),
]


def setup_labels(repo):
    print(f"\n[Step 2] Setting up labels on {repo}")
    ok = 0

    # Delete default labels
    for name in DEFAULT_LABELS:
        encoded = requests.utils.quote(name, safe="")
        r = api("delete", f"/repos/{USERNAME}/{repo}/labels/{encoded}")
        if r.status_code in (204, 404):
            pass  # deleted or didn't exist
        sleep(0.1)

    # Get existing custom labels to avoid duplicates
    r = api("get", f"/repos/{USERNAME}/{repo}/labels?per_page=100")
    existing = {l["name"] for l in r.json()} if r.status_code == 200 else set()

    for name, color, desc in MOXIE_LABELS:
        if name in existing:
            # Update it
            encoded = requests.utils.quote(name, safe="")
            r = api("patch", f"/repos/{USERNAME}/{repo}/labels/{encoded}",
                    json={"color": color, "description": desc})
            if r.status_code == 200:
                ok += 1
            else:
                print(f"  ✗ Update failed for '{name}': {r.status_code}")
        else:
            r = api("post", f"/repos/{USERNAME}/{repo}/labels",
                    json={"name": name, "color": color, "description": desc})
            if r.status_code in (200, 201):
                ok += 1
            elif r.status_code == 422:
                # Already exists
                ok += 1
            else:
                print(f"  ✗ Create failed for '{name}': {r.status_code} {r.text[:100]}")

    print(f"  ✓ {ok}/{len(MOXIE_LABELS)} labels ready on {repo}")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — MILESTONES
# ══════════════════════════════════════════════════════════════════════════════

MILESTONES = [
    # Track 1 — Breathing
    ("B-M1: Feature Set Defined",
     "The vocabulary of breathing waveform features is established — analogous to ECG feature sets. "
     "Includes jaggedness metrics, phase ratios, amplitude features, and waveform shape descriptors. "
     "Agreement from PI required to close.",
     3),
    ("B-M2: Stress Response Analysis Complete",
     "Analysis of how breathing features change under TSST and PDST conditions. Statistical comparisons "
     "across conditions (Baseline, Speech, Arithmetic, Recovery). Includes effect sizes and visualizations.",
     6),
    ("B-M3: Multi-Signal Integration Complete",
     "Analysis of congruence and relationships between breathing and other signals (ECG/HRV, EDA, BP) "
     "under stress. Breathing's added value for stress detection/classification quantified.",
     9),
    ("B-M4: Manuscript 1 Submitted",
     "First manuscript submitted — breathing characterization and stress response. Target journal TBD with PI.",
     12),
    # Track 2 — Arousal vs Valence
    ("AV-M1: Literature Review Complete",
     "Systematic review of arousal-valence frameworks in psychophysiology. Key papers identified, "
     "framework selected for analysis approach.",
     4),
    ("AV-M2: Expert Consultation Complete",
     "Consultation with psychophysiology expert(s) for methodological guidance on disentangling arousal and valence.",
     6),
    ("AV-M3: Exploratory Analysis Complete",
     "Initial exploration of whether MOXIE signals can disentangle stress arousal across valence range. "
     "Decision point on whether full study is feasible.",
     10),
    # Track 3 — Digital Twin
    ("DT-M1: ODE Model Prototype",
     "Differential equation model of ANS dynamics prototyped and validated against a subset of MOXIE data.",
     8),
    ("DT-M2: RL Agent Baseline",
     "Reinforcement learning agent trained on MOXIE feature dataset (State: ECG+EDA, Action: RSP phase, "
     "Reward: BP). Baseline performance documented.",
     12),
    ("DT-M3: Biofeedback Simulation Demo",
     "End-to-end biofeedback simulation demonstrating the digital twin concept. Demo-able prototype.",
     18),
]


def create_milestones(repo):
    print(f"\n[Step 3] Creating milestones on {repo}")
    ok = 0

    # Get existing milestones
    r = api("get", f"/repos/{USERNAME}/{repo}/milestones?state=all&per_page=100")
    existing = {}
    if r.status_code == 200:
        for m in r.json():
            existing[m["title"]] = m["number"]

    for title, desc, months in MILESTONES:
        if title in existing:
            print(f"  → milestone '{title}' already exists (#{existing[title]})")
            results["milestones"]["map"][title] = existing[title]
            ok += 1
            continue
        due = months_from_today(months)
        r = api("post", f"/repos/{USERNAME}/{repo}/milestones",
                json={"title": title, "description": desc, "due_on": due})
        if r.status_code in (200, 201):
            num = r.json()["number"]
            results["milestones"]["map"][title] = num
            ok += 1
            print(f"  ✓ #{num} {title}")
        else:
            print(f"  ✗ Failed: {title}: {r.status_code} {r.text[:200]}")

    print(f"  ✓ {ok}/{len(MILESTONES)} milestones created")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — ISSUE TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

TEMPLATE_RQ = """\
---
name: Research Question
about: Define a specific scientific question for MOXIE analysis
title: "[QUESTION] "
labels: ["type: research-question", "phase: scoping"]
assignees: ''
---

## The Question
*State the question in one clear sentence.*


## Hypothesis
*What do you expect to find, and why?*


## Required Data / Signals
- [ ] RSP
- [ ] ECG / HRV
- [ ] EDA
- [ ] BP
- [ ] EMG
- [ ] Multi-signal

**Visit types needed:** TSST / PDST / Both

**Pipeline dependency:** Does the processing pipeline need to be complete first? What specific output files are needed?


## Analysis Approach
*Briefly describe the statistical or computational method.*


## Success Criteria
*How will you know this question is answered? What would a positive result look like? A negative result?*


## Potential Manuscript
*Does this question contribute to a specific paper? Which one?*


## Notes / References
*Any relevant papers, prior work, or PI comments.*
"""

TEMPLATE_MT = """\
---
name: Milestone Task
about: A concrete piece of work that moves a milestone forward
title: "[TASK] "
labels: "phase: scoping"
assignees: ''
---

## Parent Milestone
*Which milestone does this task contribute to? (e.g., B-M1: Feature Set Defined)*


## What Needs to Be Done
*Clear description of the work. Be specific enough that someone else could pick this up.*


## Definition of Done
*How do you know this task is complete? What is the deliverable?*
- [ ]
- [ ]


## Dependencies
*What must exist or be complete before this task can start?*


## Estimated Effort
- [ ] Small (< 4 hours)
- [ ] Medium (1-3 days)
- [ ] Large (1-2 weeks)
- [ ] Needs scoping


## Signals / Data Involved
*Which processed files or features does this task use?*


## Notes
"""

TEMPLATE_MS = """\
---
name: Manuscript
about: Track a paper from concept to submission
title: "[PAPER] "
labels: ["type: manuscript", "phase: scoping"]
assignees: ''
---

## Working Title


## Research Track
- [ ] Track 1: Breathing Characterization
- [ ] Track 2: Arousal vs Valence
- [ ] Track 3: ANS Digital Twin

## Target Journal (if known)


## Authors (planned)


## Core Questions This Paper Answers
1.
2.
3.

## Required Data & Pipeline Outputs
*What processed files, feature CSVs, or analyses must exist before writing can begin?*


## Key Figures Planned
1.
2.
3.

## Current Status
- [ ] Question defined
- [ ] Analysis complete
- [ ] Figures complete
- [ ] First draft
- [ ] Internal review
- [ ] Submitted
- [ ] Under review
- [ ] Accepted

## Target Submission Date


## Notes / PI Comments
"""


def create_issue_templates(repo):
    print(f"\n[Step 4] Creating issue templates on {repo}")

    templates = [
        (".github/ISSUE_TEMPLATE/research_question.md", TEMPLATE_RQ, "research_question"),
        (".github/ISSUE_TEMPLATE/milestone_task.md",    TEMPLATE_MT, "milestone_task"),
        (".github/ISSUE_TEMPLATE/manuscript.md",         TEMPLATE_MS, "manuscript"),
    ]

    for path, content, key in templates:
        r = api("get", f"/repos/{USERNAME}/{repo}/contents/{path}")
        if r.status_code == 200:
            print(f"  → {path} already exists")
            results["templates"][key] = True
            continue
        payload = {
            "message": "chore: add issue templates",
            "content": b64(content),
        }
        r = api("put", f"/repos/{USERNAME}/{repo}/contents/{path}", json=payload)
        if r.status_code in (200, 201):
            print(f"  ✓ {path}")
            results["templates"][key] = True
        else:
            print(f"  ✗ {path}: {r.status_code} {r.text[:200]}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — FOLDER STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

GITIGNORE = """\
# Data (never commit patient data)
data/processed/
data/features/
data/raw/
*.csv
*.acq

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Jupyter
.ipynb_checkpoints/

# OS
.DS_Store
.vscode/
"""

FOLDER_FILES = [
    ("analysis/track1_breathing/.gitkeep",    ""),
    ("analysis/track2_arousal_valence/.gitkeep", ""),
    ("analysis/track3_digital_twin/.gitkeep", ""),
    ("analysis/shared/.gitkeep",              ""),
    ("notebooks/.gitkeep",                    ""),
    ("data/processed/.gitkeep",               ""),
    ("data/features/.gitkeep",                ""),
    ("figures/.gitkeep",                      ""),
    (".gitignore",                             GITIGNORE),
]


def create_folder_structure(repo):
    print(f"\n[Step 5] Creating folder structure on {repo}")

    # Get current tree SHA for batch commit
    # We'll do individual file creates instead (simpler)
    ok = 0
    for path, content in FOLDER_FILES:
        r = api("get", f"/repos/{USERNAME}/{repo}/contents/{path}")
        if r.status_code == 200:
            print(f"  → {path} already exists")
            ok += 1
            continue
        payload = {
            "message": "chore: initialize repo structure",
            "content": b64(content if content else ""),
        }
        r = api("put", f"/repos/{USERNAME}/{repo}/contents/{path}", json=payload)
        if r.status_code in (200, 201):
            print(f"  ✓ {path}")
            ok += 1
        else:
            print(f"  ✗ {path}: {r.status_code} {r.text[:150]}")
        sleep(0.2)

    print(f"  ✓ {ok}/{len(FOLDER_FILES)} files created")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — STARTER ISSUES
# ══════════════════════════════════════════════════════════════════════════════

ISSUES = [
    {
        "title": "Define breathing waveform feature vocabulary for MOXIE RSP data",
        "body": """\
## The Question
What features best characterize the breathing waveform in MOXIE RIP data, analogous to how ECG features (R-peaks, HRV, QRS duration) characterize cardiac activity?

## What We're Looking For
- Jaggedness / irregularity metrics
- Phase ratio features (already prototyped: Inhale/Exhale/Hold slope method)
- Amplitude and tidal volume proxies
- Waveform shape descriptors
- Inter-breath interval variability (analogous to HRV)

## Starting Point
The MOXIE pipeline already outputs: RSP_Clean, RSP_Rate, RSP_Amplitude, RSP_Phase, RSP_Peaks, RSP_Troughs, and slope-based phase ratios (RSP_Slope_Inhale_Ratio, RSP_Slope_Exhale_Ratio, RSP_Slope_Hold_Ratio, RSP_Slope_Dominant).

The question is: what additional features should we extract? What does the literature say about characterizing respiratory waveform morphology?

## Next Step
Literature review on respiratory signal feature extraction, then propose a feature set for PI review.
""",
        "labels": ["track: breathing", "type: research-question", "phase: scoping", "signal: RSP", "P1: critical"],
        "milestone": "B-M1: Feature Set Defined",
    },
    {
        "title": "Literature review — respiratory signal feature extraction methods",
        "body": """\
## Task
Survey existing literature on respiratory waveform feature extraction, focusing on:
1. Features used in stress/emotion research
2. Features from clinical respiratory monitoring
3. Any ECG-inspired approaches applied to breathing
4. Breath hold detection methods beyond slope-based approaches

## Deliverable
A summary document (can be a markdown file in `analysis/track1_breathing/`) listing candidate features with citations, organized by feature category.

## Relevant Context
We use RIP (Respiratory Inductance Plethysmography) belts via Biopac Acqknowledge — both thoracic and abdominal channels — and Hexoskin (thoracic and abdominal). Sampling rate 2000 Hz (Biopac) or 256 Hz (Hexoskin).
""",
        "labels": ["track: breathing", "type: literature", "phase: scoping", "signal: RSP", "P1: critical"],
        "milestone": "B-M1: Feature Set Defined",
    },
    {
        "title": "Define arousal-valence framework for MOXIE — literature review",
        "body": """\
## Task
Review the arousal-valence literature to determine the appropriate theoretical and analytical framework for Track 2.

Key questions:
- What is the current consensus on how physiological signals relate to arousal vs valence separately?
- What methods have been used to disentangle them?
- What would "success" look like in the MOXIE dataset — what signals or patterns would indicate we've separated arousal from valence?

## Starting Point
The TSST and PDST protocols differ in their emotional content (TSST = performance stress / social evaluation; PDST = trauma-focused). This may give us a natural experimental handle on valence while keeping arousal roughly comparable.
""",
        "labels": ["track: arousal-valence", "type: literature", "phase: scoping", "signal: multi", "P2: high"],
        "milestone": "AV-M1: Literature Review Complete",
    },
    {
        "title": "Cherry-pick — patient study breathing data opportunity",
        "body": """\
## Opportunity
Dr. Tewari's lab may have access to physiological data from a patient study. If so, the breathing characterization work from Track 1 could be applied or validated in a clinical population.

## What This Would Enable
- Cross-population validation of breathing features
- Potential second manuscript (clinical application)
- Stronger impact for Track 1 paper

## Status
This is a future opportunity — flag for PI discussion once Track 1 feature set is defined (B-M1).

## Action
Revisit this issue after B-M1 milestone is closed.
""",
        "labels": ["track: breathing", "type: research-question", "cherry-pick", "P3: backlog"],
        "milestone": None,
    },
    {
        "title": "Set up moxie-analysis repo structure and shared utilities",
        "body": """\
## Task
Initialize the analysis repository with the agreed folder structure and create shared utility functions that all three tracks will use.

## Deliverables
- [ ] Folder structure in place (track1, track2, track3, shared, notebooks, data, figures)
- [ ] `shared/load_features.py` — utility to load and merge feature CSVs from the pipeline output
- [ ] `shared/condition_labels.py` — mapping of TSST and PDST event markers to clean condition names
- [ ] `shared/plotting.py` — common figure style/theme for consistency across all manuscripts
- [ ] `requirements.txt` for the analysis repo (pandas, numpy, scipy, matplotlib, seaborn, statsmodels, scikit-learn, pingouin)
""",
        "labels": ["track: pipeline", "type: infrastructure", "phase: scoping", "P1: critical"],
        "milestone": None,
    },
]


def create_issues(repo):
    print(f"\n[Step 6] Creating starter issues on {repo}")

    # Get existing issue titles
    r = api("get", f"/repos/{USERNAME}/{repo}/issues?state=all&per_page=100")
    existing_titles = set()
    if r.status_code == 200:
        existing_titles = {i["title"] for i in r.json()}

    for issue in ISSUES:
        if issue["title"] in existing_titles:
            print(f"  → Issue already exists: {issue['title'][:60]}")
            # Find its URL
            r2 = api("get", f"/repos/{USERNAME}/{repo}/issues?state=all&per_page=100")
            if r2.status_code == 200:
                for i in r2.json():
                    if i["title"] == issue["title"]:
                        results["issues"].append({"title": issue["title"], "url": i["html_url"], "number": i["number"]})
            continue

        payload = {
            "title": issue["title"],
            "body": issue["body"],
            "labels": issue["labels"],
        }
        if issue["milestone"] and issue["milestone"] in results["milestones"]["map"]:
            payload["milestone"] = results["milestones"]["map"][issue["milestone"]]

        r = api("post", f"/repos/{USERNAME}/{repo}/issues", json=payload)
        if r.status_code in (200, 201):
            data = r.json()
            url = data["html_url"]
            num = data["number"]
            results["issues"].append({"title": issue["title"], "url": url, "number": num})
            print(f"  ✓ #{num}: {issue['title'][:60]}")
        else:
            print(f"  ✗ Failed: {issue['title'][:60]}: {r.status_code} {r.text[:200]}")
            results["issues"].append({"title": issue["title"], "url": None, "number": None})


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — GITHUB PROJECT (v2 / GraphQL)
# ══════════════════════════════════════════════════════════════════════════════

def get_user_id():
    q = """query($login: String!) {
      user(login: $login) { id }
    }"""
    d = graphql(q, {"login": USERNAME})
    return d["data"]["user"]["id"]


def find_existing_project(owner_id):
    q = """query($login: String!) {
      user(login: $login) {
        projectsV2(first: 20) {
          nodes { id title url }
        }
      }
    }"""
    d = graphql(q, {"login": USERNAME})
    nodes = d.get("data", {}).get("user", {}).get("projectsV2", {}).get("nodes", [])
    for n in nodes:
        if n["title"] == "MOXIE Research":
            return n["id"], n["url"]
    return None, None


def create_project(owner_id):
    print(f"\n[Step 7] Creating GitHub Project board")
    existing_id, existing_url = find_existing_project(owner_id)
    if existing_id:
        print(f"  → Project already exists: {existing_url}")
        results["project"]["id"] = existing_id
        results["project"]["url"] = existing_url
        return existing_id

    q = """mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 { id url }
      }
    }"""
    d = graphql(q, {"ownerId": owner_id, "title": "MOXIE Research"})
    if "errors" in d:
        print(f"  ✗ Project creation failed: {d['errors']}")
        return None
    proj = d["data"]["createProjectV2"]["projectV2"]
    pid = proj["id"]
    url = proj["url"]
    results["project"]["id"] = pid
    results["project"]["url"] = url
    print(f"  ✓ Created project: {url}")

    # Update description via updateProjectV2
    q2 = """mutation($pid: ID!, $desc: String!) {
      updateProjectV2(input: {projectId: $pid, shortDescription: $desc}) {
        projectV2 { id }
      }
    }"""
    graphql(q2, {"pid": pid, "desc": "Unified planning board for all MOXIE research tracks — Breathing, Arousal/Valence, and ANS Digital Twin"})
    return pid


def add_field(pid, name, data_type, options=None):
    """Add a custom field. data_type: TEXT, DATE, SINGLE_SELECT"""
    if data_type == "SINGLE_SELECT" and options:
        q = """mutation($pid: ID!, $name: String!, $opts: [ProjectV2SingleSelectFieldOptionInput!]!) {
          createProjectV2Field(input: {projectId: $pid, name: $name, dataType: SINGLE_SELECT, singleSelectOptions: $opts}) {
            projectV2Field { ... on ProjectV2SingleSelectField { id name } }
          }
        }"""
        opts = [{"name": o, "color": "GRAY", "description": ""} for o in options]
        d = graphql(q, {"pid": pid, "name": name, "opts": opts})
    elif data_type == "TEXT":
        q = """mutation($pid: ID!, $name: String!) {
          createProjectV2Field(input: {projectId: $pid, name: $name, dataType: TEXT}) {
            projectV2Field { ... on ProjectV2Field { id name } }
          }
        }"""
        d = graphql(q, {"pid": pid, "name": name})
    elif data_type == "DATE":
        q = """mutation($pid: ID!, $name: String!) {
          createProjectV2Field(input: {projectId: $pid, name: $name, dataType: DATE}) {
            projectV2Field { ... on ProjectV2Field { id name } }
          }
        }"""
        d = graphql(q, {"pid": pid, "name": name})
    else:
        return False

    if "errors" in d:
        print(f"    ✗ Field '{name}': {d['errors'][0].get('message', d['errors'])}")
        return False
    print(f"    ✓ Field '{name}' created")
    return True


def create_project_fields(pid):
    print(f"  Creating custom fields...")
    fields_created = 0

    # Check existing fields
    q = """query($pid: ID!) {
      node(id: $pid) {
        ... on ProjectV2 {
          fields(first: 30) {
            nodes {
              ... on ProjectV2Field { name }
              ... on ProjectV2SingleSelectField { name }
              ... on ProjectV2IterationField { name }
            }
          }
        }
      }
    }"""
    d = graphql(q, {"pid": pid})
    existing_fields = set()
    try:
        for n in d["data"]["node"]["fields"]["nodes"]:
            if n.get("name"):
                existing_fields.add(n["name"])
    except Exception:
        pass

    field_defs = [
        ("Track",        "SINGLE_SELECT", ["Breathing", "Arousal-Valence", "Digital Twin", "Pipeline"]),
        ("Phase",        "SINGLE_SELECT", ["Scoping", "Data Prep", "Analysis", "Writing", "Review", "Done"]),
        ("Priority",     "SINGLE_SELECT", ["P1 Critical", "P2 High", "P3 Backlog"]),
        ("Effort",       "SINGLE_SELECT", ["Small", "Medium", "Large", "Needs Scoping"]),
        ("Manuscript",   "TEXT",          None),
        ("Target Date",  "DATE",          None),
    ]

    for name, dtype, opts in field_defs:
        if name in existing_fields:
            print(f"    → Field '{name}' already exists")
            fields_created += 1
            continue
        ok = add_field(pid, name, dtype, opts)
        if ok:
            fields_created += 1

    results["project"]["fields"] = fields_created
    print(f"  ✓ {fields_created}/6 fields ready")


def create_project_views(pid):
    print(f"  Creating project views...")
    # Views are created via GraphQL — note: the API has limited view customization
    # We create views by name; layout/grouping is best set in the UI
    views = [
        ("Roadmap",         "ROADMAP"),
        ("Active Sprint",   "BOARD"),
        ("By Track",        "TABLE"),
        ("By Person",       "TABLE"),
        ("Manuscripts",     "BOARD"),
    ]

    # Get existing views
    q = """query($pid: ID!) {
      node(id: $pid) {
        ... on ProjectV2 {
          views(first: 20) {
            nodes { name }
          }
        }
      }
    }"""
    d = graphql(q, {"pid": pid})
    existing_views = set()
    try:
        for v in d["data"]["node"]["views"]["nodes"]:
            existing_views.add(v["name"])
    except Exception:
        pass

    views_created = 0
    for name, layout in views:
        if name in existing_views:
            print(f"    → View '{name}' already exists")
            views_created += 1
            continue
        q2 = """mutation($pid: ID!, $name: String!, $layout: ProjectV2ViewLayout!) {
          addProjectV2View(input: {projectId: $pid, name: $name, layout: $layout}) {
            projectV2View { id name }
          }
        }"""
        d2 = graphql(q2, {"pid": pid, "name": name, "layout": layout})
        if "errors" in d2:
            print(f"    ✗ View '{name}': {d2['errors'][0].get('message', d2['errors'])}")
        else:
            views_created += 1
            print(f"    ✓ View '{name}' created")

    results["project"]["views"] = views_created
    print(f"  ✓ {views_created}/5 views ready")


def link_repo_to_project(pid, repo_name):
    """Link a repo to the project via GraphQL"""
    # First get the repo node ID
    q = """query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) { id }
    }"""
    d = graphql(q, {"owner": USERNAME, "name": repo_name})
    if "errors" in d or not d.get("data", {}).get("repository"):
        print(f"    ✗ Could not find repo {repo_name}: {d}")
        return False
    repo_id = d["data"]["repository"]["id"]

    # Link it
    q2 = """mutation($pid: ID!, $rid: ID!) {
      linkProjectV2ToRepository(input: {projectId: $pid, repositoryId: $rid}) {
        repository { name }
      }
    }"""
    d2 = graphql(q2, {"pid": pid, "rid": repo_id})
    if "errors" in d2:
        msg = d2["errors"][0].get("message", str(d2["errors"]))
        if "already" in msg.lower():
            print(f"    → {repo_name} already linked")
            return True
        print(f"    ✗ Link failed for {repo_name}: {msg}")
        return False
    print(f"    ✓ {repo_name} linked to project")
    return True


def add_issue_to_project(pid, repo_name, issue_number):
    """Add a repo issue to the project"""
    # Get issue node ID
    q = """query($owner: String!, $repo: String!, $num: Int!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $num) { id }
      }
    }"""
    d = graphql(q, {"owner": USERNAME, "repo": repo_name, "num": issue_number})
    if "errors" in d or not d.get("data", {}).get("repository", {}).get("issue"):
        print(f"    ✗ Could not find issue #{issue_number}: {d}")
        return False
    issue_id = d["data"]["repository"]["issue"]["id"]

    q2 = """mutation($pid: ID!, $cid: ID!) {
      addProjectV2ItemById(input: {projectId: $pid, contentId: $cid}) {
        item { id }
      }
    }"""
    d2 = graphql(q2, {"pid": pid, "cid": issue_id})
    if "errors" in d2:
        msg = d2["errors"][0].get("message", str(d2["errors"]))
        if "already" in msg.lower():
            return True
        print(f"    ✗ Add issue #{issue_number} failed: {msg}")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN not set")
        sys.exit(1)

    print("=" * 60)
    print("  MOXIE GitHub Infrastructure Setup")
    print("=" * 60)

    # ── Step 1: Repos ─────────────────────────────────────────────
    pipeline_url = create_repo(
        "moxie-pipeline",
        "Signal processing, QC, and feature extraction pipeline for MOXIE physiological data (Acqknowledge + Hexoskin)",
        ["physiological-data", "signal-processing", "neurokit2", "slurm", "bioinformatics"],
    )
    results["pipeline_repo"] = pipeline_url
    if pipeline_url:
        init_readme("moxie-pipeline", PIPELINE_README)

    analysis_url = create_repo(
        "moxie-analysis",
        "Research analysis, statistical modeling, and manuscript code for the MOXIE stress physiology study",
        ["stress-physiology", "hrv", "respiration", "reinforcement-learning", "bioinformatics", "psychophysiology"],
    )
    results["analysis_repo"] = analysis_url
    if analysis_url:
        init_readme("moxie-analysis", ANALYSIS_README)

    # ── Step 2: Labels ────────────────────────────────────────────
    results["labels_pipeline"]["ok"] = setup_labels("moxie-pipeline")
    results["labels_analysis"]["ok"] = setup_labels("moxie-analysis")

    # ── Step 3: Milestones ────────────────────────────────────────
    results["milestones"]["ok"] = create_milestones("moxie-analysis")

    # ── Step 4: Issue Templates ───────────────────────────────────
    create_issue_templates("moxie-analysis")

    # ── Step 5: Folder Structure ──────────────────────────────────
    create_folder_structure("moxie-analysis")

    # ── Step 6: Starter Issues ────────────────────────────────────
    create_issues("moxie-analysis")

    # ── Step 7: Project Board ─────────────────────────────────────
    print(f"\n[Step 7] GitHub Project Board (GraphQL)")
    owner_id = get_user_id()
    print(f"  User node ID: {owner_id}")

    pid = create_project(owner_id)
    if pid:
        create_project_fields(pid)
        create_project_views(pid)

        print(f"  Linking repos to project...")
        r1 = link_repo_to_project(pid, "moxie-pipeline")
        r2 = link_repo_to_project(pid, "moxie-analysis")
        results["project"]["linked"] = int(r1) + int(r2)

        print(f"  Adding issues to project...")
        added = 0
        for issue in results["issues"]:
            if issue.get("number"):
                ok = add_issue_to_project(pid, "moxie-analysis", issue["number"])
                if ok:
                    added += 1
                    print(f"    ✓ Added issue #{issue['number']}: {issue['title'][:50]}")
        results["project"]["issues_added"] = added

    # ── Step 8: Verification Report ───────────────────────────────
    print("\n")
    print("=" * 44)
    print("  MOXIE GitHub Setup — Verification")
    print("=" * 44)
    print()
    print("REPOSITORIES")
    tick = lambda v: "✓" if v else "✗"
    print(f"  {tick(results['pipeline_repo'])} moxie-pipeline created — {results['pipeline_repo'] or 'FAILED'}")
    print(f"  {tick(results['analysis_repo'])} moxie-analysis created — {results['analysis_repo'] or 'FAILED'}")
    print()
    print("LABELS (moxie-pipeline)")
    lp = results["labels_pipeline"]
    print(f"  {tick(lp['ok'] == lp['total'])} {lp['ok']}/{lp['total']} labels created successfully")
    print()
    print("LABELS (moxie-analysis)")
    la = results["labels_analysis"]
    print(f"  {tick(la['ok'] == la['total'])} {la['ok']}/{la['total']} labels created successfully")
    print()
    print("MILESTONES (moxie-analysis)")
    m = results["milestones"]
    print(f"  {tick(m['ok'] == m['total'])} {m['ok']}/{m['total']} milestones created")
    print()
    print("ISSUE TEMPLATES (moxie-analysis)")
    t = results["templates"]
    print(f"  {tick(t['research_question'])} research_question.md")
    print(f"  {tick(t['milestone_task'])} milestone_task.md")
    print(f"  {tick(t['manuscript'])} manuscript.md")
    print()
    print("STARTER ISSUES (moxie-analysis)")
    for i, issue in enumerate(results["issues"], 1):
        print(f"  {tick(issue.get('url'))} Issue {i}: {issue['title'][:55]} — {issue.get('url', 'FAILED')}")
    print()
    print("GITHUB PROJECT")
    p = results["project"]
    print(f"  {tick(p['id'])} 'MOXIE Research' project created — {p['url'] or 'FAILED'}")
    print(f"  {tick(p['fields'] >= 6)} {p['fields']}/6 custom fields added")
    print(f"  {tick(p['views'] >= 5)} {p['views']}/5 views configured")
    print(f"  {tick(p['linked'] == 2)} Both repos linked to project")
    print(f"  {tick(p['issues_added'] == 5)} {p['issues_added']}/5 starter issues added to project")
    print()
    print("=" * 44)
    print("  NEXT STEPS FOR ADITYA")
    print("=" * 44)
    print("1. Visit the Project board and set your name as assignee on the P1 issues")
    print("2. Share the project with your PI (Dr. Tewari) — Settings → Manage access")
    print("3. Invite other team members to both repos — Settings → Collaborators")
    print("4. In the Project board UI, set grouping and sort for each view:")
    print("   - Roadmap: Group by Track, Date field = Target Date")
    print("   - Active Sprint: Board layout, filter by assignees")
    print("   - By Track: Table, Group by Track, Sort by Priority")
    print("   - By Person: Table, Group by Assignee")
    print("   - Manuscripts: Board, Filter label = 'type: manuscript'")
    print("5. Once B-M1 scoping is done with PI, convert agreed questions into issues")
    print("   using the 'Research Question' issue template")
    print("=" * 44)


if __name__ == "__main__":
    main()
