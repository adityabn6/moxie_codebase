#!/usr/bin/env python3
"""
MOXIE patch:
  1. Create moxie-analyses repo with full infrastructure
  2. On project: delete Phase field, update Status options,
     unlink moxie-analysis, link moxie-analyses, add new issues
"""

import os, sys, json, time, base64, requests

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = "adityabn6"
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
BASE = "https://api.github.com"
PID = "PVT_kwHOBxMK_84BQnGq"   # MOXIE Research project node ID

# Field IDs from introspection
STATUS_FIELD_ID = "PVTSSF_lAHOBxMK_84BQnGqzg-ribw"
PHASE_FIELD_ID  = "PVTSSF_lAHOBxMK_84BQnGqzg-ricU"


def sleep(s=0.15): time.sleep(s)

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

def b64(s): return base64.b64encode(s.encode()).decode()


# ══════════════════════════════════════════════════════════════════════════════
# PART A — Update Status field options & delete Phase field
# ══════════════════════════════════════════════════════════════════════════════

def update_status_options():
    print("\n[A1] Updating Status field options...")
    # Replace Status options — provide options without IDs so GitHub replaces the full list
    new_options = [
        {"name": "Scoping",   "color": "BLUE",   "description": "Question not yet fully defined — in planning"},
        {"name": "Data Prep", "color": "PURPLE", "description": "Waiting on or actively preparing data/pipeline output"},
        {"name": "Analysis",  "color": "GREEN",  "description": "Active analysis or coding in progress"},
        {"name": "Writing",   "color": "YELLOW", "description": "Manuscript, report, or documentation writing"},
        {"name": "Review",    "color": "ORANGE", "description": "Under internal or external review"},
        {"name": "Done",      "color": "GREEN",  "description": "Complete"},
    ]
    q = """mutation($fid: ID!, $opts: [ProjectV2SingleSelectFieldOptionInput!]!) {
      updateProjectV2Field(input: {fieldId: $fid, singleSelectOptions: $opts}) {
        projectV2Field { ... on ProjectV2SingleSelectField { name options { id name } } }
      }
    }"""
    d = graphql(q, {"fid": STATUS_FIELD_ID, "opts": new_options})
    if "errors" in d:
        print(f"  ✗ {d['errors'][0].get('message', d['errors'])}")
        return False
    opts = d["data"]["updateProjectV2Field"]["projectV2Field"]["options"]
    print(f"  ✓ Status options: {[o['name'] for o in opts]}")
    return True


def delete_phase_field():
    print("\n[A2] Deleting Phase custom field...")
    q = """mutation($fid: ID!) {
      deleteProjectV2Field(input: {fieldId: $fid}) {
        projectV2Field { ... on ProjectV2SingleSelectField { name } }
      }
    }"""
    d = graphql(q, {"fid": PHASE_FIELD_ID})
    if "errors" in d:
        msg = d["errors"][0].get("message", str(d["errors"]))
        print(f"  ✗ {msg}")
        return False
    print("  ✓ Phase field deleted")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# PART B — Create moxie-analyses repo with full infrastructure
# ══════════════════════════════════════════════════════════════════════════════

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

DEFAULT_LABELS = [
    "bug", "documentation", "duplicate", "enhancement",
    "good first issue", "help wanted", "invalid", "question", "wontfix"
]

MOXIE_LABELS = [
    ("track: breathing",        "0D3B66", "Project 1 — Breathing characterization & stress response"),
    ("track: arousal-valence",  "7B2D8B", "Project 2 — Arousal vs valence distinction"),
    ("track: digital-twin",     "1A5C38", "Project 3 — ANS digital twin (ODE, RL, biofeedback)"),
    ("track: pipeline",         "4A4A4A", "Data processing, QC, and infrastructure work"),
    ("type: research-question", "E05C00", "A specific scientific question to be answered"),
    ("type: manuscript",        "C0392B", "A paper being planned, written, or submitted"),
    ("type: analysis",          "E67E22", "Code, statistics, or modeling work"),
    ("type: literature",        "F39C12", "Literature review or reading task"),
    ("type: infrastructure",    "D4AC0D", "Pipeline, tooling, or compute setup"),
    ("type: meeting-outcome",   "B7950B", "Action item arising from a meeting"),
    ("phase: scoping",          "AED6F1", "Question not yet fully defined — in planning"),
    ("phase: data-prep",        "5DADE2", "Waiting on or actively preparing data/pipeline output"),
    ("phase: analysis",         "2E86C1", "Active analysis or coding in progress"),
    ("phase: writing",          "1A5276", "Manuscript, report, or documentation writing"),
    ("phase: review",           "0E3460", "Under internal or external review"),
    ("signal: RSP",   "A9DFBF", "Respiration (Acqknowledge thoracic/abdominal or Hexoskin)"),
    ("signal: ECG",   "52BE80", "Electrocardiogram / HRV (Acqknowledge or Hexoskin)"),
    ("signal: EDA",   "1E8449", "Electrodermal activity / skin conductance"),
    ("signal: BP",    "145A32", "Blood pressure (NIBP continuous waveform)"),
    ("signal: EMG",   "7DCEA0", "Electromyography (zygomatic / corrugator)"),
    ("signal: multi", "0B5345", "Analysis involving 2 or more signals together"),
    ("P1: critical", "B03A2E", "Must happen now — blocks other work or upcoming deadline"),
    ("P2: high",     "E59866", "Important, scheduled for current quarter"),
    ("P3: backlog",  "F9E79F", "Planned but not yet scheduled"),
    ("blocked: waiting-data",   "D7BDE2", "Blocked — needs pipeline output or raw data to exist first"),
    ("blocked: waiting-person", "C39BD3", "Blocked — waiting on collaborator, PI, or external party"),
    ("needs-decision",          "F1948A", "Requires supervisor input or team decision before proceeding"),
    ("cherry-pick",             "F8C8D4", "High-potential opportunity to revisit when resources allow"),
]

MILESTONES = [
    ("B-M1: Feature Set Defined",
     "The vocabulary of breathing waveform features is established — analogous to ECG feature sets. "
     "Includes jaggedness metrics, phase ratios, amplitude features, and waveform shape descriptors. "
     "Agreement from PI required to close.", 3),
    ("B-M2: Stress Response Analysis Complete",
     "Analysis of how breathing features change under TSST and PDST conditions. Statistical comparisons "
     "across conditions (Baseline, Speech, Arithmetic, Recovery). Includes effect sizes and visualizations.", 6),
    ("B-M3: Multi-Signal Integration Complete",
     "Analysis of congruence and relationships between breathing and other signals (ECG/HRV, EDA, BP) "
     "under stress. Breathing's added value for stress detection/classification quantified.", 9),
    ("B-M4: Manuscript 1 Submitted",
     "First manuscript submitted — breathing characterization and stress response. Target journal TBD with PI.", 12),
    ("AV-M1: Literature Review Complete",
     "Systematic review of arousal-valence frameworks in psychophysiology. Key papers identified, "
     "framework selected for analysis approach.", 4),
    ("AV-M2: Expert Consultation Complete",
     "Consultation with psychophysiology expert(s) for methodological guidance on disentangling arousal and valence.", 6),
    ("AV-M3: Exploratory Analysis Complete",
     "Initial exploration of whether MOXIE signals can disentangle stress arousal across valence range. "
     "Decision point on whether full study is feasible.", 10),
    ("DT-M1: ODE Model Prototype",
     "Differential equation model of ANS dynamics prototyped and validated against a subset of MOXIE data.", 8),
    ("DT-M2: RL Agent Baseline",
     "Reinforcement learning agent trained on MOXIE feature dataset (State: ECG+EDA, Action: RSP phase, "
     "Reward: BP). Baseline performance documented.", 12),
    ("DT-M3: Biofeedback Simulation Demo",
     "End-to-end biofeedback simulation demonstrating the digital twin concept. Demo-able prototype.", 18),
]

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
labels: ["phase: scoping"]
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
The MOXIE pipeline already outputs: RSP_Clean, RSP_Rate, RSP_Amplitude, RSP_Phase, RSP_Peaks, RSP_Troughs, and slope-based phase ratios.

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
A summary document in `analysis/track1_breathing/` listing candidate features with citations.

## Relevant Context
RIP belts via Biopac Acqknowledge (thoracic and abdominal) and Hexoskin. Sampling rate 2000 Hz (Biopac) or 256 Hz (Hexoskin).
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
- What would "success" look like in the MOXIE dataset?

## Starting Point
TSST and PDST protocols differ in emotional content — this may give a natural experimental handle on valence.
""",
        "labels": ["track: arousal-valence", "type: literature", "phase: scoping", "signal: multi", "P2: high"],
        "milestone": "AV-M1: Literature Review Complete",
    },
    {
        "title": "Cherry-pick — patient study breathing data opportunity",
        "body": """\
## Opportunity
Dr. Tewari's lab may have access to physiological data from a patient study. The breathing characterization work from Track 1 could be applied or validated in a clinical population.

## What This Would Enable
- Cross-population validation of breathing features
- Potential second manuscript (clinical application)

## Action
Revisit after B-M1 milestone is closed.
""",
        "labels": ["track: breathing", "type: research-question", "cherry-pick", "P3: backlog"],
        "milestone": None,
    },
    {
        "title": "Set up moxie-analyses repo structure and shared utilities",
        "body": """\
## Task
Initialize the analysis repository with the agreed folder structure and create shared utility functions.

## Deliverables
- [ ] Folder structure (track1, track2, track3, shared, notebooks, data, figures)
- [ ] `shared/load_features.py` — load and merge feature CSVs from pipeline output
- [ ] `shared/condition_labels.py` — mapping of TSST/PDST event markers to condition names
- [ ] `shared/plotting.py` — common figure style for all manuscripts
- [ ] `requirements.txt` (pandas, numpy, scipy, matplotlib, seaborn, statsmodels, scikit-learn, pingouin)
""",
        "labels": ["track: pipeline", "type: infrastructure", "phase: scoping", "P1: critical"],
        "milestone": None,
    },
]

from datetime import datetime
from dateutil.relativedelta import relativedelta

def months_from_today(n):
    today = datetime(2026, 3, 2)
    return (today + relativedelta(months=n)).strftime("%Y-%m-%dT00:00:00Z")


def create_repo(name):
    print(f"\n[B1] Creating repo: {name}")
    r = api("get", f"/repos/{USERNAME}/{name}")
    if r.status_code == 200:
        print(f"  → already exists: {r.json()['html_url']}")
        return r.json()["html_url"]
    r = api("post", "/user/repos", json={
        "name": name,
        "description": "Research analysis, statistical modeling, and manuscript code for the MOXIE stress physiology study",
        "private": True, "has_issues": True, "has_projects": True, "auto_init": False,
    })
    if r.status_code not in (200, 201):
        print(f"  ✗ {r.status_code} {r.text[:200]}")
        return None
    url = r.json()["html_url"]
    print(f"  ✓ {url}")
    sleep(1)
    topics_headers = {**HEADERS, "Accept": "application/vnd.github.mercy-preview+json"}
    requests.put(f"{BASE}/repos/{USERNAME}/{name}/topics", headers=topics_headers,
                 json={"names": ["stress-physiology","hrv","respiration","reinforcement-learning","bioinformatics","psychophysiology"]})
    sleep()
    return url


def init_readme(name):
    print(f"  Initializing README...")
    r = api("get", f"/repos/{USERNAME}/{name}/contents/README.md")
    if r.status_code == 200:
        print("  → already exists"); return
    r = api("put", f"/repos/{USERNAME}/{name}/contents/README.md",
            json={"message": "chore: initialize repository with README", "content": b64(ANALYSIS_README)})
    print(f"  ✓ README created" if r.status_code in (200,201) else f"  ✗ {r.status_code} {r.text[:100]}")


def setup_labels(name):
    print(f"\n[B2] Labels on {name}")
    for label in DEFAULT_LABELS:
        api("delete", f"/repos/{USERNAME}/{name}/labels/{requests.utils.quote(label, safe='')}")
        sleep(0.1)
    r = api("get", f"/repos/{USERNAME}/{name}/labels?per_page=100")
    existing = {l["name"] for l in r.json()} if r.status_code == 200 else set()
    ok = 0
    for lname, color, desc in MOXIE_LABELS:
        if lname in existing:
            encoded = requests.utils.quote(lname, safe="")
            r = api("patch", f"/repos/{USERNAME}/{name}/labels/{encoded}", json={"color": color, "description": desc})
        else:
            r = api("post", f"/repos/{USERNAME}/{name}/labels", json={"name": lname, "color": color, "description": desc})
        ok += 1 if r.status_code in (200, 201, 422) else 0
    print(f"  ✓ {ok}/{len(MOXIE_LABELS)} labels")
    return ok


def create_milestones(name):
    print(f"\n[B3] Milestones on {name}")
    r = api("get", f"/repos/{USERNAME}/{name}/milestones?state=all&per_page=100")
    existing = {m["title"]: m["number"] for m in r.json()} if r.status_code == 200 else {}
    milestone_map = {}
    ok = 0
    for title, desc, months in MILESTONES:
        if title in existing:
            milestone_map[title] = existing[title]
            ok += 1; continue
        r = api("post", f"/repos/{USERNAME}/{name}/milestones",
                json={"title": title, "description": desc, "due_on": months_from_today(months)})
        if r.status_code in (200, 201):
            num = r.json()["number"]
            milestone_map[title] = num
            ok += 1
            print(f"  ✓ #{num} {title}")
        else:
            print(f"  ✗ {title}: {r.status_code} {r.text[:100]}")
    print(f"  ✓ {ok}/{len(MILESTONES)} milestones")
    return milestone_map


def create_templates(name):
    print(f"\n[B4] Issue templates on {name}")
    for path, content in [
        (".github/ISSUE_TEMPLATE/research_question.md", TEMPLATE_RQ),
        (".github/ISSUE_TEMPLATE/milestone_task.md",    TEMPLATE_MT),
        (".github/ISSUE_TEMPLATE/manuscript.md",         TEMPLATE_MS),
    ]:
        r = api("get", f"/repos/{USERNAME}/{name}/contents/{path}")
        if r.status_code == 200:
            print(f"  → {path} already exists"); continue
        r = api("put", f"/repos/{USERNAME}/{name}/contents/{path}",
                json={"message": "chore: add issue templates", "content": b64(content)})
        print(f"  ✓ {path}" if r.status_code in (200,201) else f"  ✗ {path}: {r.status_code}")


def create_structure(name):
    print(f"\n[B5] Folder structure on {name}")
    files = [
        ("analysis/track1_breathing/.gitkeep",      ""),
        ("analysis/track2_arousal_valence/.gitkeep", ""),
        ("analysis/track3_digital_twin/.gitkeep",    ""),
        ("analysis/shared/.gitkeep",                 ""),
        ("notebooks/.gitkeep",                       ""),
        ("data/processed/.gitkeep",                  ""),
        ("data/features/.gitkeep",                   ""),
        ("figures/.gitkeep",                         ""),
        (".gitignore",                               GITIGNORE),
    ]
    ok = 0
    for path, content in files:
        r = api("get", f"/repos/{USERNAME}/{name}/contents/{path}")
        if r.status_code == 200:
            ok += 1; continue
        r = api("put", f"/repos/{USERNAME}/{name}/contents/{path}",
                json={"message": "chore: initialize repo structure", "content": b64(content)})
        if r.status_code in (200, 201):
            ok += 1
        else:
            print(f"  ✗ {path}: {r.status_code} {r.text[:100]}")
        sleep(0.2)
    print(f"  ✓ {ok}/{len(files)} files")


def create_issues(name, milestone_map):
    print(f"\n[B6] Starter issues on {name}")
    r = api("get", f"/repos/{USERNAME}/{name}/issues?state=all&per_page=100")
    existing = {i["title"]: (i["html_url"], i["number"]) for i in r.json()} if r.status_code == 200 else {}
    issue_numbers = []
    for issue in ISSUES:
        if issue["title"] in existing:
            url, num = existing[issue["title"]]
            print(f"  → #{num} already exists")
            issue_numbers.append(num); continue
        payload = {"title": issue["title"], "body": issue["body"], "labels": issue["labels"]}
        if issue["milestone"] and issue["milestone"] in milestone_map:
            payload["milestone"] = milestone_map[issue["milestone"]]
        r = api("post", f"/repos/{USERNAME}/{name}/issues", json=payload)
        if r.status_code in (200, 201):
            num = r.json()["number"]
            print(f"  ✓ #{num}: {issue['title'][:60]}")
            issue_numbers.append(num)
        else:
            print(f"  ✗ {issue['title'][:50]}: {r.status_code} {r.text[:100]}")
    return issue_numbers


def link_repo(pid, repo_name):
    q = """query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) { id }
    }"""
    d = graphql(q, {"owner": USERNAME, "name": repo_name})
    if not d.get("data", {}).get("repository"):
        print(f"    ✗ repo not found: {repo_name}"); return False
    rid = d["data"]["repository"]["id"]
    q2 = """mutation($pid: ID!, $rid: ID!) {
      linkProjectV2ToRepository(input: {projectId: $pid, repositoryId: $rid}) {
        repository { name }
      }
    }"""
    d2 = graphql(q2, {"pid": pid, "rid": rid})
    if "errors" in d2:
        msg = d2["errors"][0].get("message", "")
        if "already" in msg.lower():
            print(f"    → {repo_name} already linked"); return True
        print(f"    ✗ {repo_name}: {msg}"); return False
    print(f"    ✓ {repo_name} linked"); return True


def unlink_repo(pid, repo_name):
    q = """query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) { id }
    }"""
    d = graphql(q, {"owner": USERNAME, "name": repo_name})
    if not d.get("data", {}).get("repository"):
        print(f"    → {repo_name} not found, skipping unlink"); return
    rid = d["data"]["repository"]["id"]
    q2 = """mutation($pid: ID!, $rid: ID!) {
      unlinkProjectV2FromRepository(input: {projectId: $pid, repositoryId: $rid}) {
        repository { name }
      }
    }"""
    d2 = graphql(q2, {"pid": pid, "rid": rid})
    if "errors" in d2:
        msg = d2["errors"][0].get("message", "")
        if "not linked" in msg.lower() or "not found" in msg.lower():
            print(f"    → {repo_name} was not linked")
        else:
            print(f"    ✗ unlink {repo_name}: {msg}")
    else:
        print(f"    ✓ {repo_name} unlinked")


def add_issues_to_project(pid, repo_name, issue_numbers):
    print(f"\n[B8] Adding issues to project...")
    added = 0
    for num in issue_numbers:
        q = """query($owner: String!, $repo: String!, $num: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $num) { id }
          }
        }"""
        d = graphql(q, {"owner": USERNAME, "repo": repo_name, "num": num})
        issue_id = d.get("data", {}).get("repository", {}).get("issue", {}).get("id")
        if not issue_id:
            print(f"    ✗ issue #{num} not found"); continue
        q2 = """mutation($pid: ID!, $cid: ID!) {
          addProjectV2ItemById(input: {projectId: $pid, contentId: $cid}) {
            item { id }
          }
        }"""
        d2 = graphql(q2, {"pid": pid, "cid": issue_id})
        if "errors" in d2:
            msg = d2["errors"][0].get("message", "")
            if "already" in msg.lower():
                added += 1
            else:
                print(f"    ✗ #{num}: {msg}")
        else:
            added += 1
            print(f"    ✓ Added issue #{num}")
    print(f"  ✓ {added}/{len(issue_numbers)} issues added to project")
    return added


def main():
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN not set"); sys.exit(1)

    print("=" * 60)
    print("  MOXIE Patch: moxie-analyses + Status field update")
    print("=" * 60)

    # ── Part A: Project field changes ─────────────────────────────
    update_status_options()
    delete_phase_field()

    # ── Part B: moxie-analyses repo ───────────────────────────────
    repo = "moxie-analyses"
    url = create_repo(repo)
    if url:
        init_readme(repo)

    setup_labels(repo)
    milestone_map = create_milestones(repo)
    create_templates(repo)
    create_structure(repo)
    issue_numbers = create_issues(repo, milestone_map)

    # ── Part C: Update project repo links ─────────────────────────
    print(f"\n[C] Updating project repo links...")
    unlink_repo(PID, "moxie-analysis")
    link_repo(PID, "moxie-analyses")

    add_issues_to_project(PID, repo, issue_numbers)

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Patch Complete")
    print("=" * 60)
    print(f"  moxie-analyses: https://github.com/{USERNAME}/{repo}")
    print(f"  Project board:  https://github.com/users/{USERNAME}/projects/8")
    print()
    print("  Status field options: Scoping → Data Prep → Analysis → Writing → Review → Done")
    print("  Phase field: deleted")
    print("  Project repos: moxie-pipeline + moxie-analyses (moxie-analysis unlinked)")


if __name__ == "__main__":
    main()
