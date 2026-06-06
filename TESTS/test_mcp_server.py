"""
Tests for acrqa-mcp/server.py — Feature 11.

Covers:
  - Module structure and importability
  - Config loading (env vars, config file)
  - HTTP helper functions (mocked)
  - _tool_scan: success path, timeout path, submission error
  - _tool_explain: success, 404, HTTP error
  - _tool_fix: success, 404, HTTP error
  - create_server: FastMCP server created with correct tools
  - MCP tool docstrings and parameter types
  - pyproject.toml structure and version
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add acrqa-mcp to path for import
MCP_DIR = Path(__file__).parent.parent / "acrqa-mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))


class TestMCPServerImport:
    def test_server_module_importable(self):
        import server  # noqa: F401

        assert server is not None

    def test_create_server_function_exists(self):
        import server

        assert callable(server.create_server)

    def test_main_function_exists(self):
        import server

        assert callable(server.main)

    def test_tool_functions_exist(self):
        import server

        assert callable(server._tool_scan)
        assert callable(server._tool_explain)
        assert callable(server._tool_fix)


class TestConfig:
    def test_get_base_url_default(self):
        import os

        import server

        with patch.object(server, "_load_config", return_value={}):
            old = os.environ.pop("ACRQA_URL", None)
            try:
                url = server._get_base_url()
                assert "localhost:8000" in url
            finally:
                if old is not None:
                    os.environ["ACRQA_URL"] = old

    def test_get_base_url_from_env(self):
        import os

        import server

        with patch.dict(os.environ, {"ACRQA_URL": "http://custom:9000"}):
            assert server._get_base_url() == "http://custom:9000"

    def test_get_token_from_env(self):
        import os

        import server

        with patch.dict(os.environ, {"ACRQA_TOKEN": "test-token-abc"}):
            assert server._get_token() == "test-token-abc"

    def test_headers_include_bearer(self):
        import os

        import server

        with patch.dict(os.environ, {"ACRQA_TOKEN": "my-token"}):
            h = server._headers()
            assert h["Authorization"] == "Bearer my-token"

    def test_headers_no_auth_without_token(self):
        import os

        import server

        with patch.dict(os.environ, {}, clear=False):
            old = os.environ.pop("ACRQA_TOKEN", None)
            try:
                with patch.object(server, "_load_config", return_value={}):
                    h = server._headers()
                    assert "Authorization" not in h
            finally:
                if old is not None:
                    os.environ["ACRQA_TOKEN"] = old

    def test_load_config_valid(self, tmp_path):
        import server

        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"url": "http://cfg-url:8080", "token": "cfg-token"}')
        with patch.object(server, "_CONFIG_PATH", cfg_file):
            cfg = server._load_config()
            assert cfg["url"] == "http://cfg-url:8080"
            assert cfg["token"] == "cfg-token"

    def test_load_config_invalid(self, tmp_path):
        import server

        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("invalid json")
        with patch.object(server, "_CONFIG_PATH", cfg_file):
            cfg = server._load_config()
            assert cfg == {}


class TestToolScan:
    def _mock_post(self, job_id="test-job-123"):
        return {"job_id": job_id, "status": "queued"}

    def _mock_poll_completed(self, run_id=1, findings=None):
        findings = findings or []
        return {
            "job_id": "test-job-123",
            "status": "completed",
            "result": {"run_id": run_id, "findings": findings},
        }

    def test_scan_success_returns_summary(self):
        import server

        findings = [
            {"severity": "high", "canonical_rule_id": "SECURITY-027", "file": "a.py", "line": 10, "message": "sqli"},
            {"severity": "medium", "canonical_rule_id": "STYLE-001", "file": "b.py", "line": 5, "message": "style"},
        ]
        with (
            patch.object(server, "_post", return_value=self._mock_post()),
            patch.object(server, "_get", return_value=self._mock_poll_completed(findings=findings)),
        ):
            result = server._tool_scan("/tmp/test", poll_timeout=10)

        assert result["status"] == "completed"
        assert result["findings_count"] == 2
        assert result["high_count"] == 1
        assert result["medium_count"] == 1
        assert result["low_count"] == 0
        assert len(result["top_findings"]) == 2
        assert "summary" in result

    def test_scan_submission_error(self):
        import httpx
        import server

        with patch.object(server, "_post", side_effect=httpx.HTTPError("connection refused")):
            result = server._tool_scan("/tmp/test")
        assert "error" in result

    def test_scan_timeout_returns_status(self):
        import server

        with (
            patch.object(server, "_post", return_value=self._mock_post()),
            patch.object(server, "_get", return_value={"job_id": "j1", "status": "started", "result": None}),
            patch("server.time.sleep"),
        ):
            result = server._tool_scan("/tmp/test", poll_timeout=0)
        assert result["status"] != "completed"

    def test_top_findings_sorted_by_severity(self):
        import server

        findings = [
            {"severity": "low", "canonical_rule_id": "STYLE-001", "file": "a.py", "line": 1, "message": "s"},
            {"severity": "high", "canonical_rule_id": "SECURITY-027", "file": "b.py", "line": 2, "message": "h"},
            {"severity": "medium", "canonical_rule_id": "SOLID-001", "file": "c.py", "line": 3, "message": "m"},
        ]
        with (
            patch.object(server, "_post", return_value=self._mock_post()),
            patch.object(server, "_get", return_value=self._mock_poll_completed(findings=findings)),
        ):
            result = server._tool_scan("/tmp/test", poll_timeout=10)
        assert result["top_findings"][0]["severity"] == "high"

    def test_empty_findings(self):
        import server

        with (
            patch.object(server, "_post", return_value=self._mock_post()),
            patch.object(server, "_get", return_value=self._mock_poll_completed(findings=[])),
        ):
            result = server._tool_scan("/tmp/test", poll_timeout=10)
        assert result["findings_count"] == 0
        assert result["top_findings"] == []

    @patch("server.time.sleep")
    def test_scan_polling_handles_http_error(self, mock_sleep):
        import httpx
        import server

        findings = []
        mock_poll = {
            "job_id": "test-job-123",
            "status": "completed",
            "result": {"run_id": 1, "findings": findings},
        }

        with (
            patch.object(server, "_post", return_value={"job_id": "test-job-123"}),
            patch.object(server, "_get", side_effect=[httpx.HTTPError("error"), mock_poll]),
        ):
            result = server._tool_scan("/tmp/test", poll_timeout=10)

        assert result["status"] == "completed"


class TestToolExplain:
    def test_explain_success(self):
        import server

        with patch.object(
            server,
            "_get",
            return_value={
                "explanation": "This is a SQL injection vulnerability.",
                "canonical_rule_id": "SECURITY-027",
                "severity": "high",
                "model": "llama-3.1-8b",
            },
        ):
            result = server._tool_explain(42)
        assert result["finding_id"] == 42
        assert "SQL injection" in result["explanation"]
        assert result["rule_id"] == "SECURITY-027"

    def test_explain_404_returns_error_message(self):
        import httpx
        import server

        mock_response = MagicMock()
        mock_response.status_code = 404
        err = httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_response)
        with patch.object(server, "_get", side_effect=err):
            result = server._tool_explain(9999)
        assert "error" in result
        assert "No explanation found" in result["error"]

    def test_explain_http_error(self):
        import httpx
        import server

        with patch.object(server, "_get", side_effect=httpx.HTTPError("connection error")):
            result = server._tool_explain(1)
        assert "error" in result


class TestToolFix:
    def test_fix_success(self):
        import server

        with patch.object(
            server,
            "_get",
            return_value={
                "can_fix": True,
                "confidence": 90,
                "fix_description": "Use parameterised query",
                "diff": "- raw_sql\n+ cursor.execute(q, params)",
                "canonical_rule_id": "SECURITY-027",
            },
        ):
            result = server._tool_fix(42)
        assert result["can_fix"] is True
        assert result["confidence"] == 90
        assert "parameterised" in result["fix_description"]

    def test_fix_404_returns_cannot_fix(self):
        import httpx
        import server

        mock_response = MagicMock()
        mock_response.status_code = 404
        err = httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_response)
        with patch.object(server, "_get", side_effect=err):
            result = server._tool_fix(9999)
        assert result["can_fix"] is False
        assert "error" in result

    def test_fix_http_error(self):
        import httpx
        import server

        with patch.object(server, "_get", side_effect=httpx.HTTPError("timeout")):
            result = server._tool_fix(1)
        assert result["can_fix"] is False


class TestCreateServer:
    def test_create_server_returns_object(self):
        import server

        try:
            mcp = server.create_server()
            assert mcp is not None
        except ImportError:
            pytest.skip("mcp package not installed")

    def _get_tools(self, mcp):
        """Resolve tools dict from FastMCP's _tool_manager._tools."""
        tm = getattr(mcp, "_tool_manager", None)
        if tm is not None:
            return getattr(tm, "_tools", {})
        return getattr(mcp, "_tools", {})

    def test_server_has_three_tools(self):
        import server

        try:
            mcp = server.create_server()
            tools = self._get_tools(mcp)
            assert len(tools) == 3, f"Expected 3 MCP tools, got {len(tools)}: {list(tools.keys())}"
        except ImportError:
            pytest.skip("mcp package not installed")

    def test_tool_names(self):
        import server

        try:
            mcp = server.create_server()
            names = set(self._get_tools(mcp).keys())
            assert "acrqa_scan" in names
            assert "acrqa_explain" in names
            assert "acrqa_fix" in names
        except ImportError:
            pytest.skip("mcp package not installed")

    def test_invoke_tools_success(self):
        import server

        try:
            mcp = server.create_server()
            with (
                patch.object(server, "_tool_scan", return_value={"status": "completed"}) as mock_scan,
                patch.object(server, "_tool_explain", return_value={"text": "ex"}) as mock_explain,
                patch.object(server, "_tool_fix", return_value={"diff": "df"}) as mock_fix,
            ):
                tools = self._get_tools(mcp)
                scan_tool = tools["acrqa_scan"]
                explain_tool = tools["acrqa_explain"]
                fix_tool = tools["acrqa_fix"]

                assert "completed" in scan_tool.fn("/tmp/test", repo_name="test")
                assert "ex" in explain_tool.fn(42)
                assert "df" in fix_tool.fn(42)

                mock_scan.assert_called_once_with("/tmp/test", repo_name="test")
                mock_explain.assert_called_once_with(42)
                mock_fix.assert_called_once_with(42)
        except ImportError:
            pytest.skip("mcp package not installed")


class TestMCPPackageStructure:
    def test_pyproject_toml_exists(self):
        p = MCP_DIR / "pyproject.toml"
        assert p.exists(), f"pyproject.toml not found at {p}"

    def test_pyproject_version(self):
        p = MCP_DIR / "pyproject.toml"
        content = p.read_text()
        assert "version" in content
        assert "acrqa-mcp" in content

    def test_pyproject_has_mcp_dependency(self):
        p = MCP_DIR / "pyproject.toml"
        content = p.read_text()
        assert "mcp" in content

    def test_pyproject_has_httpx_dependency(self):
        p = MCP_DIR / "pyproject.toml"
        content = p.read_text()
        assert "httpx" in content

    def test_server_file_exists(self):
        assert (MCP_DIR / "server.py").exists()

    def test_init_file_exists(self):
        assert (MCP_DIR / "__init__.py").exists()

    def test_server_has_three_tool_functions(self):
        src = (MCP_DIR / "server.py").read_text()
        assert "_tool_scan" in src
        assert "_tool_explain" in src
        assert "_tool_fix" in src

    def test_server_uses_env_var_config(self):
        src = (MCP_DIR / "server.py").read_text()
        assert "ACRQA_URL" in src
        assert "ACRQA_TOKEN" in src

    def test_server_config_file_path(self):
        src = (MCP_DIR / "server.py").read_text()
        assert ".config/acrqa/config.json" in src


class TestGodModeMCP:
    def test_tool_scan_returns_dict(self):
        import httpx
        import server

        with patch.object(server, "_post", side_effect=httpx.HTTPError("no server")):
            result = server._tool_scan("/nonexistent")
        assert isinstance(result, dict)
        assert "error" in result

    def test_tool_explain_returns_dict(self):
        import httpx
        import server

        with patch.object(server, "_get", side_effect=httpx.HTTPError("no server")):
            result = server._tool_explain(1)
        assert isinstance(result, dict)

    def test_tool_fix_returns_dict(self):
        import httpx
        import server

        with patch.object(server, "_get", side_effect=httpx.HTTPError("no server")):
            result = server._tool_fix(1)
        assert isinstance(result, dict)

    def test_scan_top_findings_max_five(self):
        import server

        findings = [
            {"severity": "high", "canonical_rule_id": f"SEC-{i}", "file": f"{i}.py", "line": i, "message": f"msg{i}"}
            for i in range(10)
        ]
        with (
            patch.object(server, "_post", return_value={"job_id": "j"}),
            patch.object(
                server,
                "_get",
                return_value={
                    "job_id": "j",
                    "status": "completed",
                    "result": {"run_id": 1, "findings": findings},
                },
            ),
        ):
            result = server._tool_scan("/tmp/test", poll_timeout=10)
        assert len(result["top_findings"]) <= 5

    def test_version_in_init(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("acrqa_mcp_init", MCP_DIR / "__init__.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "__version__")
        assert mod.__version__ == "1.0.0"


class TestHTTPHelpers:
    @patch("server.httpx.Client")
    def test_post_success(self, MockClient):
        import server

        mock_client = MockClient.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_client.post.return_value = mock_response

        res = server._post("/test-path", {"key": "val"})
        assert res == {"status": "ok"}
        mock_client.post.assert_called_once()

    @patch("server.httpx.Client")
    def test_get_success(self, MockClient):
        import server

        mock_client = MockClient.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "ok"}
        mock_client.get.return_value = mock_response

        res = server._get("/test-path")
        assert res == {"data": "ok"}
        mock_client.get.assert_called_once()


class TestMCPServerMain:
    @patch("server.create_server")
    def test_main_runs_server(self, mock_create_server):
        import server

        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        server.main()
        mock_mcp.run.assert_called_once_with(transport="stdio")
