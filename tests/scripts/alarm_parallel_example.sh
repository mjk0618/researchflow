#!/usr/bin/env bash
set -euo pipefail

# Example:
#   tests/scripts/alarm_parallel_example.sh 2 8 tests/fixtures/sample_experiment.py --epochs 1
#
# The first argument controls how many logged alarm jobs can run at once.
# The second argument controls how many total runs to launch.
# --wait keeps each alarm process in the foreground even with --log, so shell
# wait tracks the actual experiment lifetime instead of only the monitor launch.

NUM_PARALLEL="${1:-2}"
shift || true

NUM_RUNS="${1:-4}"
shift || true

SCRIPT_PATH="${1:-tests/fixtures/sample_experiment.py}"
shift || true

SCRIPT_ARGS=("$@")

if [[ "${NUM_PARALLEL}" -lt 1 ]]; then
  echo "NUM_PARALLEL must be >= 1" >&2
  exit 1
fi

if [[ "${NUM_RUNS}" -lt 1 ]]; then
  echo "NUM_RUNS must be >= 1" >&2
  exit 1
fi

run_one() {
  local run_id="$1"
  alarm --log --wait "${SCRIPT_PATH}" \
    --epochs 1 \
    --total-runtime-factor 0 \
    --checkpoint-save-dir "test_artifacts/parallel/run_${run_id}" \
    "${SCRIPT_ARGS[@]}"
}

active_jobs=0

for run_id in $(seq 1 "${NUM_RUNS}"); do
  run_one "${run_id}" &
  active_jobs=$((active_jobs + 1))

  if [[ "${active_jobs}" -ge "${NUM_PARALLEL}" ]]; then
    wait -n
    active_jobs=$((active_jobs - 1))
  fi
done

wait

echo "Completed ${NUM_RUNS} alarm-wrapped foreground jobs with NUM_PARALLEL=${NUM_PARALLEL}."
