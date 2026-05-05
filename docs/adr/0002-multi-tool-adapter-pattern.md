# ADR 0002 — Multi-Tool Adapter Pattern for Language Support

**Status:** Accepted
**Date:** 2026-05-05
**Author:** Ahmed Mahmoud Abbas

---

## Context

ACR-QA needs to run different tools depending on the programming language of the target repo:
- Python: Ruff, Bandit, Semgrep, Vulture, Radon
- JavaScript/TypeScript: ESLint, Semgrep JS, npm audit
- Go: gosec, staticcheck, Semgrep Go

Each tool:
- Is invoked differently (subprocess call, different flags)
- Produces output in a completely different schema (Bandit JSON ≠ ESLint JSON ≠ staticcheck text)
- Maps to different rule identifiers (B307, no-eval, G304...)

Without abstraction, adding Go support in v3.2.0 would require modifying the core pipeline logic, creating a spaghetti of `if language == "python": ... elif language == "go": ...` branches throughout `main.py`.

---

## Decision

Implement a **LanguageAdapter** abstract base class (`CORE/adapters/base.py`) that defines the interface every language must satisfy:

```python
class LanguageAdapter(ABC):
    def language_name(self) -> str: ...
    def file_extensions(self) -> list[str]: ...
    def run_tools(self, output_dir: str) -> dict[str, Any]: ...
    def get_rule_mappings(self) -> dict[str, str]: ...
```

Each language ships its own concrete adapter:
- `CORE/adapters/python_adapter.py` — `PythonAdapter`
- `CORE/adapters/js_adapter.py` — `JavaScriptAdapter` (v3.0.1)
- `CORE/adapters/go_adapter.py` — `GoAdapter` (v3.2.0)

Auto-detection (`JavaScriptAdapter.detect_language()`) inspects project structure (presence of `package.json`, `go.mod`, `.py` files) and routes without manual `--lang` flag.

Rule mappings live inside each adapter (`RULE_MAPPING`, `JS_RULE_MAPPING`, `GO_RULE_MAPPING`) and map tool-specific codes to canonical IDs:
```python
JS_RULE_MAPPING = {
    "no-eval": "SECURITY-001",
    "security/detect-sql-injection": "SECURITY-027",
    ...  # 55 entries
}
```

---

## Consequences

**What we gain:**
- Adding a new language = implement one adapter class + update CLI routing. No changes to normaliser, scorer, quality gate, or explainer.
- Each adapter's tests are isolated (`test_js_adapter.py`, `test_go_adapter.py`)
- Language detection is automatic — developers don't need `--lang` flags on mixed repos

**What we lose:**
- Rule mappings are spread across three files (Python normaliser, JS adapter, Go adapter). A centralised YAML registry would be cleaner — but that's a future refactor.
- Each adapter is responsible for both tool execution AND normalisation. Ideally these are two responsibilities, but splitting them would add abstraction overhead not justified at current scale.

**Known debt:**
As of v3.2.4, the Python tool severity is normalised through `normalizer.py` while JS and Go tools normalise through their respective adapter files. A future unification pass should move all rule mappings into `config/rules.yml` as the single source of truth.

---

## Alternatives Considered

| Option | Rejected Because |
|---|---|
| Direct if/elif branching in main.py | Doesn't scale — every new language touches the pipeline core |
| Single universal tool (Semgrep only) | Semgrep alone misses ~40% of findings that Bandit, ESLint, gosec catch |
| Plugin system with dynamic imports | Over-engineered for 3 languages — YAGNI |
| One adapter per tool (not per language) | Too granular — Go needs gosec + staticcheck + semgrep to work together |
