#!/bin/bash
export PYTHONUTF8=1	# ensure proper encoding so that this script can print emojis without error
export PYTHONUNBUFFERED=1	# flush python output to the log as it happens, so a run that dies mid-way still leaves a usable log
# Scheduled Device Monitoring Script for CRON
# Based on .github/workflows/daily-device-monitoring.yml
#
# Usage: ./scheduled_device_monitoring.sh [start_date] [end_date] [node_ids] [project]
# All parameters are optional and will use defaults if not provided
#
# Tunable via the environment:
#   DEVICEMON_MAX_ATTEMPTS     how many times to run the report before giving up (default 3)
#   DEVICEMON_ATTEMPT_TIMEOUT  hard wall-clock limit per attempt, seconds (default 1800)
#   DEVICEMON_RETRY_DELAY      pause between attempts, seconds (default 300)
#
# Paths (defaults = the lab's shared MSI workspace, run from Bryan's scrontab):
#   DEVICEMON_BASE_DIR    /projects/standard/runck014/shared/device_monitoring
#   DEVICEMON_WORK_DIR    $DEVICEMON_BASE_DIR/rtgs-lab-tools-cron   (clone + venv live here)
#   DEVICEMON_LOG_DIR     $DEVICEMON_BASE_DIR/logs
#   DEVICEMON_CREDS_FILE  $DEVICEMON_BASE_DIR/credentials/.rtgs_credentials
#                         (mode 660, group runck014; holds DEVICEMON_INGEST_URL/TOKEN)
#   DEVICEMON_BATCH_DIR   $DEVICEMON_LOG_DIR/batches   (each batch saved before it is sent)

set -e  # Exit on any error

# Fingerprint of the copy now running; see the release pin below.
SELF_SHA="$(sha1sum < "${BASH_SOURCE[0]}")"

# Parse command line arguments
START_DATE="${1:-}"
END_DATE="${2:-}"
NODE_IDS="${3:-}"
PROJECT="${4:-ALL}"

# Retry policy. A healthy run takes about 80 seconds, so the per-attempt limit
# is deliberately loose: it exists to catch a hang, not to police a slow day.
#
# IMPORTANT: under scrontab this script runs as a SLURM job, and SLURM kills the
# entire job step -- this script and its children together, with no chance to
# log anything -- the moment #SCRON --time is reached. The worst case below is
# MAX_ATTEMPTS*ATTEMPT_TIMEOUT + (MAX_ATTEMPTS-1)*RETRY_DELAY = 34 minutes, so
# --time must be comfortably above that (01:00:00 is the intended pairing).
# Raising these values without raising --time makes the retries unreachable.
MAX_ATTEMPTS="${DEVICEMON_MAX_ATTEMPTS:-3}"
ATTEMPT_TIMEOUT="${DEVICEMON_ATTEMPT_TIMEOUT:-600}"
RETRY_DELAY="${DEVICEMON_RETRY_DELAY:-120}"

# Set up working directory and log file. Group-shared workspace: files stay group-readable,
# never world-readable.
umask 007
BASE_DIR="${DEVICEMON_BASE_DIR:-/projects/standard/runck014/shared/device_monitoring}"
WORK_DIR="${DEVICEMON_WORK_DIR:-$BASE_DIR/rtgs-lab-tools-cron}"
LOG_DIR="${DEVICEMON_LOG_DIR:-$BASE_DIR/logs}"
CREDS_FILE="${DEVICEMON_CREDS_FILE:-$BASE_DIR/credentials/.rtgs_credentials}"
export DEVICEMON_BATCH_DIR="${DEVICEMON_BATCH_DIR:-$LOG_DIR/batches}"
LOG_FILE="$LOG_DIR/device_monitoring_$(date +%Y%m%d_%H%M%S).log"
LOCK_FILE="$WORK_DIR/device_monitoring.lock"

# Create directories if they don't exist
mkdir -p "$WORK_DIR"
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $1" | tee -a "$LOG_FILE"
}

# Simple cleanup function - just deactivate venv
cleanup() {
    # Deactivate venv if active
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate || true
        log "Deactivated virtual environment"
    fi
    log "Cleanup completed - keeping persistent directory for reuse"
}

# Record why we stopped. Previously cleanup() was defined but never wired up to
# a trap, so a script killed by a signal left no trace at all in the log.
# SIGKILL still cannot be caught, but everything else now says so on the way out.
on_signal() {
    log "ERROR: Received SIG$1 - aborting device monitoring"
    exit 128
}
trap 'on_signal TERM' TERM
trap 'on_signal INT' INT
trap 'on_signal HUP' HUP
trap cleanup EXIT

log "Starting daily device monitoring"
log "Work directory: $WORK_DIR"
log "Log directory: $LOG_DIR"
log "Parameters: start_date=$START_DATE, end_date=$END_DATE, node_ids=$NODE_IDS, project=$PROJECT"
RETRY_BUDGET=$(( MAX_ATTEMPTS * ATTEMPT_TIMEOUT + (MAX_ATTEMPTS - 1) * RETRY_DELAY ))
log "Retry policy: up to $MAX_ATTEMPTS attempts, ${ATTEMPT_TIMEOUT}s limit each, ${RETRY_DELAY}s between (worst case ${RETRY_BUDGET}s)"

# Under SLURM, say up front how much room we actually have. A job time limit
# below the retry budget means later attempts can never run, and the kill
# arrives as a SIGKILL that leaves no trace in this log.
if [ -n "$SLURM_JOB_ID" ]; then
    log "Running as SLURM job $SLURM_JOB_ID"
    if command -v squeue &> /dev/null; then
        SLURM_TIMELIMIT="$(squeue -h -j "$SLURM_JOB_ID" -o %l 2>/dev/null || true)"
        log "SLURM time limit for this job: ${SLURM_TIMELIMIT:-unknown} (retry budget needs ${RETRY_BUDGET}s)"
    fi
fi

# Refuse to start if yesterday's run is somehow still alive. Two concurrent
# runs would write competing rows for the same nodes, and a hung run holding
# stale database connections is not something to pile onto.
if command -v flock &> /dev/null; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        log "ERROR: Another device monitoring run still holds $LOCK_FILE - exiting"
        log "Check for a stuck process with: ps -u \"$USER\" -o pid,lstart,etime,cmd | grep rtgs"
        exit 1
    fi
else
    log "Warning: flock not available, cannot guard against overlapping runs"
fi

# Change to work directory
cd "$WORK_DIR"
log "Changed to work directory: $(pwd)"

# Load required modules (if running on HPC/cluster environment)
log "Loading required modules"
if command -v module &> /dev/null; then
    module load python || log "Warning: Could not load python module"
    module load git || log "Warning: Could not load git module"
else
    log "Module command not found, assuming modules are already available"
fi

# Source RTGS credentials: the shared file (DEVICEMON_CREDS_FILE); the per-user files are a
# fallback for running from a personal account.
CREDS_LOADED=0
for f in "$CREDS_FILE" "$HOME/.rtgs_credentials" "$HOME/.rtgs_creds"; do
    [ -f "$f" ] || continue
    source "$f"; CREDS_LOADED=1
    log "Loaded credentials from $f"
    break
done
if [ "$CREDS_LOADED" -eq 0 ]; then
    log "ERROR: No credentials found: expected $CREDS_FILE (or ~/.rtgs_credentials, ~/.rtgs_creds)"
    exit 1
fi

# Where the results go. Publishing to device-monitoring-ingest is the supported path; the direct
# Cloud SQL write (DEVICEMON_INSTANCE_CONNECTION_NAME + a service-account key) is deprecated, and
# with neither set the pipeline would silently write a SQLite file inside this clone.
if [ -n "${DEVICEMON_INGEST_URL:-}" ] && [ -n "${DEVICEMON_INGEST_TOKEN:-}" ]; then
    log "Results go to the ingest service: $DEVICEMON_INGEST_URL"
elif [ -n "${DEVICEMON_INSTANCE_CONNECTION_NAME:-}" ]; then
    log "WARNING: DEVICEMON_INGEST_URL/TOKEN unset; writing Cloud SQL directly (deprecated)"
else
    log "ERROR: set DEVICEMON_INGEST_URL and DEVICEMON_INGEST_TOKEN in $CREDS_FILE"
    exit 1
fi

# Setup repository and pin the release. The cron runs a tagged release, never a moving branch.
# DEVICEMON_RELEASE (in the credentials file):
#   devmon-v0.1.0      pinned: editing this one line on MSI is the deploy
#   track:devmon-v*    newest tag matching the glob, fetched every run: pushing a tag is the deploy
#   (unset)            stay on the current checkout, unpinned, with a warning
REPO_DIR="$WORK_DIR/rtgs-lab-tools"
if [ ! -d "$REPO_DIR/.git" ]; then
    log "Repository doesn't exist, cloning..."
    rm -rf "$REPO_DIR"
    git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git "$REPO_DIR"
fi
cd "$REPO_DIR"

select_release() {
    if ! git fetch --quiet --tags --force origin; then
        log "WARNING: git fetch failed; staying on $(git describe --tags --always)"
        return 0
    fi
    local want="${DEVICEMON_RELEASE:-}"
    if [ -z "$want" ]; then
        log "WARNING: DEVICEMON_RELEASE unset; running $(git describe --tags --always) unpinned"
        return 0
    fi
    if [[ $want == track:* ]]; then
        want="$(git tag -l "${want#track:}" --sort=-v:refname | head -n 1)"
        [ -n "$want" ] || { log "ERROR: no tag matches ${DEVICEMON_RELEASE#track:}"; return 1; }
    fi
    git rev-parse -q --verify "refs/tags/$want" >/dev/null \
        || { log "ERROR: release tag $want not found"; return 1; }
    if [ "$(git rev-parse HEAD)" != "$(git rev-parse "refs/tags/$want^{commit}")" ]; then
        git checkout --quiet --detach "refs/tags/$want"
        log "Checked out release $want"
    else
        log "Release $want already checked out"
    fi
    export DEVICEMON_RELEASE="$want"
}
select_release || exit 1

# If the release carries a different version of this script, run that one instead (once).
NEW_SELF="$REPO_DIR/src/rtgs_lab_tools/device_monitoring/scheduled_device_monitoring.sh"
if [ -z "${DEVICEMON_REEXEC:-}" ] && [ -f "$NEW_SELF" ] \
        && [ "$(sha1sum < "$NEW_SELF")" != "$SELF_SHA" ]; then
    log "Script differs in ${DEVICEMON_RELEASE:-this checkout}; re-running that copy"
    exec env DEVICEMON_REEXEC=1 bash "$NEW_SELF" "$@"
fi

# Only run installation if venv doesn't exist or if it's a fresh clone
if [ ! -d "venv" ]; then
    log "Virtual environment not found, running installation"
    bash install.sh
else
    log "Virtual environment exists, skipping installation"
fi

# Check if virtual environment was created
if [ ! -d "venv" ]; then
    log "ERROR: Virtual environment not found after installation"
    exit 1
fi

# Activate virtual environment. Check both layouts: venv puts the activate
# script in bin/ on Linux and Scripts/ on Windows, and a venv rebuilt by
# install.sh on the cluster would land in bin/ and silently break the hardcoded
# path under `set -e`.
log "Activating virtual environment"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    log "ERROR: No activate script found in venv/bin or venv/Scripts"
    exit 1
fi


# A new release may bring new dependencies: refresh the editable install once per release.
STAMP="venv/.devmon-installed-release"
if [ "$(cat "$STAMP" 2>/dev/null)" != "${DEVICEMON_RELEASE:-unpinned}" ]; then
    log "Installing rtgs-lab-tools for release ${DEVICEMON_RELEASE:-unpinned}"
    if command -v uv &> /dev/null; then
        uv pip install --quiet -e . && echo "${DEVICEMON_RELEASE:-unpinned}" > "$STAMP"
    else
        pip install --quiet -e . && echo "${DEVICEMON_RELEASE:-unpinned}" > "$STAMP"
    fi
fi

# Verify rtgs command is available
if ! command -v rtgs &> /dev/null; then
    log "ERROR: rtgs command not found in virtual environment"
    exit 1
fi

# Build the monitoring command
MONITOR_CMD="rtgs device-monitoring monitor"

# Add optional parameters if provided
if [ -n "$START_DATE" ]; then
    MONITOR_CMD="$MONITOR_CMD --start-date=$START_DATE"
fi

if [ -n "$END_DATE" ]; then
    MONITOR_CMD="$MONITOR_CMD --end-date=$END_DATE"
fi

if [ -n "$NODE_IDS" ]; then
    MONITOR_CMD="$MONITOR_CMD --node-ids=$NODE_IDS"
fi

if [ "$PROJECT" != "ALL" ]; then
    MONITOR_CMD="$MONITOR_CMD --project=$PROJECT"
fi

# Pin one timestamp for the whole day and keep it across retries, so a retried
# report replaces the rows of the attempt it is repeating rather than adding a
# second near-identical entry to the web app's list of monitoring timestamps.
# -u because the pipeline stores UTC throughout: device timestamps come from
# GEMS publish_time (UTC), and mixing in the cluster's local Central time is
# what made "last connected" read five hours ahead of the report that found it.
export DEVICEMON_RUN_TIMESTAMP="$(date -u '+%Y-%m-%d %H:%M')"
log "Monitoring run timestamp: $DEVICEMON_RUN_TIMESTAMP UTC"

# Cap each attempt so a hang becomes a failure the retry loop can act on.
# --kill-after sends SIGKILL if the process ignores the initial SIGTERM.
if command -v timeout &> /dev/null; then
    TIMEOUT_PREFIX="timeout --kill-after=60 $ATTEMPT_TIMEOUT"
else
    log "Warning: timeout not available, attempts will run unbounded"
    TIMEOUT_PREFIX=""
fi

EXIT_CODE=1
ATTEMPT=1

while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
    log "Attempt $ATTEMPT/$MAX_ATTEMPTS - running command: $MONITOR_CMD"

    # set +e so a failed attempt does not abort the script before it can retry.
    set +e
    $TIMEOUT_PREFIX $MONITOR_CMD >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    set -e

    if [ "$EXIT_CODE" -eq 0 ]; then
        log "Device monitoring completed successfully on attempt $ATTEMPT"
        break
    fi

    # 124 = timeout sent SIGTERM; 137 = it had to escalate to SIGKILL.
    if [ "$EXIT_CODE" -eq 124 ] || [ "$EXIT_CODE" -eq 137 ]; then
        log "ERROR: Attempt $ATTEMPT hit the ${ATTEMPT_TIMEOUT}s limit and was killed (exit $EXIT_CODE)"
    else
        log "ERROR: Attempt $ATTEMPT failed with exit code $EXIT_CODE"
    fi

    if [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; then
        log "Retrying in ${RETRY_DELAY}s"
        sleep "$RETRY_DELAY"
    fi

    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$EXIT_CODE" -ne 0 ]; then
    log "ERROR: Device monitoring failed on all $MAX_ATTEMPTS attempts - no report for today"
fi

# Virtual environment is deactivated by cleanup() on exit.
log "Script completed with exit code $EXIT_CODE"

# Exit with the same code as the monitoring command
exit $EXIT_CODE
