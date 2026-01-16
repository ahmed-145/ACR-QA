#!/bin/bash
set -e

TARGET_DIR="${1:-TESTS/samples/realistic-issues}"
OUTPUT_DIR="DATA/outputs"

echo "🔍 ACR-QA Static Analysis Tool Suite"
echo "Target: $TARGET_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# 1. RUFF - Find ALL Python files recursively
echo "[1/5] Running Ruff (style & best practices)..."
find "$TARGET_DIR" -name "*.py" -type f | xargs ruff check \
    --output-format=json \
    --config pyproject.toml \
    > "$OUTPUT_DIR/ruff.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/ruff.json"
echo "      ✓ Ruff complete"

# 2. SEMGREP
echo "[2/5] Running Semgrep (security patterns)..."
semgrep scan \
    --config="TOOLS/semgrep/python-rules.yml" \
    --json \
    --quiet \
    "$TARGET_DIR" \
    > "$OUTPUT_DIR/semgrep.json" 2>/dev/null || echo '{"results":[]}' > "$OUTPUT_DIR/semgrep.json"
echo "      ✓ Semgrep complete"

# 3. VULTURE
echo "[3/5] Running Vulture (unused code)..."
find "$TARGET_DIR" -name "*.py" -type f | xargs vulture \
    --min-confidence 60 \
    > "$OUTPUT_DIR/vulture.txt" 2>/dev/null || touch "$OUTPUT_DIR/vulture.txt"
echo "      ✓ Vulture complete"

# 4. JSCPD
echo "[4/5] Running jscpd (duplication)..."
jscpd "$TARGET_DIR" \
    --reporters json \
    --output "$OUTPUT_DIR" \
    --min-lines 5 \
    --min-tokens 50 \
    --silent \
    > /dev/null 2>&1 || echo '{"duplicates":[]}' > "$OUTPUT_DIR/jscpd.json"

if [ -f "$OUTPUT_DIR/jscpd-report.json" ]; then
    mv "$OUTPUT_DIR/jscpd-report.json" "$OUTPUT_DIR/jscpd.json"
fi

if [ ! -f "$OUTPUT_DIR/jscpd.json" ]; then
    echo '{"duplicates":[]}' > "$OUTPUT_DIR/jscpd.json"
fi
echo "      ✓ jscpd complete"

# 5. RADON
echo "[5/5] Running Radon (complexity metrics)..."
find "$TARGET_DIR" -name "*.py" -type f | xargs radon cc -a -j > "$OUTPUT_DIR/radon.json" 2>/dev/null || echo '{}' > "$OUTPUT_DIR/radon.json"
echo "      ✓ Radon complete"

echo ""
echo "✅ All tools complete! Outputs in $OUTPUT_DIR/"
