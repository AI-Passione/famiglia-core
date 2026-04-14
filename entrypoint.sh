#!/bin/bash
set -e

# Function to handle shutdown
cleanup() {
    echo "Shutting down..."
    kill $ENGINE_PID $API_PID
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🎩 Starting Agent Engine..."
python main.py &
ENGINE_PID=$!

echo "🛰️ Waiting for Engine to verify brain-models..."
until [ -f /tmp/famiglia_engine_ready ]
do
     sleep 1
done

echo "🛰️ Engine ready. Starting Command Center API..."
python src/famiglia_core/command_center/backend/main.py &
API_PID=$!


# Wait for any process to exit
wait -n

# Kill the other process if one dies
cleanup
