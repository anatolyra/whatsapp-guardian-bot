# GitHub Workflows

This directory contains GitHub Actions workflows for CI/CD.

## Workflows

### CI (`ci.yml`)

Runs tests on every push to `main` and on every pull request.

**Triggers:**
- Push to `main` branch
- Pull request targeting `main` branch

**Jobs:**
- `test`: Sets up Python 3.11, installs dependencies, runs pytest

---

### PR Check (`pr-check.yml`)

Enforces version bump labels on every pull request targeting `main`.

**Triggers:**
- Pull request opened, synchronized, labeled, or unlabeled

**Requirements:**
- PR must have exactly one of these labels: `major`, `minor`, or `patch`
- Fails if no label or multiple labels are present

**Label Meanings:**
| Label | Version Bump | Use Case |
|-------|---------------|----------|
| `major` | X.0.0 | Breaking changes |
| `minor` | 0.X.0 | New features (backward compatible) |
| `patch` | 0.0.X | Bug fixes |

---

### Release (`release.yml`)

Manual workflow for creating versioned releases.

**Triggers:**
- Manual dispatch via GitHub Actions UI

**Inputs:**
- `dry-run` (boolean): Preview version without releasing (default: `false`)

**Process:**
1. Gets latest tag (e.g., `v0.1.0`)
2. Queries merged PRs since that tag
3. Calculates new version from PR labels using sequential SemVer
4. If `dry-run`: outputs version and PR list, then stops
5. If not `dry-run`:
   - Runs tests
   - Builds Docker image
   - Pushes to `ghcr.io` with version tag + `latest`
   - Creates git tag
   - Creates GitHub Release with PR authors

**Version Calculation:**

Versions are calculated from merged PR labels using **sequential SemVer**:

```
Example: v0.1.0 → v0.2.3

PR #1: patch → v0.1.0 → v0.1.1
PR #2: patch → v0.1.1 → v0.1.2
PR #3: minor → v0.1.2 → v0.2.0  (minor resets patch)
PR #4: patch → v0.2.0 → v0.2.1
PR #5: patch → v0.2.1 → v0.2.2
PR #6: patch → v0.2.2 → v0.2.3

Final version: v0.2.3
```

**Sequential SemVer Rules:**
- `major` bumps major, resets minor and patch to 0
- `minor` bumps minor, resets patch to 0
- `patch` bumps patch

## How to Release

1. Ensure all PRs since last release have version labels (`major`, `minor`, `patch`)
2. Go to Actions → Release workflow
3. Click "Run workflow"
4. Select branch and `dry-run` input
5. For preview: run with `dry-run: true`
6. For actual release: run with `dry-run: false`

## First Release

Before the first release:
1. Create an initial tag (v0.0.0) pointing to a commit before any merged PRs
2. The release workflow will calculate version from PRs merged after that tag

```bash
git tag -a v0.0.0 <base-commit> -m "Initial release"
git push origin v0.0.0
```