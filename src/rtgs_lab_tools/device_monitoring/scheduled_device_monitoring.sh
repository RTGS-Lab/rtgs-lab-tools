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
LOG_FILE="$WORK_DIR/device_monitoring_$(date +%Y%m%d_%H%M%S).log"

# Create work directory if it doesn't exist
mkdir -p "$WORK_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to cleanup on exit
cleanup() {
    log "Cleaning up temporary installation"
    if [ -d "$WORK_DIR/rtgs-lab-tools" ]; then
        rm -rf "$WORK_DIR/rtgs-lab-tools"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

log "Starting daily device monitoring"
log "Work directory: $WORK_DIR"
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

# Clone the repository
log "Cloning rtgs-lab-tools repository"
if [ -d "rtgs-lab-tools" ]; then
    log "Repository already exists, updating..."
    cd rtgs-lab-tools
    git pull
else
    git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
    cd rtgs-lab-tools
fi

# Run installation
log "Running installation"
bash install.sh

# Check if virtual environment was created
if [ ! -d "venv" ]; then
    log "ERROR: Virtual environment not found after installation"
    exit 1
fi

# Activate virtual environment
log "Activating virtual environment"
source venv/bin/activate

# Source RTGS credentials
source /users/4/graff253/.rtgs_creds

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