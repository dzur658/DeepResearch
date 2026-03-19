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

# Validate Brev API configuration
if [ -z "$BREV_API_KEY" ] || [ "$BREV_API_KEY" = "your_brev_api_key" ]; then
    echo "Error: BREV_API_KEY not configured in .env file"
    exit 1
fi

if [ -z "$BREV_MAIN_BASE_URL" ] || echo "$BREV_MAIN_BASE_URL" | grep -q 'your_main_deployment_id'; then
    echo "Error: BREV_MAIN_BASE_URL not configured in .env file"
    exit 1
fi

if [ -z "$BREV_MAIN_MODEL_NAME" ]; then
    echo "Error: BREV_MAIN_MODEL_NAME not configured in .env file"
    exit 1
fi

echo "Using Nvidia Brev API backend"
echo "  Model: $BREV_MAIN_MODEL_NAME"
echo "  Endpoint: $BREV_MAIN_BASE_URL"

cd "$( dirname -- "${BASH_SOURCE[0]}" )"

python -u run_multi_react.py \
    --dataset "$DATASET" \
    --output "$OUTPUT_PATH" \
    --max_workers $MAX_WORKERS \
    --model "$BREV_MAIN_MODEL_NAME" \
    --temperature $TEMPERATURE \
    --presence_penalty $PRESENCE_PENALTY \
    --total_splits ${WORLD_SIZE:-1} \
    --worker_split $((${RANK:-0} + 1)) \
    --roll_out_count $ROLLOUT_COUNT
