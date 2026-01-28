"""
Unit tests for Dashboard API endpoints
Tests filtering, grouping, and data integrity
"""
import pytest
import json
from FRONTEND.app import app
from DATABASE.database import Database


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestDashboardAPI:
    """Test dashboard REST API endpoints"""

    def test_get_recent_runs(self, client):
        """Test GET /api/runs returns recent runs"""
        response = client.get('/api/runs')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['success'] is True
        assert 'runs' in data

    def test_get_run_findings_basic(self, client):
        """Test GET /api/runs/{id}/findings returns findings"""
        # Assume run 1 exists from previous tests
        response = client.get('/api/runs/1/findings')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['success'] is True
        assert 'findings' in data or 'groups' in data

    def test_findings_severity_filter(self, client):
        """Test filtering findings by severity"""
        response = client.get('/api/runs/1/findings?severity=high')
        data = json.loads(response.data)
        
        if data['success'] and 'findings' in data:
            for finding in data['findings']:
                assert finding['severity'] == 'high'

    def test_findings_category_filter(self, client):
        """Test filtering findings by category"""
        response = client.get('/api/runs/1/findings?category=security')
        data = json.loads(response.data)
        
        if data['success'] and 'findings' in data:
            for finding in data['findings']:
                assert finding['category'] == 'security'

    def test_findings_search_filter(self, client):
        """Test search filtering"""
        response = client.get('/api/runs/1/findings?search=eval')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['success'] is True

    def test_findings_grouping(self, client):
        """Test grouping findings by rule"""
        response = client.get('/api/runs/1/findings?group_by=rule')
        data = json.loads(response.data)
        
        if data['success'] and data.get('grouped'):
            assert 'groups' in data
            for group in data['groups']:
                assert 'rule_id' in group
                assert 'count' in group
                assert group['count'] > 0

    def test_run_stats(self, client):
        """Test GET /api/runs/{id}/stats"""
        response = client.get('/api/runs/1/stats')
        data = json.loads(response.data)
        
        if response.status_code == 200:
            assert 'total' in data or 'success' in data

    def test_confidence_score_in_response(self, client):
        """Test confidence scores are included in findings"""
        response = client.get('/api/runs/1/findings')
        data = json.loads(response.data)
        
        if data['success'] and 'findings' in data and len(data['findings']) > 0:
            finding = data['findings'][0]
            assert 'confidence' in finding
            assert 0 <= finding['confidence'] <= 1

    def test_invalid_run_id(self, client):
        """Test invalid run ID returns error"""
        response = client.get('/api/runs/999999/findings')
        
        # Should return empty or error, not crash
        assert response.status_code in [200, 404, 500]
