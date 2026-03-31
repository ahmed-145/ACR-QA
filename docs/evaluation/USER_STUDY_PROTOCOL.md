# ACR-QA User Study Protocol
**Version:** 1.0 | **Date:** 2026-03-31 | **Target Participants:** 8–10

---

## Purpose
Evaluate whether ACR-QA's AI-generated explanations help developers identify and fix issues faster and more accurately than manual code review or traditional linters.

## Participant Profile
- Computer Science students (3rd year+) or working developers
- Python experience: intermediate (can read and write Python functions)
- No prior ACR-QA exposure required

---

## Study Design: Within-Subject A/B

Each participant reviews the **same 3 code snippets** twice:
- **Condition A:** Manual review only (they read the code, no tool output)
- **Condition B:** With ACR-QA output (findings + AI explanations shown)

Order is counterbalanced (half start with A, half with B) to reduce learning effects.

---

## Materials Needed
- [ ] This protocol document (for the researcher)
- [ ] [Questionnaire form](./USER_STUDY.md) (for participants — one copy per person)
- [ ] 3 Python code snippet printouts or screen share (see Appendix A)
- [ ] Timer (20 minutes per participant)
- [ ] Participant ID sheet (P001–P010)

---

## Session Structure (≈ 20 minutes)

| Time | Activity |
|------|----------|
| 0–2 min | Welcome, consent, assign participant ID |
| 2–4 min | Brief intro — explain what they'll do (NOT what the tool does) |
| 4–9 min | **Task 1:** Review Snippet A manually, write down issues |
| 9–14 min | **Task 2:** Review Snippet B with ACR-QA output, write down issues |
| 14–18 min | Fill out questionnaire |
| 18–20 min | Optional: short verbal debrief |

---

## Researcher Script (Read Verbatim)

> "Thanks for participating. Today I'll show you some Python code snippets. First, I'll ask you to review a snippet on your own and write down any issues you notice. Then I'll show you the output from our automated review tool for a second snippet. Please work through each task independently without asking me for help — there are no right or wrong answers."

---

## The 3 Test Code Snippets

### Snippet 1 — Security Issues (Condition A: manual)
Used to measure **baseline detection** without tool.

```python
# user_auth.py
import pickle

SECRET_KEY = "admin123"

def authenticate(username, password):
    query = "SELECT * FROM users WHERE username = '%s'" % username
    cursor.execute(query)
    user_data = pickle.loads(cursor.fetchone()["session"])
    return user_data
```

**Expected detections:**
- HARDCODE-001 (SECRET_KEY hardcoded)
- SECURITY-027 (SQL injection via % format)
- SECURITY-008 (unsafe pickle.loads)

---

### Snippet 2 — Design Issues (Condition B: with ACR-QA)
Used to measure **assisted detection** with tool output shown.

```python
# data_processor.py
def process_data(user_id, name, email, phone, address, city, country, zipcode):
    try:
        result = fetch_user(user_id)
        if result:
            if result["active"]:
                if result["verified"]:
                    return result
    except:
        pass
```

**ACR-QA Output to show:**
```
[MEDIUM] SOLID-001 @ line 2: Function has too many parameters (>6)
[MEDIUM] EXCEPT-001 @ line 9: Bare except clause catches everything
  → AI: This violates EXCEPT-001. bare except catches KeyboardInterrupt and
    SystemExit. Fix: use `except Exception as e: logger.error(e)` instead.
```

---

### Snippet 3 — Mixed (used for Likert rating task)

```python
# file_handler.py
import yaml

def load_config(path):
    f = open(path)
    config = yaml.load(f.read())
    return config
```

**Expected detections:**
- RESOURCE-001 (file not closed — no `with`)
- SECURITY-018 (yaml.load without Loader — RCE risk)

---

## Metrics to Collect

| Metric | How Measured |
|--------|-------------|
| Detection rate | Count of issues correctly identified per snippet |
| Fix accuracy | Boolean — did they propose a correct fix? |
| Time per task | Researcher records |
| Perceived usefulness | Q4–Q6 in questionnaire (Likert 1-5) |
| Clarity of AI explanations | Q7–Q9 in questionnaire (Likert 1-5) |

---

## Data Recording Template

| Participant | Snippet 1 Issues Found | Snippet 2 Issues Found | Time A (min) | Time B (min) | Overall Rating |
|-------------|----------------------|----------------------|-------------|-------------|----------------|
| P001 | | | | | |
| P002 | | | | | |
| P003 | | | | | |

---

## Appendix A — Participant Consent Blurb

> "Your participation is voluntary and anonymous. Data will only be used for academic research as part of a graduation thesis. You may stop at any time. By continuing, you consent to participation."

---

## Appendix B — Running the Questionnaire Generator

```bash
python3 scripts/user_study.py --generate-form --output docs/evaluation/
```
This creates:
- `survey_form.md` — printable questionnaire
- `responses_template.csv` — data collection template
