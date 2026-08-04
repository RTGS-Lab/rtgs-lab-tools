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

set -e  # Exit on any error

# Parse command line arguments
START_DATE="${1:-}"
END_DATE="${2:-}"
NODE_IDS="${3:-}"
PROJECT="${4:-ALL}"

# Retry policy. A healthy run takes about 80 seconds, so the per-attempt limit
# is deliberately loose: it exists to catch a hang, not to police a slow day.
MAX_ATTEMPTS="${DEVICEMON_MAX_ATTEMPTS:-3}"
ATTEMPT_TIMEOUT="${DEVICEMON_ATTEMPT_TIMEOUT:-1800}"
RETRY_DELAY="${DEVICEMON_RETRY_DELAY:-300}"

# Set up working directory and log file
WORK_DIR="$HOME/rtgs-lab-tools-cron"
LOG_DIR="$HOME/logs/device-monitoring-logs"
LOG_FILE="$LOG_DIR/device_monitoring_$(date +%Y%m%d_%H%M%S).log"
LOCK_FILE="$WORK_DIR/device_monitoring.lock"

# Create directories if they don't exist
mkdir -p "$WORK_DIR"
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
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
log "Retry policy: up to $MAX_ATTEMPTS attempts, ${ATTEMPT_TIMEOUT}s limit each, ${RETRY_DELAY}s between"

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

# Setup repository - clone once, then just update
REPO_DIR="$WORK_DIR/rtgs-lab-tools"
if [ -d "$REPO_DIR" ]; then
    log "Repository exists, updating with git pull..."
    cd "$REPO_DIR"
    git pull || {
        log "Git pull failed, repository may be corrupted. Removing and re-cloning..."
        cd "$WORK_DIR"
        rm -rf rtgs-lab-tools
        git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
        cd rtgs-lab-tools
    }
else
    log "Repository doesn't exist, cloning..."
    cd "$WORK_DIR"
    git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
    cd rtgs-lab-tools
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

# Source RTGS credentials (use generic path)
if [ -f "$HOME/.rtgs_credentials" ]; then
    source "$HOME/.rtgs_credentials"
    log "Loaded credentials from $HOME/.rtgs_credentials"
elif [ -f "$HOME/.rtgs_creds" ]; then
    source "$HOME/.rtgs_creds"
    log "Loaded credentials from $HOME/.rtgs_creds"
else
    log "ERROR: No credentials file found. Expected $HOME/.rtgs_credentials or $HOME/.rtgs_creds"
    exit 1
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
    MONITOR_CMD="$MONITOR_CMD --start_date=$START_DATE"
fi

if [ -n "$END_DATE" ]; then
    MONITOR_CMD="$MONITOR_CMD --end_date=$END_DATE"
fi

if [ -n "$NODE_IDS" ]; then
    MONITOR_CMD="$MONITOR_CMD --node_ids=$NODE_IDS"
fi

if [ "$PROJECT" != "ALL" ]; then
    MONITOR_CMD="$MONITOR_CMD --project=$PROJECT"
fi

# Pin one timestamp for the whole day and keep it across retries, so a retried
# report replaces the rows of the attempt it is repeating rather than adding a
# second near-identical entry to the web app's list of monitoring timestamps.
export DEVICEMON_RUN_TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"
log "Monitoring run timestamp: $DEVICEMON_RUN_TIMESTAMP"

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
