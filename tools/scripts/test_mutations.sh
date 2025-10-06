#!/usr/bin/env bash
set -u -o pipefail

if [ -d /opt/venv ]; then
    source /opt/venv/bin/activate
fi

dump_results() {
    echo "Mutation testing results:"
    mutmut results
}

show_survivors() {
    mutmut results | grep "survived" | awk '{print $1}' | while read -r s; do
        echo ">>> $s"
        echo
    done
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

if [ "$GITHUB_EVENT_NAME" = "pull_request" ]; then
    base_branch="origin/${GITHUB_BASE_REF:-master}"
    changed_files=$(git diff --name-only "$base_branch"..HEAD --diff-filter=AMR -M | grep -E '\.py$' || true)

    if [ -z "$changed_files" ]; then
        echo "No Python files changed. Skipping mutation testing."
        exit 0
    fi

    paths=$(echo "$changed_files" | paste -sd "," -)

    # Write temporary config
    cat > pyproject.mutmut.toml <<EOF
[tool.mutmut]
paths_to_mutate = "$paths"
EOF

    echo "Starting mutation testing on changed files:"
    echo "$changed_files"
    check_if_tests_exist
    MUTMUT_CONFIG_FILE=pyproject.mutmut.toml timeout 1800 mutmut run --max-children 1
else
    echo "Starting full mutation testing with mutmut"
    check_if_tests_exist
    timeout 3600 mutmut run --max-children 1
fi

echo "Mutation testing done"

dump_results
show_survivors

if mutmut results | grep -q "bad"; then
    echo "FAILED: Survived mutations found"
    exit 1
else
    echo "PASSED: No survived mutations"
fi
