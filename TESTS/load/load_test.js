// ACR-QA Load Test Script (k6)
// Run: k6 run TESTS/load/load_test.js
//
// Install k6: https://k6.io/docs/get-started/installation/
//   Ubuntu: sudo snap install k6
//   macOS:  brew install k6

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const analyzeLatency = new Trend('analyze_latency');

// Test configuration
const BASE_URL = __ENV.ACR_QA_URL || 'http://localhost:5000';

// Test scenarios
export const options = {
    scenarios: {
        // Scenario 1: Smoke test (1 user, 30s)
        smoke: {
            executor: 'constant-vus',
            vus: 1,
            duration: '30s',
            tags: { scenario: 'smoke' },
            exec: 'smokeTest',
        },
        // Scenario 2: Load test (10 users, 2 min)
        load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 5 },
                { duration: '1m', target: 10 },
                { duration: '30s', target: 0 },
            ],
            tags: { scenario: 'load' },
            exec: 'loadTest',
            startTime: '35s',
        },
        // Scenario 3: Stress test (ramp to 25 users)
        stress: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 10 },
                { duration: '30s', target: 25 },
                { duration: '30s', target: 0 },
            ],
            tags: { scenario: 'stress' },
            exec: 'stressTest',
            startTime: '3m10s',
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<2000'],  // 95th percentile < 2s
        http_req_failed: ['rate<0.05'],     // Error rate < 5%
        errors: ['rate<0.1'],               // Custom error rate < 10%
    },
};

// Sample Python code for analysis
const SAMPLE_CODE = `
import os
import pickle

def process_data(data):
    result = eval(data)  # Security issue
    password = "admin123"  # Hardcoded secret
    
    try:
        with open("file.txt") as f:
            content = f.read()
    except:  # Bare except
        pass
    
    unused_var = 42
    return result

class MyClass:
    def __init__(self):
        self.items = []
    
    def add(self, item):
        self.items.append(item)
`;

// ─── Smoke Test ───────────────────────────────────────────
export function smokeTest() {
    group('Health Check', () => {
        const res = http.get(`${BASE_URL}/api/health`);
        check(res, {
            'health status 200': (r) => r.status === 200,
            'health body ok': (r) => JSON.parse(r.body).status === 'healthy',
        }) || errorRate.add(1);
    });

    group('Quick Stats', () => {
        const res = http.get(`${BASE_URL}/api/quick-stats`);
        check(res, {
            'stats status 200': (r) => r.status === 200,
            'stats has data': (r) => JSON.parse(r.body).success === true,
        }) || errorRate.add(1);
    });

    sleep(1);
}

// ─── Load Test ────────────────────────────────────────────
export function loadTest() {
    group('API Endpoints', () => {
        // GET /api/runs
        const runsRes = http.get(`${BASE_URL}/api/runs?limit=5`);
        check(runsRes, {
            'runs status 200': (r) => r.status === 200,
        }) || errorRate.add(1);

        // GET /api/categories
        const catRes = http.get(`${BASE_URL}/api/categories`);
        check(catRes, {
            'categories status 200': (r) => r.status === 200,
        }) || errorRate.add(1);

        // GET /api/trends
        const trendRes = http.get(`${BASE_URL}/api/trends?limit=10`);
        check(trendRes, {
            'trends status 200': (r) => r.status === 200,
        }) || errorRate.add(1);
    });

    group('Single File Analysis', () => {
        const payload = JSON.stringify({
            content: SAMPLE_CODE,
            filename: 'test_sample.py',
        });

        const params = {
            headers: { 'Content-Type': 'application/json' },
        };

        const start = Date.now();
        const res = http.post(`${BASE_URL}/api/analyze`, payload, params);
        analyzeLatency.add(Date.now() - start);

        check(res, {
            'analyze status 200': (r) => r.status === 200,
            'analyze has findings': (r) => {
                const body = JSON.parse(r.body);
                return body.success && body.total >= 0;
            },
        }) || errorRate.add(1);
    });

    sleep(0.5);
}

// ─── Stress Test ──────────────────────────────────────────
export function stressTest() {
    // Hammer the analyze endpoint
    const payload = JSON.stringify({
        content: SAMPLE_CODE,
        filename: `stress_test_${__VU}_${__ITER}.py`,
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.post(`${BASE_URL}/api/analyze`, payload, params);
    check(res, {
        'stress status 200': (r) => r.status === 200,
    }) || errorRate.add(1);

    // Also hit read endpoints
    http.get(`${BASE_URL}/api/health`);
    http.get(`${BASE_URL}/api/quick-stats`);

    sleep(0.2);
}

// ─── Summary ──────────────────────────────────────────────
export function handleSummary(data) {
    const summary = {
        timestamp: new Date().toISOString(),
        scenarios: {
            smoke: data.metrics['iterations{scenario:smoke}'] || {},
            load: data.metrics['iterations{scenario:load}'] || {},
            stress: data.metrics['iterations{scenario:stress}'] || {},
        },
        overall: {
            http_reqs: data.metrics.http_reqs?.values?.count || 0,
            http_req_duration_p95: data.metrics.http_req_duration?.values?.['p(95)'] || 0,
            http_req_failed_rate: data.metrics.http_req_failed?.values?.rate || 0,
            analyze_latency_avg: data.metrics.analyze_latency?.values?.avg || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
        },
    };

    return {
        stdout: `\n━━━ ACR-QA Load Test Results ━━━\n` +
            `Total Requests: ${summary.overall.http_reqs}\n` +
            `p95 Latency: ${Math.round(summary.overall.http_req_duration_p95)}ms\n` +
            `Error Rate: ${(summary.overall.http_req_failed_rate * 100).toFixed(2)}%\n` +
            `Analyze Avg: ${Math.round(summary.overall.analyze_latency_avg)}ms\n` +
            `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`,
        'DATA/outputs/load_test_results.json': JSON.stringify(summary, null, 2),
    };
}
