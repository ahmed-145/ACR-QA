#!/bin/bash
set -e

echo "🧪 Testing PR Comment Generation"
echo "================================="

# Run analysis
python3 CORE/main.py --target-dir TESTS/samples/comprehensive-issues --pr-number 1 --limit 56

# Get latest run ID
RUN_ID=$(python3 -c "
from DATABASE.database import Database
db = Database()
runs = db.get_recent_runs(limit=1)
print(runs[0]['id'] if runs else '')
")

echo "✅ Analysis complete (Run ID: $RUN_ID)"

# Generate comment (without posting)
python3 -c "
from DATABASE.database import Database
import sys
sys.path.insert(0, 'scripts')
from post_pr_comments import format_pr_comment

db = Database()
findings = db.get_findings_with_explanations($RUN_ID)

print(f'Found {len(findings)} findings')

# Show severity distribution
by_sev = {'high': 0, 'medium': 0, 'low': 0}
for f in findings:
    by_sev[f.get('canonical_severity', 'low')] += 1

print(f'HIGH: {by_sev[\"high\"]}, MEDIUM: {by_sev[\"medium\"]}, LOW: {by_sev[\"low\"]}')

# Save comment
comment = format_pr_comment(findings)
with open('/tmp/pr_comment_preview.md', 'w') as f:
    f.write(comment)

print('✅ Comment saved to /tmp/pr_comment_preview.md')
"

echo ""
echo "📄 Preview first 50 lines:"
head -50 /tmp/pr_comment_preview.md
