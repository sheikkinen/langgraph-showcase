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

    .venv/bin/python -m yamlgraph.cli graph run "$graph" "${vars[@]}"

    echo -e "${GREEN}✓ ${name} completed${NC}"
}

demo_hello() {
    run_demo "Hello World" "graphs/hello.yaml" \
        --var name="World" --var style="enthusiastic"
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

demo_interview() {
    echo -e "${YELLOW}Note: Interview demo requires interactive input${NC}"
    echo -e "${YELLOW}Running via dedicated script...${NC}"
    .venv/bin/python scripts/run_interview_demo.py
}

demo_brainstorm() {
    run_demo "Feature Brainstorm" "graphs/feature-brainstorm.yaml"
}

demo_webresearch() {
    run_demo "Web Research Agent" "graphs/web-research.yaml" \
        --var topic="Latest developments in AI agents"
}

demo_codegen() {
    run_demo "Impl-Agent (Code Analysis)" "examples/codegen/impl-agent.yaml" \
        --var story="Add a timeout parameter to websearch" \
        --var scope="yamlgraph/tools"
}

demo_subgraph() {
    run_demo "Subgraph Composition" "graphs/subgraph-demo.yaml" \
        --var raw_text="LangGraph is a library for building stateful, multi-actor applications with LLMs. It allows developers to create complex AI workflows using a graph-based approach."
}

demo_costrouter() {
    echo -e "${YELLOW}Cost Router - Routes queries to cost-appropriate models${NC}"
    echo -e "${YELLOW}Using: Replicate/Granite (simple), Mistral (medium), Anthropic (complex)${NC}"
    run_demo "Cost Router (Simple Query)" "examples/cost-router/cost-router.yaml" \
        --var query="What is the capital of France?"
    run_demo "Cost Router (Medium Query)" "examples/cost-router/cost-router.yaml" \
        --var query="Summarize the key benefits of cloud computing"
    run_demo "Cost Router (Complex Query)" "examples/cost-router/cost-router.yaml" \
        --var query="Analyze the ethical implications of AI in healthcare"
}

print_usage() {
    echo -e "${YELLOW}YamlGraph Demos${NC}"
    echo ""
    echo "Usage: ./demo.sh [demo_name]"
    echo ""
    echo "Available demos:"
    echo "  hello       - Hello World (minimal example)"
    echo "  router      - Tone-based routing (positive/negative/neutral)"
    echo "  yamlgraph   - Content generation pipeline (generate → analyze → summarize)"
    echo "  reflexion   - Self-refinement loop (draft → critique → refine)"
    echo "  git         - AI agent with git tools"
    echo "  memory      - Agent with conversation memory"
    echo "  map         - Parallel fan-out processing"
    echo "  storyboard  - Animated character storyboard with image generation"
    echo "  analysis    - Self-analysis of yamlgraph codebase"
    echo "  interview   - Human-in-the-loop interrupt demo"
    echo "  brainstorm  - Feature brainstorm (YAMLGraph analyzes itself)"
    echo "  webresearch - Web research agent"
    echo "  codegen     - Impl-agent code analysis (from examples/codegen)"
    echo "  subgraph    - Subgraph composition demo"
    echo "  costrouter  - Cost-based routing (Replicate/Mistral/Anthropic)"
    echo "  all         - Run all demos (default)"
    echo ""
}

# Main
cd "$(dirname "$0")/.."

# Lint all graphs first
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}▶ Linting all graphs...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
.venv/bin/python -m yamlgraph.cli graph lint graphs/*.yaml
echo -e "${GREEN}✓ All graphs passed linting${NC}"
echo ""

case "${1:-all}" in
    hello)
        demo_hello
        ;;
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
    interview)
        demo_interview
        ;;
    brainstorm)
        demo_brainstorm
        ;;
    webresearch)
        demo_webresearch
        ;;
    codegen)
        demo_codegen
        ;;
    subgraph)
        demo_subgraph
        ;;
    costrouter)
        demo_costrouter
        ;;
    all)
        echo -e "${YELLOW}🚀 Running all YamlGraph demos...${NC}"
        demo_hello
        demo_router
        demo_yamlgraph
        demo_reflexion
        demo_git
        demo_memory
        demo_map
        demo_storyboard
        demo_analysis
        demo_brainstorm
        demo_webresearch
        demo_costrouter
        # Skip interview (requires interaction) and codegen (slow)
        echo ""
        echo -e "${YELLOW}Note: Skipped 'interview' (interactive) and 'codegen' (slow)${NC}"
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
