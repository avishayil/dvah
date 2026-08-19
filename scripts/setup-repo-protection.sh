#!/usr/bin/env bash
#
# One-time repo hardening for accepting community pull requests.
# Idempotent: safe to re-run. Requires `gh` authenticated to github.com with
# admin rights on the repo:
#
#     gh auth login --hostname github.com
#     bash scripts/setup-repo-protection.sh
#
# This LOCKS main: after running, force-pushes and direct pushes are rejected —
# all changes must land via PR. That deliberately ends the "amend the initial
# commit + force-push" workflow.

set -euo pipefail

REPO="${DVAH_REPO:-avishayil/dvah}"
BRANCH="${DVAH_BRANCH:-main}"

echo "==> Protecting ${REPO}@${BRANCH}"
# Required checks are the job names from ci.yml (test, web) + dependency-review.
# CodeQL is intentionally NOT required so a scanner hiccup can't block a merge.
gh api -X PUT "repos/${REPO}/branches/${BRANCH}/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test", "web", "review"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "require_code_owner_reviews": true,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON

echo "==> Enabling GitHub Pages (source = GitHub Actions)"
# Create, or fall back to update if it already exists.
gh api -X POST "repos/${REPO}/pages" \
  -H "Accept: application/vnd.github+json" \
  -f "build_type=workflow" 2>/dev/null \
  || gh api -X PUT "repos/${REPO}/pages" \
       -H "Accept: application/vnd.github+json" \
       -f "build_type=workflow"

echo "==> Enabling secret scanning + push protection"
gh api -X PATCH "repos/${REPO}" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "security_and_analysis": {
    "secret_scanning": { "status": "enabled" },
    "secret_scanning_push_protection": { "status": "enabled" }
  }
}
JSON

echo "==> Enabling Dependabot vulnerability ALERTS (no auto-PRs)"
gh api -X PUT "repos/${REPO}/vulnerability-alerts" \
  -H "Accept: application/vnd.github+json"
# NOTE: intentionally NOT enabling automated-security-fixes (that opens PRs).

echo "==> Setting default workflow token to read-only"
gh api -X PUT "repos/${REPO}/actions/permissions/workflow" \
  -H "Accept: application/vnd.github+json" \
  -f "default_workflow_permissions=read" \
  -F "can_approve_pull_request_reviews=false"

cat <<'NOTE'

==> Done. One setting the API can't reliably toggle — do it in the UI:
    Settings → Actions → General → "Fork pull request workflows from outside
    collaborators" → require approval for ALL outside collaborators.

Verify:
    gh api repos/avishayil/dvah/branches/main/protection | jq '.required_status_checks, .allow_force_pushes'
NOTE
