#!/bin/bash

# LLM Stock Team Analyzer - Docker Run Script
# Simple script to run the Docker container with common configurations

set -e

# Default values
IMAGE_NAME="llm-stock-analyzer"
TAG="latest"
CONTAINER_NAME="stock-analyzer-$(date +%Y%m%d-%H%M%S)"

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --config PATH     Mount custom config file"
    echo "  --data PATH       Mount data directory"
    echo "  --name NAME       Set container name"
    echo "  --interactive     Run in interactive mode (default)"
    echo "  --detach         Run in background"
    echo "  -h, --help       Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Basic run"
    echo "  $0 --config ./custom-config.yaml    # With custom config"
    echo "  $0 --data ./output                  # With data directory"
}

# Parse arguments
INTERACTIVE=true
CONFIG_PATH=""
DATA_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --data)
            DATA_PATH="$2"
            shift 2
            ;;
        --name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --detach)
            INTERACTIVE=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Build docker run command
DOCKER_CMD="docker run --rm"

if [ "$INTERACTIVE" = true ]; then
    DOCKER_CMD="$DOCKER_CMD -it"
else
    DOCKER_CMD="$DOCKER_CMD -d"
fi

DOCKER_CMD="$DOCKER_CMD --name $CONTAINER_NAME"

# Add volume mounts if specified
if [ -n "$CONFIG_PATH" ]; then
    if [ ! -f "$CONFIG_PATH" ]; then
        echo "Error: Config file not found: $CONFIG_PATH"
        exit 1
    fi
    DOCKER_CMD="$DOCKER_CMD -v $(realpath $CONFIG_PATH):/app/llm_stock_team_analyzer/configs/config.yaml"
fi

if [ -n "$DATA_PATH" ]; then
    mkdir -p "$DATA_PATH"
    DOCKER_CMD="$DOCKER_CMD -v $(realpath $DATA_PATH):/app/data"
fi

DOCKER_CMD="$DOCKER_CMD ${IMAGE_NAME}:${TAG}"

# Run the container
echo "Running: $DOCKER_CMD"
echo "Container name: $CONTAINER_NAME"
echo ""

exec $DOCKER_CMD
