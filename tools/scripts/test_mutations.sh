#!/usr/bin/env bash
set -e

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
        if ! mutmut show "$s"; then
            echo "Failed to show mutation $s"
        fi
        echo
    done
}

cleanup() {
    rm -rf mutants
    rm -f pyproject.mutmut.toml
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
    MUTMUT_CONFIG_FILE=pyproject.mutmut.toml timeout 1800 mutmut run
else
    echo "Starting full mutation testing with mutmut"
    timeout 3600 mutmut run
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
