#!/bin/bash
echo "🧪 Testing Comprehensive Issues Detection"
echo "=========================================="
echo ""

# Run analysis on comprehensive test suite
python3 CORE/main.py \
    --target-dir TESTS/samples/comprehensive-issues \
    --repo-name "comprehensive-test" \
    --limit 50

echo ""
echo "📊 Expected Results:"
echo "  - HIGH severity: 8-10 findings (SQL injections, eval)"
echo "  - MEDIUM severity: 6-8 findings (complexity, params, duplication)"
echo "  - LOW severity: 10-15 findings (style, unused code)"
echo "  - TOTAL: 25-35 findings"