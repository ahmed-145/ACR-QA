// ACR-QA Dashboard JavaScript

const API_BASE = 'http://localhost:5000';
let currentRunId = null;
let allFindings = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadRuns();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('severity-filter').addEventListener('change', filterFindings);
    document.getElementById('category-filter').addEventListener('change', filterFindings);
    document.getElementById('search-input').addEventListener('input', filterFindings);
    
    // Modal close
    document.querySelector('.close').addEventListener('click', () => {
        document.getElementById('detail-modal').style.display = 'none';
    });
    
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('detail-modal');
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Load analysis runs
async function loadRuns() {
    try {
        const response = await fetch(`${API_BASE}/api/runs?limit=20`);
        const data = await response.json();
        
        if (data.success) {
            displayRuns(data.runs);
        }
    } catch (error) {
        console.error('Error loading runs:', error);
        document.getElementById('runs-list').innerHTML = 
            '<div class="error">Failed to load runs</div>';
    }
}

// Display runs in sidebar
function displayRuns(runs) {
    const container = document.getElementById('runs-list');
    
    if (runs.length === 0) {
        container.innerHTML = '<div class="empty-state">No runs found</div>';
        return;
    }
    
    container.innerHTML = runs.map(run => `
        <div class="run-card" onclick="loadFindings(${run.id})">
            <div class="run-header">
                <span class="run-id">Run #${run.id}</span>
                <span class="run-status">${run.status}</span>
            </div>
            <div class="run-info">
                ${run.repo_name}${run.pr_number ? ` #${run.pr_number}` : ''}
            </div>
            <div class="run-stats">
                ${run.high_count > 0 ? `<span class="stat high">${run.high_count} high</span>` : ''}
                ${run.medium_count > 0 ? `<span class="stat medium">${run.medium_count} med</span>` : ''}
                ${run.low_count > 0 ? `<span class="stat low">${run.low_count} low</span>` : ''}
            </div>
        </div>
    `).join('');
}

// Load findings for a run
async function loadFindings(runId) {
    currentRunId = runId;
    
    // Update active state
    document.querySelectorAll('.run-card').forEach(card => {
        card.classList.remove('active');
    });
    event.target.closest('.run-card').classList.add('active');
    
    // Show loading
    document.getElementById('findings-container').innerHTML = 
        '<div class="loading">Loading findings...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/runs/${runId}/findings`);
        const data = await response.json();
        
        if (data.success) {
            allFindings = data.findings;
            displayFindings(allFindings);
        }
    } catch (error) {
        console.error('Error loading findings:', error);
        document.getElementById('findings-container').innerHTML = 
            '<div class="error">Failed to load findings</div>';
    }
}

// Display findings
function displayFindings(findings) {
    const container = document.getElementById('findings-container');
    
    if (findings.length === 0) {
        container.innerHTML = '<div class="empty-state">No findings match your filters</div>';
        return;
    }
    
    container.innerHTML = findings.map(finding => `
        <div class="finding-card" onclick="showFindingDetail(${finding.id})">
            <div class="finding-header">
                <div class="finding-title">
                    <span class="severity-badge ${finding.canonical_severity}">
                        ${getSeverityEmoji(finding.canonical_severity)} ${finding.canonical_severity.toUpperCase()}
                    </span>
                    <span class="rule-id">${finding.canonical_rule_id || 'UNKNOWN'}</span>
                </div>
                <div class="finding-actions" onclick="event.stopPropagation()">
                    <button class="btn btn-fp" onclick="markFalsePositive(${finding.id})">
                        Mark FP
                    </button>
                </div>
            </div>
            
            <div class="finding-location">
                📄 ${finding.file_path}:${finding.line}
            </div>
            
            <div class="finding-message">
                ${finding.message}
            </div>
            
            ${finding.explanation_text ? `
                <div class="finding-explanation">
                    💡 <strong>AI Explanation:</strong><br>
                    ${truncate(finding.explanation_text, 200)}
                    ${finding.confidence ? `
                        <span class="confidence-score">
                            Confidence: ${(finding.confidence * 100).toFixed(0)}%
                        </span>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Filter findings
function filterFindings() {
    const severity = document.getElementById('severity-filter').value;
    const category = document.getElementById('category-filter').value;
    const search = document.getElementById('search-input').value.toLowerCase();
    
    let filtered = allFindings;
    
    if (severity) {
        filtered = filtered.filter(f => f.canonical_severity === severity);
    }
    
    if (category) {
        filtered = filtered.filter(f => f.category === category);
    }
    
    if (search) {
        filtered = filtered.filter(f => 
            f.file_path.toLowerCase().includes(search) ||
            f.message.toLowerCase().includes(search) ||
            (f.canonical_rule_id && f.canonical_rule_id.toLowerCase().includes(search))
        );
    }
    
    displayFindings(filtered);
}

// Show finding detail in modal
function showFindingDetail(findingId) {
    const finding = allFindings.find(f => f.id === findingId);
    if (!finding) return;
    
    const modal = document.getElementById('detail-modal');
    const modalBody = document.getElementById('modal-body');
    
    modalBody.innerHTML = `
        <h2>${finding.canonical_rule_id || 'Finding Details'}</h2>
        
        <div style="margin: 1.5rem 0;">
            <span class="severity-badge ${finding.canonical_severity}">
                ${getSeverityEmoji(finding.canonical_severity)} ${finding.canonical_severity.toUpperCase()}
            </span>
            <span style="margin-left: 1rem; color: var(--text-secondary);">
                Category: ${finding.category}
            </span>
        </div>
        
        <h3>Location</h3>
        <p style="font-family: monospace; background: var(--bg-dark); padding: 0.75rem; border-radius: 6px;">
            ${finding.file_path}:${finding.line}${finding.column ? `:${finding.column}` : ''}
        </p>
        
        <h3>Message</h3>
        <p>${finding.message}</p>
        
        ${finding.explanation_text ? `
            <h3>AI Explanation</h3>
            <div class="finding-explanation">
                ${finding.explanation_text}
            </div>
            
            ${finding.confidence ? `
                <p style="margin-top: 1rem;">
                    <strong>Confidence:</strong> ${(finding.confidence * 100).toFixed(0)}%
                    ${finding.cites_rule ? ' ✓ Cites rule' : ''}
                </p>
            ` : ''}
        ` : ''}
        
        <div style="margin-top: 2rem; display: flex; gap: 1rem;">
            <button class="btn btn-fp" onclick="markFalsePositive(${finding.id})">
                Mark as False Positive
            </button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Mark finding as false positive
async function markFalsePositive(findingId) {
    const reason = prompt('Reason for marking as false positive (optional):');
    
    try {
        const response = await fetch(`${API_BASE}/api/findings/${findingId}/mark-false-positive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: reason || 'User marked as FP' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ Marked as false positive');
            loadFindings(currentRunId);
            document.getElementById('detail-modal').style.display = 'none';
        } else {
            alert('Failed to mark as false positive');
        }
    } catch (error) {
        console.error('Error marking FP:', error);
        alert('Error marking as false positive');
    }
}

// Helper functions
function getSeverityEmoji(severity) {
    const emojis = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    };
    return emojis[severity] || '⚪';
}

function truncate(text, length) {
    if (text.length <= length) return text;
    return text.substring(0, length) + '... <em>(click for full)</em>';
}
