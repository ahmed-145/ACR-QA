#!/usr/bin/env python3
"""
Build the GP2 defense deck (.pptx) from the content in
docs/DEFENSE_PRESENTATION_CONTENT.md.

Generates a clean, KSIU-branded deck following the recommended outline. Convert to
.odp afterwards with:
    libreoffice --headless --convert-to odp --outdir docs/ docs/ACR-QA_Defense.pptx

Usage:
    .venv/bin/python3 scripts/build_defense_deck.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

NAVY = RGBColor(0x00, 0x26, 0x54)
GOLD = RGBColor(0xC9, 0xA8, 0x4C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREEN = RGBColor(0x1E, 0x9E, 0x53)
GRAY = RGBColor(0x55, 0x5F, 0x6B)

OUT = Path(__file__).resolve().parent.parent / "docs" / "ACR-QA_Defense.pptx"

# Widescreen 16:9
EMU_W, EMU_H = Inches(13.333), Inches(7.5)


def _bg(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def _textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def _accent_bar(slide):
    """Thin gold bar under the title area."""
    bar = slide.shapes.add_shape(1, Inches(0.6), Inches(1.35), Inches(2.2), Pt(3))
    bar.fill.solid()
    bar.fill.fore_color.rgb = GOLD
    bar.line.fill.background()


def title_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, NAVY)
    tf = _textbox(s, Inches(0.8), Inches(2.2), Inches(11.7), Inches(2.0))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "ACR-QA"
    r.font.size = Pt(60)
    r.font.bold = True
    r.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = "Automated Code Review & Quality Assurance"
    r2.font.size = Pt(24)
    r2.font.color.rgb = GOLD
    p2.alignment = PP_ALIGN.CENTER
    p3 = tf.add_paragraph()
    r3 = p3.add_run()
    r3.text = "The Trust Layer for AI-Written Code — exploit-verified, cryptographically attested"
    r3.font.size = Pt(14)
    r3.font.color.rgb = WHITE
    p3.alignment = PP_ALIGN.CENTER

    tf2 = _textbox(s, Inches(0.8), Inches(5.3), Inches(11.7), Inches(1.6))
    for txt, sz in [
        ("Ahmed Mahmoud Abbas", 18),
        ("Supervisor: Dr. Samy AbdelNabi", 14),
        ("Faculty of Computer Science & Engineering · CSE494 Graduation Project 2 · 2026", 12),
    ]:
        p = tf2.add_paragraph() if tf2.paragraphs[0].runs else tf2.paragraphs[0]
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(sz)
        r.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER


def content_slide(prs, title, bullets, *, accent=None, footer=None):
    """bullets: list of (text, level, bold, color_or_None)."""
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    # Title
    tf = _textbox(s, Inches(0.6), Inches(0.5), Inches(12.1), Inches(0.9))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(30)
    r.font.bold = True
    r.font.color.rgb = NAVY
    _accent_bar(s)
    if accent:
        ap = tf.add_paragraph()
        ar = ap.add_run()
        ar.text = accent
        ar.font.size = Pt(14)
        ar.font.italic = True
        ar.font.color.rgb = GOLD

    body = _textbox(s, Inches(0.7), Inches(1.7), Inches(12.0), Inches(5.2))
    first = True
    for text, level, bold, color in bullets:
        p = body.paragraphs[0] if first else body.add_paragraph()
        first = False
        p.level = level
        r = p.add_run()
        r.text = ("• " if level == 0 else "– ") + text
        r.font.size = Pt(20 - level * 2)
        r.font.bold = bold
        r.font.color.rgb = color or DARK
        p.space_after = Pt(6)

    if footer:
        ftf = _textbox(s, Inches(0.6), Inches(6.95), Inches(12.1), Inches(0.4))
        fp = ftf.paragraphs[0]
        fr = fp.add_run()
        fr.text = footer
        fr.font.size = Pt(11)
        fr.font.color.rgb = GRAY


def table_slide(prs, title, headers, rows, *, accent=None, footer=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    tf = _textbox(s, Inches(0.6), Inches(0.5), Inches(12.1), Inches(0.9))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(30)
    r.font.bold = True
    r.font.color.rgb = NAVY
    _accent_bar(s)
    if accent:
        ap = tf.add_paragraph()
        ar = ap.add_run()
        ar.text = accent
        ar.font.size = Pt(14)
        ar.font.italic = True
        ar.font.color.rgb = GOLD

    nrows, ncols = len(rows) + 1, len(headers)
    gtbl = s.shapes.add_table(nrows, ncols, Inches(0.7), Inches(1.85), Inches(12.0), Inches(0.5 * nrows)).table
    for c, h in enumerate(headers):
        cell = gtbl.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.color.rgb = WHITE
        para.runs[0].font.bold = True
        para.runs[0].font.size = Pt(14)
    for ri, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            cell = gtbl.cell(ri, c)
            cell.text = val
            para = cell.text_frame.paragraphs[0]
            para.runs[0].font.size = Pt(13)
            para.runs[0].font.color.rgb = DARK
            if c == 1:
                para.runs[0].font.bold = True
                para.runs[0].font.color.rgb = GREEN
    if footer:
        ftf = _textbox(s, Inches(0.6), Inches(6.95), Inches(12.1), Inches(0.4))
        fr = ftf.paragraphs[0].add_run()
        fr.text = footer
        fr.font.size = Pt(11)
        fr.font.color.rgb = GRAY


def section_slide(prs, title, subtitle):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, NAVY)
    tf = _textbox(s, Inches(0.8), Inches(2.8), Inches(11.7), Inches(2.0))
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(44)
    r.font.bold = True
    r.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = subtitle
    r2.font.size = Pt(20)
    r2.font.color.rgb = GOLD
    p2.alignment = PP_ALIGN.CENTER


def B(text, level=0, bold=False, color=None):
    return (text, level, bold, color)


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = EMU_W, EMU_H

    # 1. Title
    title_slide(prs)

    # 2. Outline
    content_slide(
        prs,
        "Presentation Outline",
        [
            B("Introduction & Problem Statement"),
            B("Motivation & Core Innovations"),
            B("System Architecture"),
            B("RAG Explanation Engine"),
            B("Data Model & Audit Trail"),
            B("Evaluation & Results", 0, True, GREEN),
            B("Live Demo", 0, True, GREEN),
            B("Implementation Status"),
            B("Conclusion & Future Work · Questions"),
        ],
    )

    # 3. Introduction
    content_slide(
        prs,
        "Introduction: The Context",
        [
            B("Code review is critical to software quality — but manual review is inconsistent, slow, error-prone"),
            B("It doesn't scale: universities see 300+ PRs/semester; startups 100+ PRs/week"),
            B("The market gap:", 0, True, NAVY),
            B("Enterprise tools (SonarQube, Coverity) cost $10k–50k/year", 1),
            B("Cloud SaaS requires uploading proprietary code — violates security policy", 1),
            B("AI explainers hallucinate — developers get burned once and stop trusting them", 1),
            B("ACR-QA: self-hosted, multi-tool, AI-explained, exploit-verified — at $0", 0, True, GREEN),
        ],
    )

    # 4. Problem Statement
    content_slide(
        prs,
        "Problem Statement",
        [
            B("Quality variance", 0, True, NAVY),
            B("Reviewer expertise & availability vary → vulnerabilities slip through", 1),
            B("Cost barrier", 0, True, NAVY),
            B("Powerful tools are unaffordable; free tools lack context → small teams use nothing", 1),
            B("The hallucination problem", 0, True, NAVY),
            B("LLMs invent plausible-but-wrong guidance → trust collapses, feedback ignored", 1),
        ],
    )

    # 5. Motivation & Core Innovations
    content_slide(
        prs,
        "Motivation & Core Innovations",
        [
            B("RAG-enhanced explanations — ground the AI in the actual rule definition; it cites, not guesses", 0, True, NAVY),
            B("Canonical findings schema — normalize 19 engines (Ruff, Semgrep, Bandit…) into one format", 0, True, NAVY),
            B("Confirmed Tier — a 4-gate stratum precise enough to auto-block a merge (96.4%)", 0, True, GREEN),
            B("Exploit verification — detonate a real payload in a Docker sandbox; not 'maybe', but proven", 0, True, GREEN),
            B("On-premises — Docker Compose, zero cloud, zero recurring cost, full data privacy", 0, True, NAVY),
            B("Cryptographic attestation — every scan ECDSA-signed + SLSA L3 provenance", 0, True, NAVY),
        ],
    )

    # 6. System Architecture
    content_slide(
        prs,
        "System Architecture",
        [
            B("Developer pushes code → webhook received; PR diff extracted, job enqueued (Redis)"),
            B("Detection: language adapter runs the tool suite in parallel (Ruff, Semgrep, Bandit, Vulture, Radon, jscpd)"),
            B("Normalization: every tool's JSON → one CanonicalFinding schema"),
            B("Trust gates: confidence scoring → reachability + taint → Confirmed Tier → exploit verification"),
            B("RAG engine: retrieve rule definition → generate grounded explanation → entropy-validate"),
            B("Persist to PostgreSQL (full audit trail) → ECDSA-sign → post PR comments by severity"),
            B("End to end: 30–90 seconds per PR", 0, True, GREEN),
        ],
        accent="Python, JavaScript/TypeScript, and Go adapters implemented",
    )

    # 7. RAG Explanation Engine
    content_slide(
        prs,
        "RAG Explanation Engine",
        [
            B("Problem: a raw LLM explains from memory → it hallucinates on obscure rules"),
            B("Solution: retrieve the actual rule definition first, then prompt with rule + code context", 0, True, NAVY),
            B("\"This function has 5 parameters. SOLID-001 says each is a responsibility — consider splitting.\"", 1),
            B("Validate: did it cite the rule? Is it coherent? Entropy filter rejects 96% of hallucinated runs", 0, True, GREEN),
            B("Fallback: deterministic template if the API is down or validation fails — never a blank, never a lie"),
            B("This grounding is why the explanations are trustworthy", 0, True, NAVY),
        ],
    )

    # 8. Data Model (compressed)
    content_slide(
        prs,
        "Data Model & Audit Trail",
        [
            B("Every decision is logged — full provenance from raw tool output to signed verdict"),
            B("CanonicalFinding is the single contract every engine reads and writes", 1),
            B("Raw tool output, LLM prompt/response/cost, reachability & exploit results — all stored", 1),
            B("If a finding is disputed, the whole pipeline is auditable; feedback tunes thresholds", 1),
            B("PostgreSQL + 20 migrations; each scan anchored by an ECDSA-P256 + Dilithium3 signature", 0, True, NAVY),
        ],
    )

    # 9. Evaluation & Results (the star)
    table_slide(
        prs,
        "Evaluation & Results",
        ["What we measured", "Result"],
        [
            ["Confirmed-Tier precision (auto-block stratum)", "96.4%  (CI 90.9–100%)"],
            ["CVE recall (pre-registered battery)", "100% — 8/8 detectable"],
            ["Head-to-head F1", "98.2% vs Semgrep 45.7% / Bandit 21.8%"],
            ["OWASP Top 10 coverage", "9 / 10 categories"],
            ["RealVuln 2026 leaderboard", "25.1% — beats Semgrep/Snyk/SonarQube"],
            ["Test suite / CORE coverage", "3,017 tests · 88%"],
        ],
        accent="Not just built — measured on adversarial corpora, against the standard tools",
        footer="Two corpora · pre-registered methodology · Wilson CIs · external Bandit gate (non-tautological)",
    )

    # 9b. Three proof points
    content_slide(
        prs,
        "Why You Can Trust the Numbers",
        [
            B("We separated detection from trust", 0, True, NAVY),
            B("Most tools emit 30–70% false positives. The Confirmed Tier hits 96.4% — enough to auto-block.", 1),
            B("We don't claim a vulnerability — we detonate it", 0, True, GREEN),
            B("Real payloads in a Docker sandbox: SQLi ' OR 1=1, SSTI {{7*7}}→49, command injection", 1),
            B("Verified live: SQLi + SSTI detonate; safe code correctly does NOT (no false detonation)", 1, False, GREEN),
            B("Every result is signed", 0, True, NAVY),
            B("ECDSA-P256 + Sigstore Rekor + SLSA L3 — an auditor verifies in one command", 1),
        ],
    )

    # 10. Live Demo
    section_slide(prs, "Live Demo", "ACR-QA in action — real repos, real findings, real exploits")

    # 11. Implementation Status
    content_slide(
        prs,
        "Implementation Status",
        [
            B("19 analysis engines across detection, scoring, RAG, reachability, taint, attestation", 0, True, NAVY),
            B("Python, JavaScript/TypeScript, Go adapters; PHP/Java via Semgrep generic rules"),
            B("52-endpoint FastAPI service + React 18 / TypeScript dashboard (live SSE progress)"),
            B("3,017 tests, 88% CORE coverage; Docker Compose, Helm, Terraform, K8s operator"),
            B("Exploit verification across 13 categories; CBoM with NIST PQC classification"),
            B("Shipped as acrqa==5.0.0rc2 — self-hosted, zero recurring cost", 0, True, GREEN),
        ],
    )

    # 12. Conclusion & Future Work
    content_slide(
        prs,
        "Conclusion & Future Work",
        [
            B("ACR-QA delivers trustworthy, multi-tool security analysis with verifiable exploit-proof at $0", 0, True, NAVY),
            B("96.4% Confirmed-Tier precision · 100% CVE recall · F1 98.2% · every result signed", 0, True, GREEN),
            B("Future work:", 0, True, NAVY),
            B("Inter-procedural taint analysis (est. +10–15pp injection recall)", 1),
            B("Automatic pull-request generation via the GitHub API", 1),
            B("PHP / Java / Rust dedicated adapters; parallel exploit-sandbox scale-out", 1),
        ],
    )

    # 13. Questions
    section_slide(prs, "Thank You", "Questions?")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"✓ Deck written: {OUT}  ({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")


if __name__ == "__main__":
    build()
