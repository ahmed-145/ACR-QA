"""
Triage Memory — Feature 6.

When a user marks a finding as a false positive, the system learns a
suppression rule and automatically suppresses similar findings in future scans.
"""

import fnmatch
import logging
import os

logger = logging.getLogger(__name__)


class TriageMemory:
    """Learns from user FP feedback and suppresses matching findings in future runs."""

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def learn_from_fp(self, finding_id: int, db) -> int | None:
        """Create a suppression rule from a marked false-positive finding.

        Loads the finding, derives a file pattern, inserts a suppression rule,
        and updates the finding's ground_truth to 'FP'.

        Returns the new suppression rule ID, or None on failure.
        """
        try:
            rows = db.execute(
                "SELECT canonical_rule_id, file_path FROM findings WHERE id = %s",
                (finding_id,),
                fetch=True,
            )
            if not rows:
                logger.warning("learn_from_fp: finding %s not found", finding_id)
                return None

            row = rows[0]
            canonical_rule_id = row["canonical_rule_id"] or "UNKNOWN"
            file_path = row.get("file_path") or ""

            file_pattern = self._derive_pattern(file_path)

            rule_id = db.insert_suppression_rule(
                canonical_rule_id=canonical_rule_id,
                file_pattern=file_pattern,
                finding_id=finding_id,
            )

            # Also update ground_truth on the finding
            db.execute(
                "UPDATE findings SET ground_truth = 'FP' WHERE id = %s",
                (finding_id,),
            )

            logger.info(
                "TriageMemory: learned rule %s for %s (pattern: %s)",
                rule_id,
                canonical_rule_id,
                file_pattern,
            )
            return rule_id

        except Exception:
            logger.exception("learn_from_fp failed for finding %s", finding_id)
            return None

    def should_suppress(self, finding: dict, db) -> bool:
        """Return True if any active suppression rule matches this finding."""
        try:
            rules = db.get_suppression_rules(active_only=True)
            canonical = finding.get("canonical_rule_id", finding.get("rule_id", ""))
            file_path = finding.get("file_path", finding.get("file", ""))

            for rule in rules:
                if rule["canonical_rule_id"] != canonical:
                    continue
                pattern = rule.get("file_pattern") or ""
                if not pattern or fnmatch.fnmatch(file_path, pattern):
                    # Increment suppression counter asynchronously (best-effort)
                    try:
                        db.increment_suppression_count(rule["id"])
                    except Exception:
                        pass
                    return True
            return False
        except Exception:
            logger.exception("should_suppress failed")
            return False

    def get_active_rules(self, db) -> list[dict]:
        """Return all active suppression rules."""
        return db.get_suppression_rules(active_only=True)

    def suppress_findings(self, findings: list[dict], db) -> tuple[list[dict], int]:
        """Filter findings, removing those matched by a suppression rule.

        Returns (kept_findings, suppressed_count).
        """
        try:
            rules = db.get_suppression_rules(active_only=True)
            if not rules:
                return findings, 0

            kept = []
            suppressed = 0
            for f in findings:
                canonical = f.get("canonical_rule_id", f.get("rule_id", ""))
                file_path = f.get("file_path", f.get("file", ""))
                matched = False
                for rule in rules:
                    if rule["canonical_rule_id"] != canonical:
                        continue
                    pattern = rule.get("file_pattern") or ""
                    if not pattern or fnmatch.fnmatch(file_path, pattern):
                        matched = True
                        try:
                            db.increment_suppression_count(rule["id"])
                        except Exception:
                            pass
                        break
                if matched:
                    suppressed += 1
                else:
                    kept.append(f)

            return kept, suppressed
        except Exception:
            logger.exception("suppress_findings failed — returning all findings")
            return findings, 0

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _derive_pattern(file_path: str) -> str:
        """Derive a glob-style suppression pattern from a file path.

        Strategy:
        - If the file is inside a test directory, suppress the whole dir: tests/*
        - Otherwise keep the directory and use a wildcard basename: dir/test_*.py
        - If no recognisable pattern, return the exact path.
        """
        if not file_path:
            return ""

        # Normalise separators
        fp = file_path.replace("\\", "/")
        dirname = os.path.dirname(fp)
        basename = os.path.basename(fp)

        # If inside a test directory, suppress the whole directory
        test_dirs = {"tests", "test", "spec", "specs", "__tests__"}
        parts = fp.split("/")
        for part in parts:
            if part.lower() in test_dirs:
                idx = parts.index(part)
                prefix = "/".join(parts[: idx + 1])
                return f"{prefix}/*"

        # If the filename itself looks like a test file, generalise the prefix
        if basename.startswith("test_") and "." in basename:
            ext = basename.rsplit(".", 1)[-1]
            if dirname:
                return f"{dirname}/test_*.{ext}"
            return f"test_*.{ext}"

        # Default: exact match on the file
        return fp
