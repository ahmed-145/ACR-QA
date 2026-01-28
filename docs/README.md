# ACR-QA Documentation Index

## 📁 Folder Structure

### Real Documentation (Thesis & Development)
- **`real-docs/markdowns/`** - Markdown documentation
  - `SESSION_DOCUMENTATION.md` - Complete development session log
  - `TOKEN_SETUP.md` - API token configuration guide
- **`real-docs/pdfs/`** - PDF exports (use pandoc to convert)

### Technical Documentation
- **`DOCS/`** - Architecture & API documentation
  - `API.md` - REST API endpoints
  - `ARCHITECTURE.md` - System architecture
  - `CANONICAL_SCHEMA.md` - Data schema

### Visual Assets
- **`diagrams/`** - System diagrams
  - Block diagrams
  - Workflow diagrams
  - ER diagrams
  - RAG process diagrams
  - Timeline diagrams

- **`images/`** - Screenshots & mockups
  - PR comment mockups
  - UI screenshots
  - Logos

### Project Documents
- **`project-docs/`** - Project requirements & planning
  - PRD (Product Requirements Document)
  - Grad Project documentation

- **`assignments/`** - Course assignments
  - Assignment PDFs

---

## 📚 Quick Access

### For Development
- [Session Documentation](real-docs/markdowns/SESSION_DOCUMENTATION.md) - What we built today
- [Token Setup](real-docs/markdowns/TOKEN_SETUP.md) - How to configure API tokens
- [API Reference](DOCS/API.md) - API endpoints

### For Thesis
- [Session Documentation](real-docs/markdowns/SESSION_DOCUMENTATION.md) - Complete implementation log
- [Architecture](DOCS/ARCHITECTURE.md) - System design
- Diagrams folder - Visual aids for thesis

---

## 🔄 Converting to PDF

```bash
# Install pandoc
sudo apt install pandoc

# Convert markdowns to PDFs
cd docs/real-docs/markdowns
pandoc SESSION_DOCUMENTATION.md -o ../pdfs/SESSION_DOCUMENTATION.pdf
pandoc TOKEN_SETUP.md -o ../pdfs/TOKEN_SETUP.pdf
```

---

## 📊 Generated Documentation

During analysis runs, ACR-QA generates:
- **Reports:** `../DATA/outputs/report_run_*.md`
- **Provenance:** `../DATA/outputs/provenance/`
- **Compliance:** Via `scripts/compliance_report.py`

---

**Last Updated:** January 28, 2026
