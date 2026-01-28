# ACR-QA VSCode Extension

AI-powered code review and quality assurance directly in your editor.

## Features

- **Real-time Code Analysis**: Analyze Python files for security, design, and style issues
- **Inline Diagnostics**: See issues highlighted directly in your code
- **AI Explanations**: Get detailed explanations for each finding
- **Quick Fixes**: Apply automatic fixes for common issues
- **Workspace Analysis**: Analyze entire projects at once

## Installation

### From VSIX
1. Download `acrqa-vscode-1.0.0.vsix`
2. Open VSCode
3. Go to Extensions (Ctrl+Shift+X)
4. Click "..." menu → "Install from VSIX"
5. Select the downloaded file

### From Source
```bash
cd vscode-extension
npm install
npm run package
code --install-extension acrqa-vscode-1.0.0.vsix
```

## Setup

1. Ensure ACR-QA backend is running:
   ```bash
   python FRONTEND/app.py
   ```

2. Configure the extension:
   - Open VSCode Settings (Ctrl+,)
   - Search for "ACR-QA"
   - Set API URL (default: `http://localhost:5000`)

## Usage

### Analyze Current File
- Command Palette (Ctrl+Shift+P) → "ACR-QA: Analyze Current File"
- Or use keyboard shortcut (if configured)

### Analyze Workspace
- Command Palette → "ACR-QA: Analyze Workspace"
- Analyzes all Python files in your project

### Auto-Analysis on Save
Enable in settings:
```json
{
  "acrqa.enableAutoAnalysis": true
}
```

### Clear Diagnostics
- Command Palette → "ACR-QA: Clear Diagnostics"

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `acrqa.apiUrl` | `http://localhost:5000` | ACR-QA API endpoint |
| `acrqa.enableAutoAnalysis` | `false` | Analyze files on save |

## Issue Severity

- 🔴 **Error** (High): Critical security or logic issues
- 🟡 **Warning** (Medium): Design flaws, potential bugs
- 🔵 **Info** (Low): Style violations, minor improvements

## Requirements

- VSCode 1.75.0 or higher
- ACR-QA backend running
- Python files in workspace

## Known Limitations

- Currently supports Python only
- Requires ACR-QA backend to be running locally
- Large workspaces may take time to analyze

## Troubleshooting

**Extension not working?**
1. Check ACR-QA backend is running: `curl http://localhost:5000/api/runs`
2. Check VSCode console for errors: Help → Toggle Developer Tools
3. Verify Python files are in workspace

**No diagnostics showing?**
1. Ensure file is saved
2. Check file is `.py` extension
3. Try "ACR-QA: Analyze Current File" command

## Development

```bash
# Install dependencies
npm install

# Package extension
npm run package

# Install locally
code --install-extension acrqa-vscode-1.0.0.vsix
```

## License

MIT

## Support

- GitHub: [ACR-QA Repository](https://github.com/ahmed-145/ACR-QA)
- Issues: [Report a Bug](https://github.com/ahmed-145/ACR-QA/issues)
