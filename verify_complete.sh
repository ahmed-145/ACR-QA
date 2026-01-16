#!/bin/bash
echo "🔍 Final Verification Checklist"
echo "================================"

echo ""
echo "1. Severity Scorer Test:"
python3 CORE/engines/severity_scorer.py | grep "Results:"

echo ""
echo "2. Database Schema:"
python3 -c "
from DATABASE.database import Database
db = Database()
runs = db.get_recent_runs(limit=1)
if runs:
    findings = db.get_findings(run_id=runs[0]['id'], limit=5)
    print(f'✅ Database working: {len(findings)} findings')
    print(f'   Columns: {list(findings[0].keys())[:8]}...')
"

echo ""
echo "3. PR Comment Formatter:"
python3 -c "
from DATABASE.database import Database
import sys
sys.path.insert(0, 'scripts')
from post_pr_comments import format_pr_comment
db = Database()
runs = db.get_recent_runs(limit=1)
if runs:
    findings = db.get_findings_with_explanations(runs[0]['id'])
    comment = format_pr_comment(findings)
    print(f'✅ Comment generated: {len(comment)} characters')
    print(f'   Findings: {len(findings)} issues')
"

echo ""
echo "4. File Structure:"
[ -f "CORE/engines/severity_scorer.py" ] && echo "✅ Severity scorer exists" || echo "❌ Missing severity scorer"
[ -f "scripts/post_pr_comments.py" ] && echo "✅ PR comment script exists" || echo "❌ Missing PR script"
[ -f ".github/workflows/acr-qa.yml" ] && echo "✅ GitHub Action exists" || echo "❌ Missing GitHub Action"
[ -d "TESTS/samples/comprehensive-issues" ] && echo "✅ Test data exists ($(ls TESTS/samples/comprehensive-issues/*.py | wc -l) files)" || echo "❌ Missing test data"

echo ""
echo "5. Dependencies:"
pip list | grep -q "PyGithub" && echo "✅ PyGithub installed" || echo "⚠️  PyGithub not installed"
pip list | grep -q "cerebras" && echo "✅ Cerebras SDK installed" || echo "❌ Cerebras SDK missing"

echo ""
echo "================================"
echo "✅ Week 1 & 2 Verification Complete!"
