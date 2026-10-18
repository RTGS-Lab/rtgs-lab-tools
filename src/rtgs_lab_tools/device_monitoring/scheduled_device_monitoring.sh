#!/bin/bash
# Scheduled Device Monitoring Script for CRON (MSI scrontab, Bryan's account)
# Based on .github/workflows/daily-device-monitoring.yml
#
# Usage: ./scheduled_device_monitoring.sh [start_date] [end_date] [node_ids] [project]
#        ./scheduled_device_monitoring.sh --check-creds <file>
#            parse a credentials file the way a run would and list the accepted / rejected
#            names (never values), then exit
# All run parameters are optional and will use defaults if not provided.
#
# Trust model. The workspace is shared with the lab group, so only logs/ is group-writable.
# Everything that decides what code runs is Bryan's alone:
#   - this script, its directory, the checkout and the venv: owned by the running user and not
#     group- or world-writable (dirs 2750, files 640/750). The script refuses to run otherwise.
#   - the release pin: ~/.config/devmon/release, "<tag> <40-hex commit>", owned by the running
#     user, not group/world-writable. Both the tag and its commit are checked.
#   - the ingest token: fetched from Secret Manager each run with ~/.config/devmon/sa.json (600)
#     by the Python side; it is never in the environment, a file, or a command line.
#   - the shared credentials file is DATA: KEY=VALUE lines parsed against an allowlist, never
#     sourced. Paths, PATH, LD_*, PYTHON*, the release and the token are refused from it.
#
# Tunable via the environment (scrontab or the caller, not the credentials file):
#   DEVICEMON_MAX_ATTEMPTS     how many times to run the report before giving up (default 3)
#   DEVICEMON_ATTEMPT_TIMEOUT  hard wall-clock limit per attempt, seconds (default 600)
#   DEVICEMON_RETRY_DELAY      pause between attempts, seconds (default 120)
#   DEVICEMON_SA_KEY           service-account key (default ~/.config/devmon/sa.json)
#   DEVICEMON_TOKEN_SECRET     secret name (default follows the URL: prod or -test)
#   DEVICEMON_RELEASE_FILE     release pin (default ~/.config/devmon/release)
#   DEVICEMON_PYTHON_MODULE    module that provides Python >= 3.10 (default
#                              python3/3.12.4_anaconda2024.06-1_libmamba; agate's bare
#                              `module load python` left /usr/bin/python3 = 3.6.8 on PATH)
#   DEVICEMON_PYTHON           interpreter to build the venv with (absolute path); skips the
#                              module lookup
#   DEVICEMON_EMAIL            1 = send the notification email after each run; default off
#                              (the dashboard is the place to look; Bryan, 2026-10-18)
#
# Paths (defaults = the lab's shared MSI workspace):
#   DEVICEMON_BASE_DIR    /projects/standard/runck014/shared/device_monitoring
#   DEVICEMON_WORK_DIR    $DEVICEMON_BASE_DIR/rtgs-lab-tools-cron   (clone + venv live here)
#   DEVICEMON_LOG_DIR     $DEVICEMON_BASE_DIR/logs                  (2770: the one shared dir)
#   DEVICEMON_CREDS_FILE  $DEVICEMON_BASE_DIR/credentials/.rtgs_credentials
#   DEVICEMON_BATCH_DIR   $DEVICEMON_LOG_DIR/batches                (2770)
#   lock file             ~/.cache/devmon/device_monitoring.lock    (Bryan-owned)

set -e  # Exit on any error

export PYTHONUTF8=1	# ensure proper encoding so that this script can print emojis without error
export PYTHONUNBUFFERED=1	# flush python output to the log as it happens

# Names the shared credentials file may set. Everything else is refused (and named in the log).
CREDS_ALLOW=" DEVICEMON_INGEST_URL PARTICLE_ACCESS_TOKEN DB_HOST DB_PORT DB_NAME DB_USER \
DB_PASSWORD LOGGING_DB_HOST LOGGING_DB_PORT LOGGING_DB_NAME LOGGING_DB_USER LOGGING_DB_PASSWORD \
POSTGRES_LOGGING_STATUS GMAIL_USER GMAIL_APP_PASSWORD GMAIL_RECIPIENT "
CREDS_ACCEPTED=""
CREDS_REJECTED=""

# parse_creds <file>: export allowlisted KEY=VALUE lines. No eval, no source, no expansion:
# a value is taken literally after stripping one pair of matching outer quotes.
parse_creds() {
    local file="$1" line name value n=0
    CREDS_ACCEPTED=""; CREDS_REJECTED=""
    while IFS= read -r line || [ -n "$line" ]; do
        n=$((n + 1))
        line="${line%$'\r'}"
        [[ $line =~ ^[[:space:]]*(#|$) ]] && continue
        if [[ $line =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            name="${BASH_REMATCH[2]}"; value="${BASH_REMATCH[3]}"
        else
            CREDS_REJECTED+=" line$n(not-KEY=VALUE)"; continue
        fi
        if [[ $value =~ ^\"(.*)\"[[:space:]]*$ ]] || [[ $value =~ ^\'(.*)\'[[:space:]]*$ ]]; then
            value="${BASH_REMATCH[1]}"
        else
            value="${value%%[[:space:]]#*}"           # trailing comment on an unquoted value
            value="${value%"${value##*[![:space:]]}"}" # trailing whitespace
        fi
        case "$name" in
            DEVICEMON_INGEST_TOKEN) CREDS_REJECTED+=" $name(now-from-Secret-Manager:delete-it)"
                                    continue ;;
            *_DIR|*_FILE|PATH|LD_*|PYTHON*|DEVICEMON_*|GOOGLE_*|BASH*|ENV|HOME|IFS)
                if [ "$name" != DEVICEMON_INGEST_URL ]; then
                    CREDS_REJECTED+=" $name(forbidden)"; continue
                fi ;;
        esac
        if [[ $CREDS_ALLOW != *" $name "* ]]; then
            CREDS_REJECTED+=" $name(not-allowlisted)"; continue
        fi
        export "$name=$value"
        CREDS_ACCEPTED+=" $name"
    done < "$file"
}

if [ "${1:-}" = "--check-creds" ]; then
    [ -r "${2:-}" ] || { echo "usage: $0 --check-creds <readable file>" >&2; exit 2; }
    ( parse_creds "$2"
      for v in $CREDS_ACCEPTED; do val="${!v}"; echo "accepted $v len=${#val}"; done
      for v in $CREDS_REJECTED; do echo "rejected $v"; done )
    exit 0
fi

# Fingerprint of the copy now running; see the release pin below.
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
SELF_SHA="$(sha1sum < "$SELF")"

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
MAX_ATTEMPTS="${DEVICEMON_MAX_ATTEMPTS:-3}"
ATTEMPT_TIMEOUT="${DEVICEMON_ATTEMPT_TIMEOUT:-600}"
RETRY_DELAY="${DEVICEMON_RETRY_DELAY:-120}"

# Code and venv: group may read, never write. Logs inherit the setgid group of logs/.
umask 027
BASE_DIR="${DEVICEMON_BASE_DIR:-/projects/standard/runck014/shared/device_monitoring}"
WORK_DIR="${DEVICEMON_WORK_DIR:-$BASE_DIR/rtgs-lab-tools-cron}"
LOG_DIR="${DEVICEMON_LOG_DIR:-$BASE_DIR/logs}"
CREDS_FILE="${DEVICEMON_CREDS_FILE:-$BASE_DIR/credentials/.rtgs_credentials}"
RELEASE_FILE="${DEVICEMON_RELEASE_FILE:-$HOME/.config/devmon/release}"
export DEVICEMON_BATCH_DIR="${DEVICEMON_BATCH_DIR:-$LOG_DIR/batches}"
LOCK_DIR="$HOME/.cache/devmon"
LOCK_FILE="$LOCK_DIR/device_monitoring.lock"
REPO_DIR="$WORK_DIR/rtgs-lab-tools"
# The token only ever comes from Secret Manager here.
unset DEVICEMON_INGEST_TOKEN DEVICEMON_RELEASE GOOGLE_APPLICATION_CREDENTIALS

mkdir -p "$LOG_DIR" "$DEVICEMON_BATCH_DIR"
mkdir -p -m 700 "$LOCK_DIR"

# Unpredictable log name in the shared dir, created exclusively by mktemp, then held open on
# fd 3 for the whole run: a file swapped in under the same name later is never written to.
LOG_FILE="$(mktemp "$LOG_DIR/device_monitoring_$(date +%Y%m%d_%H%M%S)_XXXXXX.log")"
exec 3>>"$LOG_FILE"
chmod 640 "$LOG_FILE"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S %Z')] $1"
    echo "$msg"
    echo "$msg" >&3
}

cleanup() {
    log "Script finished"
}

# Record why we stopped. SIGKILL still cannot be caught, but everything else says so.
on_signal() {
    log "ERROR: Received SIG$1 - aborting device monitoring"
    exit 128
}
trap 'on_signal TERM' TERM
trap 'on_signal INT' INT
trap 'on_signal HUP' HUP
trap cleanup EXIT

# fail_if_shared <path>...: refuse paths not owned by us or writable by group/other.
# Symlinks are skipped (their own mode is always 777); their targets are checked where they
# live inside the tree.
fail_if_shared() {
    local p bad
    for p in "$@"; do
        [ -e "$p" ] || continue
        bad="$(find "$p" ! -type l \( -perm /022 -o ! -uid "$(id -u)" \) -print -quit 2>/dev/null)"
        if [ -n "$bad" ]; then
            log "ERROR: $bad is group/world-writable or not owned by $(id -un); refusing to run."
            log "       Fix: chmod -R g-w,o-w '$p' (dirs 2750, files 640/750), owner $(id -un)"
            exit 1
        fi
    done
}

log "Starting daily device monitoring"
log "Work directory: $WORK_DIR"
log "Log file: $LOG_FILE"
log "Parameters: start_date=$START_DATE, end_date=$END_DATE, node_ids=$NODE_IDS, project=$PROJECT"
RETRY_BUDGET=$(( MAX_ATTEMPTS * ATTEMPT_TIMEOUT + (MAX_ATTEMPTS - 1) * RETRY_DELAY ))
log "Retry policy: up to $MAX_ATTEMPTS attempts, ${ATTEMPT_TIMEOUT}s limit each, ${RETRY_DELAY}s between (worst case ${RETRY_BUDGET}s)"

if [ -n "$SLURM_JOB_ID" ]; then
    log "Running as SLURM job $SLURM_JOB_ID"
    if command -v squeue &> /dev/null; then
        SLURM_TIMELIMIT="$(squeue -h -j "$SLURM_JOB_ID" -o %l 2>/dev/null || true)"
        log "SLURM time limit for this job: ${SLURM_TIMELIMIT:-unknown} (retry budget needs ${RETRY_BUDGET}s)"
    fi
fi

# This script and the directory holding it decide what runs: they must be ours alone.
[ -O "$SELF" ] || { log "ERROR: $SELF is not owned by $(id -un)"; exit 1; }
fail_if_shared "$SELF"
find "$(dirname "$SELF")" -maxdepth 0 -perm /022 | grep -q . \
    && { log "ERROR: $(dirname "$SELF") is group/world-writable; refusing to run"; exit 1; }

# One run at a time. The lock lives in Bryan's home so no one else can hold or replace it.
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

log "Loading required modules"
PYTHON_MODULE="${DEVICEMON_PYTHON_MODULE:-python3/3.12.4_anaconda2024.06-1_libmamba}"
if command -v module &> /dev/null; then
    if [ -z "${DEVICEMON_PYTHON:-}" ]; then
        module load "$PYTHON_MODULE" || log "Warning: Could not load module $PYTHON_MODULE"
    fi
    module load git || log "Warning: Could not load git module"
else
    log "Module command not found, assuming modules are already available"
fi

# The interpreter the venv is built from, by absolute path. A module may put python3, or only
# python, on PATH; take the first that is new enough. Anything older fails here, not 20 minutes
# into a pip run that builds sdists for an interpreter the code cannot run on.
py_ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; }
py_ver() { "$1" -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || echo "?"; }
PY=""
if [ -n "${DEVICEMON_PYTHON:-}" ]; then
    PY="$DEVICEMON_PYTHON"
    py_ok "$PY" || { log "ERROR: DEVICEMON_PYTHON=$PY is Python $(py_ver "$PY"); need >= 3.10"
                     exit 1; }
else
    for cand in python3 python; do
        c="$(command -v "$cand" 2>/dev/null)" || continue
        if py_ok "$c"; then PY="$c"; break; fi
        log "Skipping $c: Python $(py_ver "$c") (need >= 3.10)"
    done
    if [ -z "$PY" ]; then
        log "ERROR: no Python >= 3.10 on PATH after 'module load $PYTHON_MODULE'."
        log "       Check 'module avail python', then set DEVICEMON_PYTHON_MODULE (or"
        log "       DEVICEMON_PYTHON=/abs/path/python3) in the scrontab line."
        exit 1
    fi
fi
log "Python for the venv: $PY ($(py_ver "$PY"))"

# Credentials: the shared file (DEVICEMON_CREDS_FILE) as data; per-user files are a fallback
# for running from a personal account.
CREDS_LOADED=0
for f in "$CREDS_FILE" "$HOME/.rtgs_credentials" "$HOME/.rtgs_creds"; do
    [ -f "$f" ] || continue
    parse_creds "$f"; CREDS_LOADED=1
    log "Credentials from $f: accepted${CREDS_ACCEPTED:- nothing}"
    [ -z "$CREDS_REJECTED" ] || log "WARNING: ignored in $f:$CREDS_REJECTED"
    break
done
if [ "$CREDS_LOADED" -eq 0 ]; then
    log "ERROR: No credentials found: expected $CREDS_FILE (or ~/.rtgs_credentials, ~/.rtgs_creds)"
    exit 1
fi
if [ -z "${DEVICEMON_INGEST_URL:-}" ]; then
    log "ERROR: set DEVICEMON_INGEST_URL in $CREDS_FILE"
    exit 1
fi
log "Results go to the ingest service: $DEVICEMON_INGEST_URL"

# Release pin: "<tag> <commit sha>" in a file only Bryan can write.
[ -f "$RELEASE_FILE" ] && [ -O "$RELEASE_FILE" ] \
    || { log "ERROR: release pin $RELEASE_FILE missing or not owned by $(id -un)"; exit 1; }
find "$RELEASE_FILE" -maxdepth 0 -perm /022 | grep -q . \
    && { log "ERROR: $RELEASE_FILE is group/world-writable"; exit 1; }
read -r PIN_TAG PIN_SHA _ < "$RELEASE_FILE" || true
if ! [[ $PIN_TAG =~ ^devmon-v[0-9A-Za-z._-]+$ && $PIN_SHA =~ ^[0-9a-f]{40}$ ]]; then
    log "ERROR: $RELEASE_FILE must hold one line: <devmon-v* tag> <40-hex commit sha>"
    exit 1
fi

# Git never runs repository hooks, and never force-moves a tag it already has.
G() { git -c core.hooksPath=/dev/null -c protocol.file.allow=never "$@"; }

mkdir -p "$WORK_DIR"
fail_if_shared "$WORK_DIR"
if [ ! -d "$REPO_DIR/.git" ]; then
    if [ -e "$REPO_DIR" ]; then
        log "ERROR: $REPO_DIR exists but is not a git checkout; move it aside and re-run"
        exit 1
    fi
    log "Repository doesn't exist, cloning..."
    G clone --quiet --no-checkout https://github.com/RTGS-Lab/rtgs-lab-tools.git "$REPO_DIR"
fi
fail_if_shared "$REPO_DIR"
cd "$REPO_DIR"
log "Changed to repository: $(pwd)"

if ! G rev-parse -q --verify "refs/tags/$PIN_TAG" >/dev/null; then
    G fetch --quiet --no-tags origin "refs/tags/$PIN_TAG:refs/tags/$PIN_TAG" \
        || { log "ERROR: could not fetch tag $PIN_TAG"; exit 1; }
fi
TAG_SHA="$(G rev-parse "refs/tags/$PIN_TAG^{commit}")"
if [ "$TAG_SHA" != "$PIN_SHA" ]; then
    log "ERROR: tag $PIN_TAG is $TAG_SHA here but the pin says $PIN_SHA; refusing to run."
    log "       If the tag was legitimately re-cut, update $RELEASE_FILE (and delete the local tag)."
    exit 1
fi
if [ "$(G rev-parse HEAD 2>/dev/null)" != "$PIN_SHA" ]; then
    G checkout --quiet --detach "$PIN_SHA"
    log "Checked out release $PIN_TAG ($PIN_SHA)"
else
    log "Release $PIN_TAG ($PIN_SHA) already checked out"
fi
export DEVICEMON_RELEASE="$PIN_TAG"
fail_if_shared "$REPO_DIR"

# If the release carries a different version of this script, run that one instead (once).
NEW_SELF="$REPO_DIR/src/rtgs_lab_tools/device_monitoring/scheduled_device_monitoring.sh"
if [ -z "${DEVICEMON_REEXEC:-}" ] && [ -f "$NEW_SELF" ] \
        && [ "$(sha1sum < "$NEW_SELF")" != "$SELF_SHA" ]; then
    log "Script differs in $PIN_TAG; re-running that copy"
    exec 3>&- 9>&-
    exec env DEVICEMON_REEXEC=1 bash "$NEW_SELF" "$@"
fi

# The cron's venv holds only what the publisher needs (requirements-cron.txt), never the
# package's full base dependencies, install.sh, or the dev/all extras.
REQS="src/rtgs_lab_tools/device_monitoring/requirements-cron.txt"
VPY="$REPO_DIR/venv/bin/python"
if [ ! -f "$REQS" ]; then
    log "ERROR: $REQS is not in release $PIN_TAG; cannot build the venv"
    exit 1
fi
if [ ! -d "venv" ]; then
    log "Virtual environment not found, creating it with $PY"
    "$PY" -m venv venv >&3 2>&1
fi
if [ ! -x "$VPY" ]; then
    log "ERROR: Virtual environment not found after installation ($VPY missing)"
    exit 1
fi
if ! py_ok "$VPY"; then
    log "ERROR: venv/ runs Python $(py_ver "$VPY"); need >= 3.10. Move $REPO_DIR/venv aside"
    log "       and re-run: the venv is rebuilt with $PY."
    exit 1
fi
fail_if_shared "venv"

# A new release may bring new dependencies: refresh once per commit, still lean.
STAMP="venv/.devmon-installed-release"
if [ "$(cat "$STAMP" 2>/dev/null)" != "$PIN_TAG $PIN_SHA" ]; then
    log "Installing the device-monitoring requirements for release $PIN_TAG"
    "$VPY" -m pip install --quiet --disable-pip-version-check -r "$REQS" >&3 2>&1
    "$VPY" -m pip install --quiet --disable-pip-version-check --no-deps -e . >&3 2>&1
    echo "$PIN_TAG $PIN_SHA" > "$STAMP"
    fail_if_shared "venv"
fi

# Device monitoring's own CLI, not the `rtgs` router: a missing dependency shows up as a
# traceback naming the module instead of "No such command".
DEVMON=("$VPY" -m rtgs_lab_tools.device_monitoring.cli)

# Fail fast on setup problems (key file, IAM, URL) before the 80-second pipeline runs.
# Exit 2 = setup is wrong; 3 = transient, so carry on and let the attempts retry.
set +e
"${DEVMON[@]}" check-ingest >&3 2>&1
CHECK=$?
set -e
if [ "$CHECK" -eq 2 ]; then
    log "ERROR: ingest preflight failed (setup); see the check-ingest lines above in $LOG_FILE"
    exit 1
elif [ "$CHECK" -ne 0 ]; then
    log "WARNING: ingest preflight failed (exit $CHECK); continuing, publish retries later"
else
    log "Ingest preflight ok"
fi

MONITOR_ARGS=(monitor)
[ -z "$START_DATE" ] || MONITOR_ARGS+=("--start-date=$START_DATE")
[ -z "$END_DATE" ] || MONITOR_ARGS+=("--end-date=$END_DATE")
[ -z "$NODE_IDS" ] || MONITOR_ARGS+=("--node-ids=$NODE_IDS")
[ "$PROJECT" = "ALL" ] || MONITOR_ARGS+=("--project=$PROJECT")
if [ "${DEVICEMON_EMAIL:-0}" = "1" ]; then
    log "Notification email: on (DEVICEMON_EMAIL=1)"
else
    MONITOR_ARGS+=("--no-email")
    log "Notification email: off (set DEVICEMON_EMAIL=1 to send it)"
fi

# Pin one timestamp for the whole day and keep it across retries, so a retried
# report replaces the rows of the attempt it is repeating. UTC throughout.
export DEVICEMON_RUN_TIMESTAMP="$(date -u '+%Y-%m-%d %H:%M')"
log "Monitoring run timestamp: $DEVICEMON_RUN_TIMESTAMP UTC"

TIMEOUT_PREFIX=()
if command -v timeout &> /dev/null; then
    TIMEOUT_PREFIX=(timeout --kill-after=60 "$ATTEMPT_TIMEOUT")
else
    log "Warning: timeout not available, attempts will run unbounded"
fi

EXIT_CODE=1
ATTEMPT=1
while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
    log "Attempt $ATTEMPT/$MAX_ATTEMPTS - running: device_monitoring.cli ${MONITOR_ARGS[*]}"
    set +e
    "${TIMEOUT_PREFIX[@]}" "${DEVMON[@]}" "${MONITOR_ARGS[@]}" >&3 2>&1
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
log "Script completed with exit code $EXIT_CODE"
exit $EXIT_CODE
