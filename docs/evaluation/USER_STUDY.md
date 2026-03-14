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

## Expected Results Template

| Metric | Group A (Raw) | Group B (ACR-QA) | Improvement |
|--------|:-------------:|:----------------:|:-----------:|
| Avg understanding score | /5 | /5 | % |
| Avg fix confidence | /5 | /5 | % |
| Avg time to fix (sec) | | | % |
| Correct fixes | /10 | /10 | % |
| Would use daily | /5 | /5 | % |

---

*ACR-QA User Study Materials — March 2026*
