// ACR-QA VSCode Extension
// Real API integration for code analysis

const vscode = require('vscode');
const http = require('http');
const https = require('https');

let diagnosticCollection;

function activate(context) {
    console.log('ACR-QA extension activated');

    // Create diagnostic collection
    diagnosticCollection = vscode.languages.createDiagnosticCollection('acrqa');
    context.subscriptions.push(diagnosticCollection);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('acrqa.analyzeFile', analyzeCurrentFile)
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('acrqa.analyzeWorkspace', analyzeWorkspace)
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('acrqa.clearDiagnostics', () => {
            diagnosticCollection.clear();
            vscode.window.showInformationMessage('ACR-QA diagnostics cleared');
        })
    );

    // Auto-analyze on save if enabled
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(document => {
            const config = vscode.workspace.getConfiguration('acrqa');
            if (config.get('enableAutoAnalysis') && document.languageId === 'python') {
                analyzeFile(document.uri, document.getText());
            }
        })
    );
}

async function analyzeCurrentFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }

    const document = editor.document;
    if (document.languageId !== 'python') {
        vscode.window.showWarningMessage('ACR-QA currently only supports Python files');
        return;
    }

    await analyzeFile(document.uri, document.getText());
}

async function analyzeFile(fileUri, content) {
    const config = vscode.workspace.getConfiguration('acrqa');
    const apiUrl = config.get('apiUrl') || 'http://localhost:5000';

    vscode.window.showInformationMessage('ACR-QA: Analyzing file...');

    try {
        const findings = await callAnalyzeAPI(apiUrl, content, fileUri.fsPath);

        const diagnostics = findings.map(finding => {
            const line = Math.max(0, (finding.line || 1) - 1); // VSCode is 0-indexed
            const col = Math.max(0, (finding.column || 1) - 1);
            const range = new vscode.Range(line, col, line, col + 50);

            const diagnostic = new vscode.Diagnostic(
                range,
                finding.message,
                getSeverity(finding.severity)
            );

            diagnostic.code = finding.rule_id;
            diagnostic.source = `ACR-QA (${finding.tool || 'unknown'})`;

            return diagnostic;
        });

        diagnosticCollection.set(fileUri, diagnostics);

        if (findings.length > 0) {
            vscode.window.showWarningMessage(`ACR-QA: Found ${findings.length} issues`);
        } else {
            vscode.window.showInformationMessage('ACR-QA: No issues found! ✓');
        }

    } catch (error) {
        vscode.window.showErrorMessage(`ACR-QA Error: ${error.message}`);
        console.error('ACR-QA Error:', error);
    }
}

async function callAnalyzeAPI(apiUrl, content, filename) {
    return new Promise((resolve, reject) => {
        const url = new URL(`${apiUrl}/api/analyze`);
        const isHttps = url.protocol === 'https:';
        const httpLib = isHttps ? https : http;

        const postData = JSON.stringify({
            content: content,
            filename: filename
        });

        const options = {
            hostname: url.hostname,
            port: url.port || (isHttps ? 443 : 80),
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = httpLib.request(options, (res) => {
            let data = '';

            res.on('data', (chunk) => {
                data += chunk;
            });

            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    if (response.success) {
                        resolve(response.findings || []);
                    } else {
                        reject(new Error(response.error || 'API error'));
                    }
                } catch (e) {
                    reject(new Error('Failed to parse API response'));
                }
            });
        });

        req.on('error', (e) => {
            reject(new Error(`Connection failed: ${e.message}. Is the ACR-QA server running?`));
        });

        req.setTimeout(30000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.write(postData);
        req.end();
    });
}

async function analyzeWorkspace() {
    vscode.window.showInformationMessage('ACR-QA: Analyzing workspace...');

    // Find all Python files
    const files = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**', 50);

    let totalFindings = 0;
    for (const file of files) {
        try {
            const document = await vscode.workspace.openTextDocument(file);
            await analyzeFile(file, document.getText());
        } catch (e) {
            console.error(`Error analyzing ${file.fsPath}:`, e);
        }
    }

    vscode.window.showInformationMessage(`ACR-QA: Analyzed ${files.length} files`);
}

function getSeverity(severity) {
    switch ((severity || '').toLowerCase()) {
        case 'high':
        case 'critical':
        case 'error':
            return vscode.DiagnosticSeverity.Error;
        case 'medium':
        case 'warning':
            return vscode.DiagnosticSeverity.Warning;
        case 'low':
        case 'info':
            return vscode.DiagnosticSeverity.Information;
        default:
            return vscode.DiagnosticSeverity.Hint;
    }
}

function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.dispose();
    }
}

module.exports = {
    activate,
    deactivate
};
