#!/bin/bash

# Scheduled Device Monitoring Script for CRON
# Based on .github/workflows/daily-device-monitoring.yml
# 
# Usage: ./scheduled_device_monitoring.sh [start_date] [end_date] [node_ids] [project]
# All parameters are optional and will use defaults if not provided

set -e  # Exit on any error

# Parse command line arguments
START_DATE="${1:-}"
END_DATE="${2:-}"
NODE_IDS="${3:-}"
PROJECT="${4:-ALL}"

# Set up working directory and log file
WORK_DIR="$HOME/rtgs-lab-tools-cron"
LOG_DIR="$HOME/logs/device-monitoring-logs"
LOG_FILE="$LOG_DIR/device_monitoring_$(date +%Y%m%d_%H%M%S).log"

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

log "Starting daily device monitoring"
log "Work directory: $WORK_DIR"
log "Log directory: $LOG_DIR"
log "Parameters: start_date=$START_DATE, end_date=$END_DATE, node_ids=$NODE_IDS, project=$PROJECT"

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

# Activate virtual environment
log "Activating virtual environment"
source venv/bin/activate

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

log "Running command: $MONITOR_CMD"

# Run the device monitoring command
if $MONITOR_CMD >> "$LOG_FILE" 2>&1; then
    log "Device monitoring completed successfully"
    EXIT_CODE=0
else
    EXIT_CODE=$?
    log "ERROR: Device monitoring failed with exit code $EXIT_CODE"
fi

# Deactivate virtual environment
deactivate

log "Script completed with exit code $EXIT_CODE"

# Exit with the same code as the monitoring command
exit $EXIT_CODE