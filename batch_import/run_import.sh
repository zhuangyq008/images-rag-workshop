#!/bin/bash

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$DIR/logs"

# Get current timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$DIR/logs/import_$TIMESTAMP.log"

# Run the Python script with nohup and redirect output
nohup python3 "$DIR/batch_import_to_opensearch.py" "$@" > "$LOG_FILE" 2>&1 &

# Get the PID of the background process
PID=$!

# Disown the process
disown $PID

echo "Import process started with PID: $PID"
echo "Log file: $LOG_FILE"
echo "You can monitor the progress with: tail -f $LOG_FILE"
