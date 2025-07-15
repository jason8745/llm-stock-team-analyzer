#!/bin/bash

# LLM Stock Team Analyzer - Docker Build Script with Quality Checks

set -e  # Exit on any error

# Default values
IMAGE_NAME="llm-stock-analyzer"
TAG="latest"
DOCKERFILE="Dockerfile"
SKIP_CHECKS=false

# Show usage
show_usage() {
    echo "Usage: $0 [TAG] [--secure] [--skip-checks]"
    echo ""
    echo "  TAG           Set image tag (default: latest)"
    echo "  --secure      Use secure distroless build"
    echo "  --skip-checks Skip format, lint, and test checks"
    echo ""
    echo "Examples:"
    echo "  $0                    # Build with full quality checks"
    echo "  $0 v1.0.0             # Build v1.0.0 with checks"
    echo "  $0 --secure           # Build secure version with checks"
    echo "  $0 --skip-checks      # Build without quality checks (faster)"
    echo "  $0 v1.0.0 --secure    # Build v1.0.0 secure with checks"
}

# Quality check functions

run_quality_checks() {
    echo "🔧 Running import sort and formatting..."
    if command -v uv &> /dev/null; then
        uv run ruff check --select I --fix .
        if [ $? -ne 0 ]; then
            echo "❌ Import sort failed."
            return 1
        fi
        uv run ruff format -v .
        if [ $? -ne 0 ]; then
            echo "❌ Format failed."
            return 1
        fi
    else
        echo "⚠️  uv not found, skipping quality checks"
    fi
    echo "✅ Quality checks passed"
}

# Parse arguments
for arg in "$@"; do
    case $arg in
        --secure)
            DOCKERFILE="Dockerfile.distroless"
            echo "Using secure distroless build"
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            echo "Skipping quality checks"
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            if [[ ! "$arg" == --* ]]; then
                TAG="$arg"
            fi
            ;;
    esac
done

# Check if Dockerfile exists
if [[ ! -f "$DOCKERFILE" ]]; then
    echo "❌ Error: $DOCKERFILE not found"
    exit 1
fi

# Run quality checks unless skipped
if [ "$SKIP_CHECKS" = false ]; then
    echo "🚀 Starting quality checks before build..."
    
    # Check if we're in a Python project
    if [[ ! -f "pyproject.toml" ]]; then
        echo "⚠️  pyproject.toml not found. Skipping quality checks."
    else
        run_quality_checks || exit 1
        echo "✅ All quality checks passed!"
    fi
else
    echo "⏭️  Skipping quality checks as requested"
fi

# Build image
echo "🐳 Building Docker image: ${IMAGE_NAME}:${TAG} using ${DOCKERFILE}..."
docker build -f "$DOCKERFILE" -t "${IMAGE_NAME}:${TAG}" .

if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
    echo "📊 Image details:"
    docker images "${IMAGE_NAME}:${TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""
    echo "🚀 Run with: docker run -it ${IMAGE_NAME}:${TAG}"
    echo "🚀 Or use: ./run.sh --config ./my-config.yaml"
else
    echo "❌ Docker build failed!"
    exit 1
fi
