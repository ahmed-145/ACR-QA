# ACR-QA Demo Video Script
**Length:** ~5 minutes | **Format:** Screen recording with voiceover

---

## Intro (0:00–0:30)

> "Code review is one of the most time-consuming parts of software development.
> Junior developers miss security issues. Senior developers get bottlenecked.
> And linters give you hundreds of warnings with no explanation.
>
> I built ACR-QA — Automated Code Review and Quality Assurance — to solve this.
> It's a platform that runs 7 static analysis tools, normalizes findings into a
> canonical format, and uses AI to generate developer-friendly explanations.
> Let me show you how it works."

---

## Demo Part 1: The Problem (0:30–1:00)

*Show the bad code file in the editor*

> "This is a realistic Python snippet with 8 intentional vulnerabilities —
> eval with user input, SQL injection via string formatting, hardcoded passwords,
> unsafe pickle deserialization, and more.
>
> A developer submitting this in a PR might miss all of these under time pressure."

---

## Demo Part 2: Opening a PR (1:00–1:45)

*Show GitHub, open PR #9 (or a new test PR)*

> "I open a pull request on GitHub. The ACR-QA workflow triggers automatically."

*Show the GitHub Actions tab running*

> "Watch what happens. ACR-QA runs 7 tools simultaneously:
> Bandit, Semgrep, Ruff, Vulture, jscpd, Radon, and a custom Secrets Detector.
> It takes about 45 seconds for a full scan."

---

## Demo Part 3: The Results (1:45–3:00)

*Show the PR bot comment*

> "The bot posts a structured code review comment directly in the pull request."

*Highlight the high severity section*

> "SECURITY-001 — eval() usage. Here's the AI explanation:
> 'This code violates SECURITY-001. eval() can execute arbitrary code injected by
> an attacker. Use ast.literal_eval() instead.'
>
> That's a developer-ready explanation with a concrete fix — not just a warning code."

*Scroll to show SQL injection finding*

> "SECURITY-027 — SQL injection via % string formatting.
> The rule caught username being interpolated directly into the query string.
> The fix: use parameterized queries."

*Show quality gate failure*

> "The quality gate blocked the merge. 2 high-severity findings exceeds the threshold of 0.
> The PR cannot be merged until these are fixed."

---

## Demo Part 4: The Dashboard (3:00–4:00)

*Open the Flask dashboard at localhost:5000*

> "Every run is stored in PostgreSQL and visualized in the dashboard."

*Show the trends chart*

> "This chart shows security findings over time — perfect for tracking
> whether a team is actually improving or just adding more issues."

*Show a specific run's findings table*

> "Each finding has its canonical rule ID, severity, file location,
> and the AI explanation. You can filter by severity or category."

---

## Demo Part 5: Scale Test & Results (4:00–4:45)

*Show the terminal output from the Flask scan*

> "I tested ACR-QA on the Flask framework — 10,000 GitHub stars, 50,000+ lines of code.
> It found 49 real issues with a false positive rate of just 10.3%.
> Industry standard tools like SonarQube Community run at 30-40% FP on Python.
>
> Zero false high-severity security alarms on production-quality code."

---

## Outro (4:45–5:00)

> "ACR-QA is fully open source, runs in CI/CD with a single GitHub Actions file,
> and takes under a minute to analyze a mid-size Python project.
>
> It's designed to give every developer the code review quality of a senior engineer —
> automatically, on every pull request."

*Show GitHub repo URL: github.com/ahmed-145/ACR-QA*

---

## Recording Tips

- Use OBS Studio or built-in screen recorder
- Record at 1920×1080
- Zoom into terminal/code sections — text should be readable
- Pause 2 seconds after each major action (bot comment appearing, quality gate failing)
- Trim to exactly 5 minutes before submitting
- Export as MP4 (H.264)
