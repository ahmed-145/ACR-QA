# Rater Instructions — ACR-QA Security Finding Classification

Thank you for participating! This takes about 20 minutes.

## Your task

You will be shown 30 static analysis findings from real Python/JavaScript/Go code.
For each finding, classify it as ONE of:

| Label | Meaning |
|-------|---------|
| **TP** | True Positive — this is a real vulnerability that should be fixed |
| **FP** | False Positive — this is spurious, not actually a risk |
| **NEEDS_REVIEW** | You cannot decide without more context |

## Each finding shows you

1. **Rule** — the vulnerability category (e.g., SQL Injection, Hard-coded Secret)
2. **Severity** — CRITICAL / HIGH / MEDIUM / LOW (tool's estimate)
3. **File + line** — where in the code
4. **Message** — what the tool found
5. **Code snippet** — the 3–5 lines around the finding

## Definitions

**True Positive (TP):** A real security issue. The code snippet clearly shows the
pattern described in the message (e.g., `cursor.execute("SELECT * FROM users WHERE id=" + user_id)` is a real SQL injection risk).

**False Positive (FP):** The tool fired incorrectly. Common reasons:
- The "tainted" variable is actually a constant or internal value
- The sink is wrapped in a sanitizer the tool didn't detect
- The finding is in test code, not production code
- The rule fired on a benign pattern that superficially matches

**NEEDS_REVIEW:** You genuinely cannot tell from the snippet alone. For example, you'd need to
know where `user_input` comes from. Use this sparingly — if you can make a reasonable
call, make it.

## Tips

- Focus on the snippet, not just the message
- Test code (file path contains `test`, `spec`, `mock`) can still be TP but consider context
- Severity is the tool's estimate — it's informational, don't let it override your judgement
- Each finding is independent — your classification of #5 doesn't affect #6

## How to submit

Fill in `RATING_FORM_template.csv`:
- Column A: finding_id (already filled in)
- Column B: your label (TP / FP / NEEDS_REVIEW)
- Column C: confidence (1=low, 2=medium, 3=high)
- Column D: optional brief note

Email the completed CSV to **ahmedabbass871@gmail.com** with subject:
`ACR-QA Kappa Study — [Your Name]`
