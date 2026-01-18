#!/bin/bash
# Demo script - runs all YamlGraph demos
# Usage: ./demo.sh [demo_name]
#   demo_name: router | yamlgraph | reflexion | git | memory | map | storyboard | all (default)

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

run_demo() {
    local name=$1
    local graph=$2
    shift 2
    local vars=("$@")

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ Running: ${name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    python -m yamlgraph.cli graph run "$graph" "${vars[@]}"

    echo -e "${GREEN}✓ ${name} completed${NC}"
}

demo_router() {
    run_demo "Router Demo" "graphs/router-demo.yaml" \
        --var message="I absolutely love this product"
}

demo_yamlgraph() {
    run_demo "YamlGraph Demo Pipeline" "graphs/yamlgraph.yaml" \
        --var topic=AI --var style=casual
}

demo_reflexion() {
    run_demo "Reflexion Loop" "graphs/reflexion-demo.yaml" \
        --var topic=coffee
}

demo_git() {
    run_demo "Git Report Agent" "graphs/git-report.yaml" \
        --var input="What changed recently"
}

demo_memory() {
    run_demo "Memory Agent" "graphs/memory-demo.yaml" \
        --var input="Show recent commits"
}

demo_map() {
    run_demo "Map Fan-out" "graphs/map-demo.yaml" \
        --var topic=Space
}

demo_storyboard() {
    run_demo "Animated Storyboard" "examples/storyboard/animated-character-graph.yaml" \
        --var concept="A brave mouse knight"
}

demo_analysis() {
    run_demo "Code Analysis (Self-Analysis)" "graphs/code-analysis.yaml" \
        --var path="yamlgraph" --var package="yamlgraph"
}

print_usage() {
    echo -e "${YELLOW}YamlGraph Demos${NC}"
    echo ""
    echo "Usage: ./demo.sh [demo_name]"
    echo ""
    echo "Available demos:"
    echo "  router     - Tone-based routing (positive/negative/neutral)"
    echo "  yamlgraph  - Content generation pipeline (generate → analyze → summarize)"
    echo "  reflexion  - Self-refinement loop (draft → critique → refine)"
    echo "  git        - AI agent with git tools"
    echo "  memory     - Agent with conversation memory"
    echo "  map        - Parallel fan-out processing"
    echo "  storyboard - Animated character storyboard with image generation"
    echo "  analysis   - Self-analysis of yamlgraph codebase"
    echo "  all        - Run all demos (default)"
    echo ""
}

# Main
cd "$(dirname "$0")/.."

case "${1:-all}" in
    router)
        demo_router
        ;;
    yamlgraph)
        demo_yamlgraph
        ;;
    reflexion)
        demo_reflexion
        ;;
    git)
        demo_git
        ;;
    memory)
        demo_memory
        ;;
    map)
        demo_map
        ;;
    storyboard)
        demo_storyboard
        ;;
    analysis)
        demo_analysis
        ;;
    all)
        echo -e "${YELLOW}🚀 Running all YamlGraph demos...${NC}"
        demo_router
        demo_yamlgraph
        demo_reflexion
        demo_git
        demo_memory
        demo_map
        demo_storyboard
        demo_analysis
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✓ All demos completed successfully!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;
    -h|--help|help)
        print_usage
        ;;
    *)
        echo "Unknown demo: $1"
        print_usage
        exit 1
        ;;
esac
