## lint.sh
A fast linting script adapted from [sunnypilot/openpilot](https://github.com/sunnypilot/sunnypilot/blob/master/scripts/lint/lint.sh). 
It runs various basic quality checks on the repository.

### Checks Performed
- **Ruff**: Linting and formatting for Python code.
- **MyPy**: Static type checking for Python.
- **CodeSpell**: Spell checking for code and comments.
- **Pre-commit Hooks**:
  - Check for added large files (>120KB).
  - Verify shebang scripts are executable.
  - Validate shebang format (`#!/usr/bin/env python3` or `#!/usr/bin/env bash`).
  - Check for "NOMERGE" comments.

### Usage
Run from the repository root:

```bash
./tools/scripts/lint.sh [options]
```

### Options
- `-f, --fast`: Skip slow checks (MyPy and CodeSpell).
- `-s, --skip <tests>`: Skip specific tests (space-separated).
- `-h, --help`: Show help.

### Examples
- Run all checks: `./tools/scripts/lint.sh`
- Run only Ruff and MyPy: `./tools/scripts/lint.sh ruff mypy`
- Skip MyPy: `./tools/scripts/lint.sh --skip mypy`

### Requirements
- Virtual environment must be set up (see main README).
- Testing dependencies installed (`uv pip install -e ".[testing]"`).

## test_mutations.sh
A script to run mutation testing using mutmut for CI.

### Description
- Runs a baseline to ensure tests pass without mutations.
- Dumps results for completed mutations (survived or killed), showing the mutation details, test outcome, and diff.

### Usage
Run from the repository root:

```bash
./tools/scripts/test_mutations.sh
```

### Requirements
- Virtual environment must be set up (see main README).
- Testing dependencies installed (`uv sync --group testing`).
- mutmut configuration (creates a temp `pyproject.mutmut.toml` for PRs or default config).

### Output
Displays JSON-formatted results for tested mutations, filtered to show only those with outcomes.

## Other Scripts
- `check_nomerge_comments.sh`: Checks for "NOMERGE" comments in files.
- `check_shebang_format.sh`: Validates shebang lines in scripts.
