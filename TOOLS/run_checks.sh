#!/bin/bash
# ACR-QA Tool Runner - Executes all static analysis tools
# Place this at: TOOLS/run_checks.sh

set -e  # Exit on error

TARGET_DIR="$(pwd)/${1:-TESTS/samples/seeded-repo}"
OUTPUT_DIR="DATA/outputs"

echo "🔍 ACR-QA Static Analysis Tool Suite"
echo "Target: $TARGET_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# 1. RUFF - Fast Python linter
echo "[1/4] Running Ruff (style & best practices)..."
ruff check "TESTS/samples/seeded-repo" \
    --output-format=json \
    --config pyproject.toml \
    > "$OUTPUT_DIR/ruff.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/ruff.json"
echo "      ✓ Ruff complete"

# 2. SEMGREP - Security & pattern detection
echo "[2/4] Running Semgrep (security patterns)..."
semgrep scan \
    --config="TOOLS/semgrep/python-rules.yml" \
    --json \
    --quiet \
    "$TARGET_DIR" \
    > "$OUTPUT_DIR/semgrep.json" 2>/dev/null || echo '{"results":[]}' > "$OUTPUT_DIR/semgrep.json"
echo "      ✓ Semgrep complete"

# 3. VULTURE - Dead code detection
echo "[3/4] Running Vulture (unused code)..."
vulture "$TARGET_DIR" \
    --min-confidence 60 \
    > "$OUTPUT_DIR/vulture.txt" 2>/dev/null || touch "$OUTPUT_DIR/vulture.txt"
echo "      ✓ Vulture complete"

# 4. JSCPD - Code duplication
echo "[4/4] Running jscpd (duplication)..."
jscpd "$TARGET_DIR" \
    --reporters json \
    --output "$OUTPUT_DIR" \
    --min-lines 5 \
    --min-tokens 50 \
    --silent \
    > /dev/null 2>&1 || echo '{"duplicates":[]}' > "$OUTPUT_DIR/jscpd.json"

# jscpd creates jscpd-report.json, rename it
if [ -f "$OUTPUT_DIR/jscpd-report.json" ]; then
    mv "$OUTPUT_DIR/jscpd-report.json" "$OUTPUT_DIR/jscpd.json"
fi

# Ensure file exists
if [ ! -f "$OUTPUT_DIR/jscpd.json" ]; then
    echo '{"duplicates":[]}' > "$OUTPUT_DIR/jscpd.json"
fi

echo "      ✓ jscpd complete"

echo ""
echo "✅ All tools complete! Outputs in $OUTPUT_DIR/"
# 5. RADON - Complexity metrics
echo "[5/5] Running Radon (complexity)..."
radon cc "$TARGET_DIR" -j > "$OUTPUT_DIR/radon.json" 2>/dev/null || echo "{}" > "$OUTPUT_DIR/radon.json"
echo "      ✓ Radon complete"

