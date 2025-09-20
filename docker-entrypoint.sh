#!/bin/bash

# GTasks-Notion Integration Docker Entrypoint
# Runs the sync every 10 minutes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SYNC_INTERVAL=900  # 15 minutes in seconds
LOG_DIR="/app/logs"
LOG_FILE="$LOG_DIR/sync-$(date +%Y%m%d).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Function to check if it's night time (00:00 - 04:00)
is_night_time() {
    local hour=$(date +%H)
    # Convert to number to handle leading zeros
    hour=$((10#$hour))
    
    if [ $hour -ge 0 ] && [ $hour -lt 4 ]; then
        return 0  # It is night time
    else
        return 1  # It is not night time
    fi
}

# Function to run sync
run_sync() {
    local start_time=$(date +%s)
    
    # Check if it's night time
    if is_night_time; then
        log "INFO" "🌙 Skipping sync during night hours (00:00 - 04:00)"
        echo -e "${BLUE}🌙 Skipping sync during night hours (00:00 - 04:00)${NC}"
        return 0
    fi
    
    log "INFO" "🚀 Starting GTasks-Notion sync..."
    
    # Run the sync with error handling
    if python main.py 2>&1 | tee -a "$LOG_FILE"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "INFO" "✅ Sync completed successfully in ${duration}s"
        echo -e "${GREEN}✅ Sync completed successfully in ${duration}s${NC}"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "ERROR" "❌ Sync failed after ${duration}s"
        echo -e "${RED}❌ Sync failed after ${duration}s${NC}"
        return 1
    fi
}

# Function to cleanup old logs (keep last 7 days)
cleanup_logs() {
    find "$LOG_DIR" -name "sync-*.log" -type f -mtime +7 -delete 2>/dev/null || true
}

# Trap signals for graceful shutdown
trap 'log "INFO" "🛑 Received shutdown signal, exiting gracefully..."; exit 0' TERM INT

# Initial startup message
echo -e "${BLUE}🐳 GTasks-Notion Integration Docker Container Starting...${NC}"
log "INFO" "🐳 Container started with sync interval: ${SYNC_INTERVAL}s (15 minutes)"

# Verify Python environment
if ! python --version; then
    log "ERROR" "Python not found in container"
    exit 1
fi

# Verify main.py exists
if [ ! -f "main.py" ]; then
    log "ERROR" "main.py not found in container"
    exit 1
fi

# Verify required configuration files exist
if [ ! -f "config.yaml" ]; then
    log "ERROR" "config.yaml not found. Please mount it as a volume: ./config.yaml:/app/config.yaml:ro"
    exit 1
fi

if [ ! -f "client_secret.json" ]; then
    log "ERROR" "client_secret.json not found. Please mount it as a volume: ./client_secret.json:/app/client_secret.json:ro"
    exit 1
fi

# Check if config.yaml is valid
if ! python -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    log "ERROR" "config.yaml is not valid YAML format"
    exit 1
fi

# Run initial sync immediately
echo -e "${YELLOW}🔄 Running initial sync...${NC}"
run_sync

# Main sync loop
log "INFO" "📅 Starting periodic sync loop (every 15 minutes, paused 00:00-04:00)"
echo -e "${BLUE}📅 Sync will run every 15 minutes (paused 00:00-04:00). Press Ctrl+C to stop.${NC}"

while true; do
    # Wait for the specified interval
    log "INFO" "⏱️  Waiting ${SYNC_INTERVAL}s until next sync..."
    sleep "$SYNC_INTERVAL" &
    wait $!  # Wait for sleep, but allow signal interruption
    
    # Cleanup old logs before each sync
    cleanup_logs
    
    # Run the sync
    echo -e "${YELLOW}🔄 Running scheduled sync...${NC}"
    run_sync || log "WARN" "Sync failed but continuing..."
done