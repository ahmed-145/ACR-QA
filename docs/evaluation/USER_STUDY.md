# ACR-QA User Study — A/B Comparison Materials

## Study Design

**Objective:** Measure the impact of ACR-QA's AI-powered explanations on developer
understanding and fix speed compared to raw tool output.

**Methodology:** Between-subjects A/B comparison with 5 participants.

---

## Group A — Raw Tool Output (Control)

### Participant Instructions

You are reviewing a Python file that has been flagged by a static analysis tool.
Below are the raw findings. For each, rate your understanding and write a fix.

**Time tracking:** Start a timer when you begin reading.

### Finding 1 (Bandit)
```
>> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection vector
   Severity: Medium   Confidence: Medium
   CWE: CWE-89
   Location: ./sqli/dao/student.py:42:27
```

### Finding 2 (Bandit)
```
>> Issue: [B303:blacklist] Use of insecure MD5 hash function
   Severity: Medium   Confidence: High
   CWE: CWE-328
   Location: ./xss/dao/user.py:41:23
```

### Survey (Group A)
For each finding:
1. How well do you understand the issue? (1-5 scale)
2. How confident are you in writing a fix? (1-5 scale)
3. Write the fix (code):
4. Time taken (seconds):

---

## Group B — ACR-QA Output (Treatment)

### Participant Instructions

You are reviewing a Python file that has been flagged by ACR-QA, an AI-powered
code review tool. Below are the findings with explanations. For each, rate your
understanding and write a fix.

**Time tracking:** Start a timer when you begin reading.

### Finding 1 (ACR-QA)
```
Rule: SECURITY-027 (Hardcoded SQL Expressions)
Severity: HIGH | Category: security
File: sqli/dao/student.py:42

The code uses string formatting to build SQL queries, which is vulnerable
to SQL injection attacks. An attacker could manipulate the input to execute
arbitrary SQL commands.

❌ Vulnerable code:
    query = "SELECT * FROM students WHERE name = '%s'" % name

✅ Fixed code:
    query = "SELECT * FROM students WHERE name = %s"
    cursor.execute(query, (name,))

Use parameterized queries to prevent SQL injection. Never concatenate
user input directly into SQL strings.
```

### Finding 2 (ACR-QA)
```
Rule: SECURITY-009 (Weak Hash — MD5)
Severity: MEDIUM | Category: security
File: xss/dao/user.py:41

MD5 is a cryptographically broken hash function. It is vulnerable to
collision attacks and should not be used for password hashing or any
security-critical purpose.

❌ Vulnerable code:
    password_hash = hashlib.md5(password.encode()).hexdigest()

✅ Fixed code:
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

Use bcrypt, scrypt, or argon2 for password hashing. These algorithms
are designed to be computationally expensive, making brute-force attacks
infeasible.
```

### Survey (Group B)
For each finding:
1. How well do you understand the issue? (1-5 scale)
2. How confident are you in writing a fix? (1-5 scale)
3. Write the fix (code):
4. Time taken (seconds):

---

## Post-Study Questions (Both Groups)

1. Overall, how useful were the findings for understanding code issues? (1-5)
2. Would you use this tool in your daily workflow? (Yes/No/Maybe)
3. What would make the output more helpful? (free text)

---

## Participant Recruitment

**Target:** 5-10 software engineering students or developers.

**Requirements:**
- Familiar with Python (≥1 year experience)
- No prior exposure to ACR-QA
- Mix of experience levels preferred

**Recruitment channels:**
- University classmates / lab members
- Developer communities (Discord, Slack)
- Direct invitation via email

**Consent:** Inform participants that data is collected anonymously for academic purposes.

---

## How to Execute the Study

### Step 1: Generate Materials
```bash
cd /path/to/ACR-QA
python3 scripts/user_study.py --survey
```
This generates:
- `DATA/outputs/user_study_survey.md` — distributable questionnaire
- `DATA/outputs/user_study_responses.csv` — data collection template

### Step 2: Assign Groups
Randomly assign each participant to Group A (raw) or Group B (ACR-QA).

### Step 3: Collect Data
Have each participant complete the survey while timing themselves.

### Step 4: Analyze Results
```bash
python3 scripts/user_study.py --analyze
```
This generates a comparison report from the CSV data.

---

## Results Template

### Raw Data (fill in after study)

| Participant | Group | Q1 | Q2 | Q3 | Q4 | Time (s) | Correct Fixes |
|:-----------:|:-----:|:--:|:--:|:--:|:--:|:---------:|:-------------:|
| P001 | A | _ | _ | _ | _ | _ | _/2 |
| P002 | B | _ | _ | _ | _ | _ | _/2 |
| P003 | A | _ | _ | _ | _ | _ | _/2 |
| P004 | B | _ | _ | _ | _ | _ | _/2 |
| P005 | A | _ | _ | _ | _ | _ | _/2 |

### Aggregated Results

| Metric | Group A (Raw) | Group B (ACR-QA) | Improvement |
|--------|:-------------:|:----------------:|:-----------:|
| Avg understanding (Q1) | _/5 | _/5 | _% |
| Avg fix confidence (Q2) | _/5 | _/5 | _% |
| Avg time to fix (sec) | _ | _ | _% |
| Correct fixes | _/10 | _/10 | _% |
| Would use daily | _/5 | _/5 | _% |

### Statistical Significance

| Test | p-value | Significant? |
|------|:-------:|:------------:|
| Mann-Whitney U (understanding) | _ | _ |
| Mann-Whitney U (time) | _ | _ |
| Fisher's exact (correct fixes) | _ | _ |

> With n=5 per group, use non-parametric tests (Mann-Whitney U).
> Report p-values and effect sizes (Cohen's d).

---

*ACR-QA User Study Materials — March 2026*
*Version: 2.7.0 | Rule Mappings: 123 | Per-Tool Precision: 99%*
