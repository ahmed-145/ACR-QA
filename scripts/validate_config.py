#!/usr/bin/env python3
"""
ACR-QA Configuration Validator & Template Generator
Validates .acrqa.yml files against the expected schema and generates documented templates.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

import yaml

from CORE import __version__

# ─── Schema Definition ────────────────────────────────────────────────────
SCHEMA = {
    "enabled_tools": {
        "type": "dict",
        "description": "Enable/disable detection tools",
        "keys": {
            "ruff": {"type": "bool", "default": True, "description": "Python linter (fast)"},
            "semgrep": {"type": "bool", "default": True, "description": "Pattern-based security scanner"},
            "bandit": {"type": "bool", "default": True, "description": "Python security linter"},
            "vulture": {"type": "bool", "default": True, "description": "Dead code detector"},
            "radon": {"type": "bool", "default": True, "description": "Complexity analyzer"},
            "secrets": {"type": "bool", "default": True, "description": "Secrets detection"},
            "sca": {"type": "bool", "default": True, "description": "Dependency vulnerability scanner"},
            "ai_detector": {"type": "bool", "default": False, "description": "AI-generated code detector"},
        },
    },
    "severity_overrides": {
        "type": "dict",
        "description": "Override default severity for specific rules",
        "keys": "_dynamic",
        "value_schema": {
            "type": "string",
            "choices": ["high", "medium", "low"],
        },
    },
    "ignore_rules": {
        "type": "list",
        "description": "List of rule IDs to suppress",
        "item_type": "string",
        "example": ["STYLE-001", "DOC-001"],
    },
    "ignore_paths": {
        "type": "list",
        "description": "File/directory patterns to exclude from analysis",
        "item_type": "string",
        "example": ["tests/*", "migrations/*", "*.min.js"],
    },
    "min_severity": {
        "type": "string",
        "description": "Minimum severity to report (findings below this are hidden)",
        "choices": ["low", "medium", "high"],
        "default": "low",
    },
    "quality_gate": {
        "type": "dict",
        "description": "Thresholds that block CI/CD merge when exceeded",
        "keys": {
            "max_high": {"type": "int", "default": 0, "description": "Max high-severity findings allowed"},
            "max_medium": {"type": "int", "default": 10, "description": "Max medium-severity findings"},
            "max_total": {"type": "int", "default": 50, "description": "Max total findings"},
            "max_security": {"type": "int", "default": 0, "description": "Max security findings"},
        },
    },
    "explanation": {
        "type": "dict",
        "description": "AI explanation engine configuration",
        "keys": {
            "enabled": {"type": "bool", "default": True, "description": "Enable AI explanations"},
            "max_findings": {"type": "int", "default": 20, "description": "Max findings to explain per run"},
            "min_severity": {"type": "string", "default": "medium", "description": "Min severity to explain"},
        },
    },
    "autofix": {
        "type": "dict",
        "description": "Auto-fix engine configuration",
        "keys": {
            "enabled": {"type": "bool", "default": False, "description": "Enable auto-fixing"},
            "apply": {"type": "bool", "default": False, "description": "Apply fixes automatically"},
            "min_confidence": {"type": "float", "default": 0.8, "description": "Min confidence to apply fix"},
        },
    },
}

VALID_SEVERITIES = {"low", "medium", "high"}

logger = logging.getLogger(__name__)


def validate_config(config_path):
    """
    Validate an .acrqa.yml configuration file.

    Args:
        config_path: Path to the config file

    Returns:
        (is_valid, errors, warnings) tuple
    """
    errors = []
    warnings = []

    path = Path(config_path)
    if not path.exists():
        return False, [f"File not found: {config_path}"], []

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"], []

    if config is None:
        return True, [], ["Config file is empty — all defaults will be used."]

    if not isinstance(config, dict):
        return False, ["Config must be a YAML mapping (dict), not a list or scalar."], []

    # Check for unknown top-level keys
    known_keys = set(SCHEMA.keys())
    for key in config:
        if key not in known_keys:
            warnings.append(f"Unknown key '{key}' — will be ignored.")

    # Validate each known key
    for key, schema in SCHEMA.items():
        if key not in config:
            continue

        value = config[key]

        if schema["type"] == "dict":
            if not isinstance(value, dict):
                errors.append(f"'{key}' must be a dict, got {type(value).__name__}")
                continue

            # Validate known sub-keys
            if "keys" in schema and schema["keys"] != "_dynamic":
                for sub_key in value:
                    if sub_key not in schema["keys"]:
                        warnings.append(f"Unknown sub-key '{key}.{sub_key}'")

                for sub_key, sub_schema in schema["keys"].items():
                    if sub_key in value:
                        _validate_value(
                            f"{key}.{sub_key}",
                            value[sub_key],
                            sub_schema,
                            errors,
                            warnings,
                        )

            # Dynamic dict (severity_overrides)
            if schema.get("keys") == "_dynamic" and "value_schema" in schema:
                for sub_key, sub_val in value.items():
                    _validate_value(
                        f"{key}.{sub_key}",
                        sub_val,
                        schema["value_schema"],
                        errors,
                        warnings,
                    )

        elif schema["type"] == "list":
            if not isinstance(value, list):
                errors.append(f"'{key}' must be a list, got {type(value).__name__}")

        elif schema["type"] == "string":
            if not isinstance(value, str):
                errors.append(f"'{key}' must be a string, got {type(value).__name__}")
            elif "choices" in schema and value not in schema["choices"]:
                errors.append(f"'{key}' must be one of {schema['choices']}, got '{value}'")

    return len(errors) == 0, errors, warnings


def _validate_value(path, value, schema, errors, warnings):
    """Validate a single config value against its schema."""
    expected_type = schema["type"]

    type_map = {
        "bool": bool,
        "int": int,
        "float": (int, float),
        "string": str,
    }

    if expected_type in type_map:
        expected = type_map[expected_type]
        if not isinstance(value, expected):
            errors.append(f"'{path}' must be {expected_type}, got {type(value).__name__}")
            return

    if "choices" in schema and value not in schema["choices"]:
        errors.append(f"'{path}' must be one of {schema['choices']}, got '{value}'")


def generate_template(commented=True):
    """
    Generate a documented .acrqa.yml template.

    Args:
        commented: Include comments explaining each option

    Returns:
        YAML string with documentation
    """
    lines = []
    lines.append(f"# ACR-QA Configuration File (v{__version__})")
    lines.append("# Place this file in your project root as .acrqa.yml")
    lines.append("")

    for key, schema in SCHEMA.items():
        if commented:
            lines.append(f"# {schema['description']}")

        if schema["type"] == "dict" and "keys" in schema and schema["keys"] != "_dynamic":
            lines.append(f"{key}:")
            for sub_key, sub_schema in schema["keys"].items():
                default = sub_schema.get("default", "")
                if commented:
                    lines.append(f"  # {sub_schema.get('description', '')}")
                if isinstance(default, bool):
                    lines.append(f"  {sub_key}: {str(default).lower()}")
                else:
                    lines.append(f"  {sub_key}: {default}")
            lines.append("")

        elif schema["type"] == "dict" and schema.get("keys") == "_dynamic":
            lines.append(f"# {key}:")
            lines.append("#   RULE-ID: severity  # e.g., STYLE-001: low")
            lines.append("")

        elif schema["type"] == "list":
            example = schema.get("example", [])
            lines.append(f"# {key}:")
            for item in example:
                lines.append(f"#   - {item}")
            lines.append("")

        elif schema["type"] == "string":
            default = schema.get("default", "")
            choices = schema.get("choices", [])
            if choices and commented:
                lines.append(f"# Options: {', '.join(choices)}")
            lines.append(f"# {key}: {default}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ACR-QA Configuration Validator & Template Generator")
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # validate command
    validate_parser = sub.add_parser("validate", help="Validate a config file")
    validate_parser.add_argument(
        "config_file", nargs="?", default=".acrqa.yml", help="Path to config file (default: .acrqa.yml)"
    )

    # template command
    template_parser = sub.add_parser("template", help="Generate a documented template")
    template_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    template_parser.add_argument("--no-comments", action="store_true", help="Generate without explanatory comments")

    args = parser.parse_args()

    if args.command == "validate":
        config_file = args.config_file
        logger.info(f"🔍 Validating {config_file}...")

        is_valid, errors, warnings = validate_config(config_file)

        for w in warnings:
            logger.info(f"  ⚠️  {w}")

        for e in errors:
            logger.info(f"  ❌ {e}")

        if is_valid:
            logger.info("  ✅ Configuration is valid!")
        else:
            logger.error(f"\n  ❌ {len(errors)} error(s) found.")
            sys.exit(1)

    elif args.command == "template":
        template = generate_template(commented=not args.no_comments)

        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                f.write(template)
            logger.info(f"✅ Template written to {args.output}")
        else:
            logger.info(template)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
