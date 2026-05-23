export const DEMO_RUNS = [
  { id: 1, repo_name: "myapp/backend", status: "completed", findings_count: 47, high_count: 12, created_at: "2026-05-20T14:32:00Z", duration_seconds: 38 },
  { id: 2, repo_name: "myapp/frontend", status: "completed", findings_count: 23, high_count: 4, created_at: "2026-05-20T10:15:00Z", duration_seconds: 22 },
  { id: 3, repo_name: "infra/terraform", status: "completed", findings_count: 8, high_count: 3, created_at: "2026-05-19T18:00:00Z", duration_seconds: 15 },
  { id: 4, repo_name: "myapp/backend", status: "completed", findings_count: 51, high_count: 15, created_at: "2026-05-18T09:00:00Z", duration_seconds: 41 },
  { id: 5, repo_name: "myapp/backend", status: "completed", findings_count: 44, high_count: 10, created_at: "2026-05-17T11:00:00Z", duration_seconds: 36 },
];

export const DEMO_SPARKLINE_HIGH = [15, 12, 18, 11, 14, 10, 12];
export const DEMO_SPARKLINE_MED  = [28, 31, 25, 29, 27, 24, 26];
export const DEMO_SPARKLINE_LOW  = [42, 38, 45, 40, 43, 37, 41];

export const DEMO_OWASP = [
  { cat: "A01:Broken Access", count: 12 },
  { cat: "A02:Cryptographic Failures", count: 7 },
  { cat: "A03:Injection", count: 18 },
  { cat: "A04:Insecure Design", count: 4 },
  { cat: "A05:Security Misconfiguration", count: 9 },
  { cat: "A06:Vulnerable Components", count: 3 },
  { cat: "A07:Auth Failures", count: 6 },
  { cat: "A08:Software Integrity", count: 2 },
  { cat: "A09:Logging Failures", count: 5 },
  { cat: "A10:SSRF", count: 1 },
];

export const DEMO_TOP_RULES = [
  { rule: "SECURITY-003", label: "SQL Injection", count: 18 },
  { rule: "SECURITY-001", label: "XSS", count: 14 },
  { rule: "SECURITY-007", label: "Command Injection", count: 12 },
  { rule: "SECURITY-002", label: "Hardcoded Secret", count: 9 },
  { rule: "COMPLEXITY-001", label: "High Complexity", count: 8 },
  { rule: "SECURITY-010", label: "Path Traversal", count: 7 },
  { rule: "DUP-001", label: "Code Duplication", count: 6 },
  { rule: "SECURITY-005", label: "SSRF", count: 5 },
  { rule: "SECURITY-008", label: "Insecure Deserial.", count: 4 },
  { rule: "SECURITY-011", label: "XXE", count: 3 },
];

export const DEMO_TREND = [
  { week: "W1", high: 15, med: 28, low: 42 },
  { week: "W2", high: 12, med: 31, low: 38 },
  { week: "W3", high: 18, med: 25, low: 45 },
  { week: "W4", high: 11, med: 29, low: 40 },
  { week: "W5", high: 14, med: 27, low: 43 },
  { week: "W6", high: 10, med: 24, low: 37 },
  { week: "W7", high: 12, med: 26, low: 41 },
];

export const isDemoMode = () => localStorage.getItem("acrqa_demo") === "1";
export const setDemoMode = (on: boolean) => {
  if (on) localStorage.setItem("acrqa_demo", "1");
  else localStorage.removeItem("acrqa_demo");
};
