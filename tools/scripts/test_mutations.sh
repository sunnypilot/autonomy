#!/usr/bin/env bash
set -euo pipefail

if [ -d /opt/venv ]; then
    source /opt/venv/bin/activate
fi

dump_results() {
    echo "Mutation testing results:"
    if ! mutmut results; then
        echo "WARNING: mutmut results crashed (likely unknown exit code such as -6)."
        if [ -d mutants ]; then
            echo "Dumping raw mutant status files for inspection:"
            grep -R "" mutants || true
        fi
    fi
}

show_survivors() {
    if mutmut results >/dev/null 2>&1; then
        mutmut results | grep "survived" | awk '{print $1}' | while read -r s; do
            echo ">>> $s"
            echo
        done
    fi
}

cleanup() {
    rm -rf mutants
    rm -f pyproject.mutmut.toml
}

check_if_tests_exist() {
    if ! pytest --collect-only -q 2>/dev/null; then
        echo "No tests found. Skipping mutation testing."
        exit 0
    fi
}

trap 'dump_results; show_survivors; cleanup; exit 2' INT TERM
trap 'dump_results; show_survivors; cleanup' EXIT

if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ]; then
    base_branch="origin/${GITHUB_BASE_REF:-master}"
    changed_files=$(git diff --name-only "$base_branch"..HEAD --diff-filter=AMR -M | grep -E '\.py$' | grep -v 'navigation/common/params/params.py' || true)

    if [ -z "$changed_files" ]; then
        echo "No Python files changed. Skipping mutation testing."
        exit 0
    fi

    paths=$(echo "$changed_files" | paste -sd "," -)

    cat > pyproject.mutmut.toml <<EOF
[tool.mutmut]
paths_to_exclude = "navigation/common/params/params.py"
paths_to_mutate = "$paths"
EOF

    echo "Starting mutation testing on changed files:"
    echo "$changed_files"
    check_if_tests_exist
    if ! MUTMUT_CONFIG_FILE=pyproject.mutmut.toml timeout 1800 mutmut run --max-children 1; then
        echo "Mutmut run aborted (SIGABRT or similar)."
        exit 1
    fi
else
    echo "Starting full mutation testing with mutmut"
    check_if_tests_exist
    cat > pyproject.mutmut.toml <<EOF
[tool.mutmut]
paths_to_mutate = "**/*.py"
paths_to_exclude = "navigation/common/params/params.py"
EOF

    if ! MUTMUT_CONFIG_FILE=pyproject.mutmut.toml timeout 3600 mutmut run --max-children 1; then
        echo "Mutmut run aborted (SIGABRT or similar)."
        exit 1
    fi
fi

echo "Mutation testing done"

dump_results
show_survivors

if mutmut results 2>/dev/null | grep -q "bad"; then
    echo "FAILED: Survived mutations found"
    exit 1
else
    echo "PASSED: No survived mutations"
fi
