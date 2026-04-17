#!/usr/bin/env bash
# =============================================================================
# ACR-QA — Evaluation Repository Setup Script
# =============================================================================
# Clones and pins all evaluation target repositories used in the thesis.
# Run this once after cloning ACR-QA to restore the eval corpus.
#
# Usage:
#   bash scripts/clone_eval_repos.sh
#   bash scripts/clone_eval_repos.sh --force   # re-clone even if exists
#
# Repos cloned into: tmp_repos/
# =============================================================================

set -euo pipefail

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="$ROOT_DIR/tmp_repos"

mkdir -p "$TARGET_DIR"

# Colour helpers
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; }

clone_repo() {
    local name="$1"
    local url="$2"
    local commit="$3"   # exact commit hash to pin (empty = use default branch)
    local dest="$TARGET_DIR/$name"

    if [[ -d "$dest" && "$FORCE" == false ]]; then
        warn "$name already exists — skipping (use --force to re-clone)"
        return
    fi

    if [[ -d "$dest" ]]; then
        rm -rf "$dest"
    fi

    echo "Cloning $name..."
    git clone --quiet "$url" "$dest"

    if [[ -n "$commit" ]]; then
        git -C "$dest" checkout --quiet "$commit"
        ok "$name pinned to $commit"
    else
        ok "$name cloned (latest)"
    fi
}

echo ""
echo "=================================================="
echo "  ACR-QA Evaluation Repository Setup"
echo "=================================================="
echo "  Target directory: $TARGET_DIR"
echo ""

# ── JavaScript / Node.js vulnerable apps ──────────────────────────────────────
clone_repo "DVNA" \
    "https://github.com/appsecco/dvna.git" \
    "9ba473add536f66ac9007966acb2a775dd31277a"

clone_repo "NodeGoat" \
    "https://github.com/OWASP/NodeGoat.git" \
    ""

# ── Python vulnerable apps ────────────────────────────────────────────────────
clone_repo "DVPWA" \
    "https://github.com/anxolerd/dvpwa.git" \
    ""

clone_repo "Pygoat" \
    "https://github.com/adeyosemanputra/pygoat.git" \
    ""

clone_repo "VulPy" \
    "https://github.com/fportantier/vulpy.git" \
    ""

# ── Real-world Python repos (false positive testing) ─────────────────────────
clone_repo "django" \
    "https://github.com/django/django.git" \
    ""

clone_repo "black-fmt" \
    "https://github.com/psf/black.git" \
    ""

clone_repo "sqlalchemy" \
    "https://github.com/sqlalchemy/sqlalchemy.git" \
    ""

clone_repo "pillow" \
    "https://github.com/python-pillow/Pillow.git" \
    ""

echo ""
ok "Done."
