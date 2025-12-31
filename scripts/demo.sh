#!/bin/bash
# ACR-QA v2.0 - Complete Demo Script
# One-command demo for supervisor presentation

set -e  # Exit on error

echo "=========================================="
echo "ACR-QA v2.0 - Supervisor Demo"
echo "Automated Code Review & Quality Assurance"
echo "=========================================="
echo ""

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "✓ Running inside Docker container"
    IN_DOCKER=true
else
    echo "✓ Running on host system"
    IN_DOCKER=false
fi

# Step 1: Database check
echo ""
echo "Step 1: Checking database connection..."
if [ "$IN_DOCKER" = true ]; then
    PGPASSWORD=$DB_PASSWORD psql -h postgres -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1
else
    PGPASSWORD=${DB_PASSWORD:-secure_password_123} psql -h localhost -U acr_user -d acr_qa_db -c "SELECT 1;" > /dev/null 2>&1
fi

if [ $? -eq 0 ]; then
    echo "   ✓ Database connected"
else
    echo "   ✗ Database connection failed!"
    echo "   Tip: Make sure PostgreSQL is running and .env is configured"
    exit 1
fi

# Step 2: Run analysis
echo ""
echo "Step 2: Running code analysis..."
echo "   Target: samples/seeded-repo"
echo "   Detection tools: Ruff, Semgrep, Vulture, jscpd"
echo "   AI explanations: Cerebras API (Llama 3.1)"
echo ""

python main.py --repo-name="demo-repo" --pr-number=1 --limit=10

if [ $? -ne 0 ]; then
    echo ""
    echo "✗ Analysis failed!"
    exit 1
fi

# Get the latest run ID
if [ "$IN_DOCKER" = true ]; then
    RUN_ID=$(PGPASSWORD=$DB_PASSWORD psql -h postgres -U $DB_USER -d $DB_NAME -t -c "SELECT MAX(id) FROM analysis_runs;")
else
    RUN_ID=$(PGPASSWORD=${DB_PASSWORD:-secure_password_123} psql -h localhost -U acr_user -d acr_qa_db -t -c "SELECT MAX(id) FROM analysis_runs;")
fi

RUN_ID=$(echo $RUN_ID | xargs)  # Trim whitespace

echo ""
echo "   ✓ Analysis complete!"
echo "   Run ID: $RUN_ID"

# Step 3: Show dashboard
echo ""
echo "Step 3: Displaying results dashboard..."
echo ""
python scripts/dashboard.py --run-id $RUN_ID

# Step 4: Generate report
echo ""
echo "Step 4: Generating detailed report..."
python scripts/generate_report.py $RUN_ID

# Step 5: Show sample explanations
echo ""
echo "Step 5: Sample AI-Generated Explanations"
echo "=========================================="

if [ "$IN_DOCKER" = true ]; then
    PGPASSWORD=$DB_PASSWORD psql -h postgres -U $DB_USER -d $DB_NAME << EOF
SELECT 
    f.rule_id,
    f.severity,
    f.file_path || ':' || f.line_number as location,
    LEFT(e.response_text, 150) || '...' as explanation,
    e.latency_ms || 'ms' as latency,
    e.model_name
FROM findings f
JOIN llm_explanations e ON f.id = e.finding_id
WHERE f.run_id = $RUN_ID
ORDER BY 
    CASE f.severity 
        WHEN 'error' THEN 1 
        WHEN 'warning' THEN 2 
        ELSE 3 
    END
LIMIT 5;
EOF
else
    PGPASSWORD=${DB_PASSWORD:-secure_password_123} psql -h localhost -U acr_user -d acr_qa_db << EOF
SELECT 
    f.rule_id,
    f.severity,
    f.file_path || ':' || f.line_number as location,
    LEFT(e.response_text, 150) || '...' as explanation,
    e.latency_ms || 'ms' as latency,
    e.model_name
FROM findings f
JOIN llm_explanations e ON f.id = e.finding_id
WHERE f.run_id = $RUN_ID
ORDER BY 
    CASE f.severity 
        WHEN 'error' THEN 1 
        WHEN 'warning' THEN 2 
        ELSE 3 
    END
LIMIT 5;
EOF
fi

# Step 6: Export provenance
echo ""
echo "Step 6: Exporting provenance data..."
python scripts/export_provenance.py $RUN_ID

echo ""
echo "=========================================="
echo "✅ Demo Complete!"
echo "=========================================="
echo ""
echo "📊 Generated Files:"
echo "   • Report: outputs/report_run_${RUN_ID}.md"
echo "   • Provenance: outputs/provenance/provenance_run_${RUN_ID}.json"
echo "   • Summary: outputs/provenance/summary_run_${RUN_ID}.txt"
echo ""
echo "🎯 Next Steps:"
echo "   • View report: cat outputs/report_run_${RUN_ID}.md"
echo "   • Collect feedback: python scripts/collect_feedback.py $RUN_ID"
echo "   • Re-run analysis: python main.py --limit 20"
echo ""
echo "📚 Documentation:"
echo "   • README.md - Setup & usage guide"
echo "   • docs/ARCHITECTURE.md - System design"
echo ""