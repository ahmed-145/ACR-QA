"""
PostgreSQL Database Interface for ACR-QA v2.0
Handles provenance storage and retrieval
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        """Initialize database connection"""
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'acrqa'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = False  # Use transactions
        except psycopg2.Error as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def _ensure_connection(self):
        """Reconnect if connection is closed"""
        if self.conn is None or self.conn.closed:
            self._connect()
    
    def execute(self, query, params=None, fetch=False):
        """
        Execute a query with error handling
        
        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch: If True, return results
            
        Returns:
            Query results if fetch=True, else None
        """
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                
                if fetch:
                    return cur.fetchall()
                
                self.conn.commit()
                
                # Return last inserted ID if applicable
                if 'INSERT' in query.upper() and 'RETURNING' in query.upper():
                    return cur.fetchone()
                    
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"❌ Query failed: {e}")
            print(f"   Query: {query}")
            raise
    
    # ===== ANALYSIS RUNS =====
    
    def create_analysis_run(self, repo_name, pr_number=None, commit_sha=None, branch=None):
        """Create a new analysis run"""
        query = """
            INSERT INTO analysis_runs (repo_name, pr_number, commit_sha, branch, status)
            VALUES (%s, %s, %s, %s, 'running')
            RETURNING id
        """
        result = self.execute(query, (repo_name, pr_number, commit_sha, branch), fetch=True)
        return result[0]['id'] if result else None
    
    def complete_analysis_run(self, run_id, total_findings):
        """Mark analysis run as completed"""
        query = """
            UPDATE analysis_runs
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                total_findings = %s
            WHERE id = %s
        """
        self.execute(query, (total_findings, run_id))
    
    def fail_analysis_run(self, run_id, error_message):
        """Mark analysis run as failed"""
        query = """
            UPDATE analysis_runs
            SET status = 'failed',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        self.execute(query, (run_id,))
    
    def get_analysis_run(self, run_id):
        """Get analysis run details"""
        query = "SELECT * FROM analysis_runs WHERE id = %s"
        results = self.execute(query, (run_id,), fetch=True)
        return results[0] if results else None
    
    def list_analysis_runs(self, limit=50):
        """List recent analysis runs"""
        query = """
            SELECT id, repo_name, pr_number, status, 
                   started_at, completed_at, total_findings
            FROM analysis_runs
            ORDER BY started_at DESC
            LIMIT %s
        """
        return self.execute(query, (limit,), fetch=True)
    
    # ===== ALIASES FOR COMPATIBILITY =====
    
    def get_run_info(self, run_id):
        """Get run metadata (alias for get_analysis_run)"""
        return self.get_analysis_run(run_id)
    
    def get_recent_runs(self, limit=10):
        """Get recent analysis runs (alias for list_analysis_runs)"""
        return self.list_analysis_runs(limit)
    
    # ===== FINDINGS =====
    
    def insert_finding(self, run_id, finding_dict):
        """Insert a normalized finding"""
        query = """
            INSERT INTO findings (
                run_id, tool, rule_id, canonical_rule_id, canonical_severity,
                file_path, line_number, column_number,
                severity, category, message, evidence, raw_output
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        
        params = (
            run_id,
            finding_dict.get('tool_raw', {}).get('tool_name', 'unknown'),
            finding_dict.get('original_rule_id', finding_dict.get('rule_id')),
            finding_dict.get('canonical_rule_id', finding_dict.get('rule_id')),
            finding_dict.get('severity', 'low'),
            finding_dict.get('file', 'unknown'),
            finding_dict.get('line', 0),
            finding_dict.get('column', 0),
            finding_dict.get('severity', 'low'),
            finding_dict.get('category', 'unknown'),
            finding_dict.get('message', ''),
            Json(finding_dict.get('evidence', {})),
            Json(finding_dict.get('tool_raw', {}))
        )
        
        result = self.execute(query, params, fetch=True)
        return result[0]['id'] if result else None
    
    def get_findings(self, run_id=None, severity=None, category=None, limit=100):
        """Query findings with filters"""
        conditions = []
        params = []
        
        if run_id:
            conditions.append("run_id = %s")
            params.append(run_id)
        
        if severity:
            conditions.append("canonical_severity = %s")
            params.append(severity)
        
        if category:
            conditions.append("category = %s")
            params.append(category)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT * FROM findings
            {where_clause}
            ORDER BY 
                CASE canonical_severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                file_path, line_number
            LIMIT %s
        """
        
        params.append(limit)
        return self.execute(query, tuple(params), fetch=True)
    
    def get_findings_with_explanations(self, run_id):
        """Get all findings with their explanations for a run"""
        query = """
            SELECT 
                f.id,
                f.rule_id,
                f.canonical_rule_id,
                f.file_path,
                f.line_number,
                f.severity,
                f.category,
                f.message,
                f.tool,
                f.ground_truth,
                e.response_text as explanation_text,
                e.latency_ms,
                e.model_name
            FROM findings f
            LEFT JOIN llm_explanations e ON f.id = e.finding_id
            WHERE f.run_id = %s
            ORDER BY 
                CASE f.severity
                    WHEN 'error' THEN 1
                    WHEN 'warning' THEN 2
                    ELSE 3
                END,
                f.file_path,
                f.line_number
        """
        return self.execute(query, (run_id,), fetch=True)
    
    def update_finding_ground_truth(self, finding_id, ground_truth):
        """Update ground truth label for evaluation"""
        if ground_truth not in ['TP', 'FP', 'TN', 'FN']:
            raise ValueError(f"Invalid ground_truth: {ground_truth}")
        
        query = """
            UPDATE findings
            SET ground_truth = %s
            WHERE id = %s
        """
        self.execute(query, (ground_truth, finding_id))
    
    # ===== LLM EXPLANATIONS =====
    
    def insert_explanation(self, finding_id, explanation_dict):
        """Store LLM explanation with full provenance"""
        query = """
            INSERT INTO llm_explanations (
                finding_id, model_name, prompt_filled, response_text,
                temperature, max_tokens, tokens_used,
                latency_ms, cost_usd, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        
        params = (
            finding_id,
            explanation_dict.get('model_name', 'unknown'),
            explanation_dict.get('prompt_filled', ''),
            explanation_dict.get('response_text', ''),
            explanation_dict.get('temperature', 0.3),
            explanation_dict.get('max_tokens', 150),
            explanation_dict.get('tokens_used'),
            explanation_dict.get('latency_ms', 0),
            explanation_dict.get('cost_usd', 0),
            explanation_dict.get('status', 'success')
        )
        
        result = self.execute(query, params, fetch=True)
        return result[0]['id'] if result else None
    
    def get_explanations(self, finding_id=None, run_id=None):
        """Get explanations with optional filters"""
        if finding_id:
            query = """
                SELECT * FROM llm_explanations
                WHERE finding_id = %s
                ORDER BY created_at DESC
            """
            return self.execute(query, (finding_id,), fetch=True)
        
        elif run_id:
            query = """
                SELECT e.* FROM llm_explanations e
                JOIN findings f ON e.finding_id = f.id
                WHERE f.run_id = %s
                ORDER BY e.created_at DESC
            """
            return self.execute(query, (run_id,), fetch=True)
        
        else:
            query = """
                SELECT * FROM llm_explanations
                ORDER BY created_at DESC
                LIMIT 100
            """
            return self.execute(query, fetch=True)
    
    # ===== FEEDBACK =====
    
    def insert_feedback(self, finding_id, user_id, is_false_positive=None, 
                       is_helpful=None, clarity_rating=None, comment=None):
        """Store user feedback"""
        query = """
            INSERT INTO feedback (
                finding_id, user_id, is_false_positive,
                is_helpful, clarity_rating, comment
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (finding_id, user_id, is_false_positive, 
                 is_helpful, clarity_rating, comment)
        result = self.execute(query, params, fetch=True)
        return result[0]['id'] if result else None
    
    def get_feedback_stats(self, run_id=None):
        """Get aggregated feedback statistics"""
        if run_id:
            query = """
                SELECT 
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN is_false_positive THEN 1 ELSE 0 END) as false_positives,
                    AVG(clarity_rating) as avg_clarity_rating,
                    SUM(CASE WHEN is_helpful THEN 1 ELSE 0 END) as helpful_count
                FROM feedback fb
                JOIN findings f ON fb.finding_id = f.id
                WHERE f.run_id = %s
            """
            results = self.execute(query, (run_id,), fetch=True)
        else:
            query = """
                SELECT 
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN is_false_positive THEN 1 ELSE 0 END) as false_positives,
                    AVG(clarity_rating) as avg_clarity_rating,
                    SUM(CASE WHEN is_helpful THEN 1 ELSE 0 END) as helpful_count
                FROM feedback
            """
            results = self.execute(query, fetch=True)
        
        return results[0] if results else {}
    
    # ===== ANALYTICS =====
    
    def get_run_summary(self, run_id):
        """Get comprehensive summary for a run"""
        query = """
            SELECT 
                r.*,
                COUNT(f.id) as findings_count,
                COUNT(CASE WHEN f.canonical_severity = 'high' THEN 1 END) as high_severity_count,
                COUNT(CASE WHEN f.canonical_severity = 'medium' THEN 1 END) as medium_severity_count,
                COUNT(CASE WHEN f.canonical_severity = 'low' THEN 1 END) as low_severity_count,
                COUNT(e.id) as explanations_count,
                AVG(e.latency_ms) as avg_explanation_latency,
                SUM(e.cost_usd) as total_cost
            FROM analysis_runs r
            LEFT JOIN findings f ON r.id = f.run_id
            LEFT JOIN llm_explanations e ON f.id = e.finding_id
            WHERE r.id = %s
            GROUP BY r.id
        """
        results = self.execute(query, (run_id,), fetch=True)
        return results[0] if results else None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Test connection
if __name__ == '__main__':
    print("Testing database connection...")
    try:
        db = Database()
        runs = db.get_recent_runs(limit=5)
        print(f"✅ Connected! Found {len(runs)} recent analysis runs")
        db.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")