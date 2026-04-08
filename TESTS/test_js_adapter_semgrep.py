import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from CORE.adapters.js_adapter import JavaScriptAdapter

class TestJavaScriptAdapterSemgrepRun:
    """Targeted deep tests for _run_semgrep_js inside JavaScriptAdapter to cover EJS logic."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> JavaScriptAdapter:
        return JavaScriptAdapter(target_dir=str(tmp_path))

    @patch("subprocess.run")
    def test_run_semgrep_js_success(self, mock_run, adapter, tmp_path):
        """Simulates a successful semgrep scan returning an EJS XSS finding (SECURITY-064)."""
        output_file = tmp_path / "semgrep.json"
        results = {"errors": []}
        
        # Mock semgrep JSON output containing the EJS vulnerability
        mock_output = {
            "results": [
                {
                    "check_id": "javascript.express.security.ejs-xss",
                    "path": "/project/views/ui.ejs",
                    "start": {"line": 15, "col": 5},
                    "extra": {
                        "severity": "ERROR",
                        "message": "Unescaped EJS output",
                        "metadata": {"category": "security"}
                    }
                }
            ]
        }
        
        # Setup mock behavior
        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps(mock_output)
        mock_run.return_value = mock_proc
        
        # Execute the adapter function
        adapter._run_semgrep_js(output_file, results)
        
        # Verify side-effects
        assert "semgrep" in results
        assert len(results["semgrep"]["results"]) == 1
        assert results["semgrep"]["results"][0]["path"] == "/project/views/ui.ejs"
        
        # Verify that output file was written properly
        saved_json = json.loads(output_file.read_text())
        assert saved_json["results"][0]["check_id"] == "javascript.express.security.ejs-xss"

    @patch("subprocess.run")
    def test_run_semgrep_js_timeout(self, mock_run, adapter, tmp_path):
        """Simulates a timeout from the semgrep process."""
        output_file = tmp_path / "semgrep.json"
        results = {"errors": []}
        
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="semgrep", timeout=180)
        
        adapter._run_semgrep_js(output_file, results)
        
        assert "semgrep" not in results
        assert any("timed out" in err for err in results["errors"])

    @patch("subprocess.run")
    def test_run_semgrep_js_decode_error(self, mock_run, adapter, tmp_path):
        """Simulates semi-garbled JSON output from semgrep."""
        output_file = tmp_path / "semgrep.json"
        results = {"errors": []}
        
        mock_proc = MagicMock()
        mock_proc.stdout = "This is not json"
        mock_run.return_value = mock_proc
        
        adapter._run_semgrep_js(output_file, results)
        
        assert "semgrep" not in results
        assert any("error" in err or "JSONDecodeError" in err for err in results["errors"])
