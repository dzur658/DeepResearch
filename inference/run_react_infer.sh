#!/bin/bash

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings:"
    echo "  cp .env.example .env"
    exit 1
fi

echo "Loading environment variables from .env file..."
set -a
source "$ENV_FILE"
set +a

# Validate NVIDIA API configuration
if [ -z "$NVIDIA_API_KEY" ] || [ "$NVIDIA_API_KEY" = "your_nvidia_api_key" ]; then
    echo "Error: NVIDIA_API_KEY not configured in .env file"
    exit 1
fi

if [ -z "$NVIDIA_BASE_URL" ]; then
    echo "Error: NVIDIA_BASE_URL not configured in .env file"
    exit 1
fi

if [ -z "$NVIDIA_MAIN_MODEL" ]; then
    echo "Error: NVIDIA_MAIN_MODEL not configured in .env file"
    exit 1
fi

echo "Using NVIDIA build.nvidia.com API backend"
echo "  Model: $NVIDIA_MAIN_MODEL"
echo "  Endpoint: $NVIDIA_BASE_URL"

cd "$( dirname -- "${BASH_SOURCE[0]}" )"

python -u run_multi_react.py \
    --dataset "$DATASET" \
    --output "$OUTPUT_PATH" \
    --max_workers $MAX_WORKERS \
    --model "$NVIDIA_MAIN_MODEL" \
    --temperature $TEMPERATURE \
    --presence_penalty $PRESENCE_PENALTY \
    --total_splits ${WORLD_SIZE:-1} \
    --worker_split $((${RANK:-0} + 1)) \
    --roll_out_count $ROLLOUT_COUNT
