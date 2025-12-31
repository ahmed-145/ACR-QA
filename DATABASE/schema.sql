-- ACR-QA v2.0 Database Schema
-- Provenance & Audit Trail

-- Analysis runs table
CREATE TABLE IF NOT EXISTS analysis_runs (
    id SERIAL PRIMARY KEY,
    repo_name VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40),
    branch VARCHAR(100),
    pr_number INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('running', 'completed', 'failed')) DEFAULT 'running',
    total_findings INTEGER DEFAULT 0
);

-- Findings table (normalized tool outputs)
CREATE TABLE IF NOT EXISTS findings (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    tool VARCHAR(50) NOT NULL,
    rule_id VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER DEFAULT 0,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    raw_output JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLM explanations table (Cerebras API interactions)
CREATE TABLE IF NOT EXISTS llm_explanations (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER REFERENCES findings(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    prompt_template TEXT,
    prompt_filled TEXT NOT NULL,
    response_text TEXT NOT NULL,
    temperature FLOAT NOT NULL,
    max_tokens INTEGER NOT NULL,
    tokens_used INTEGER,
    latency_ms INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'success',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PR/MR comments table (GitHub/GitLab integration)
CREATE TABLE IF NOT EXISTS pr_comments (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER REFERENCES findings(id) ON DELETE CASCADE,
    pr_number INTEGER NOT NULL,
    comment_id VARCHAR(100),
    platform VARCHAR(20) CHECK (platform IN ('github', 'gitlab')) NOT NULL,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('posted', 'failed', 'deleted')) DEFAULT 'posted',
    error_message TEXT
);

-- User feedback table (evaluation & improvement)
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER REFERENCES findings(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    is_false_positive BOOLEAN DEFAULT FALSE,
    is_helpful BOOLEAN,
    clarity_rating INTEGER CHECK (clarity_rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id);
CREATE INDEX IF NOT EXISTS idx_findings_file_path ON findings(file_path);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_llm_finding_id ON llm_explanations(finding_id);
CREATE INDEX IF NOT EXISTS idx_pr_comments_finding ON pr_comments(finding_id);
CREATE INDEX IF NOT EXISTS idx_pr_comments_pr_number ON pr_comments(pr_number);
CREATE INDEX IF NOT EXISTS idx_feedback_finding ON feedback(finding_id);

-- Comments
COMMENT ON TABLE analysis_runs IS 'Each analysis run (one per PR or manual execution)';
COMMENT ON TABLE findings IS 'Individual code issues detected by tools';
COMMENT ON TABLE llm_explanations IS 'AI-generated explanations for findings';
COMMENT ON TABLE pr_comments IS 'Comments posted to PRs/MRs';
COMMENT ON TABLE feedback IS 'User feedback for evaluation';


ALTER TABLE findings ADD COLUMN canonical_rule_id VARCHAR(50);
ALTER TABLE findings ADD COLUMN canonical_severity VARCHAR(20);
ALTER TABLE findings ADD COLUMN evidence JSONB;


-- Add ground_truth column
ALTER TABLE findings ADD COLUMN ground_truth VARCHAR(10) 
    CHECK (ground_truth IN ('TP', 'FP', 'TN', 'FN'));

CREATE INDEX idx_findings_ground_truth ON findings(ground_truth);