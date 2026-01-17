#!/bin/bash
# ============================================================================
# Code Analysis Pipeline
# ============================================================================
# Comprehensive analysis of the langgraph-showcase codebase
# Usage: ./scripts/analysis.sh [--install] [--full]
#
# Options:
#   --install   Install analysis tools first
#   --full      Run all analyses including slow ones (graphs, profiling)
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PACKAGE="showcase"
OUTPUT_DIR="docs/analysis"

# Parse arguments
INSTALL=false
FULL=false
for arg in "$@"; do
    case $arg in
        --install) INSTALL=true ;;
        --full) FULL=true ;;
    esac
done

# ============================================================================
# Helper Functions
# ============================================================================

header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

subheader() {
    echo ""
    echo -e "${YELLOW}── $1 ──${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

check_tool() {
    if command -v "$1" &> /dev/null || python -c "import $1" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Install Tools (if requested)
# ============================================================================

if [ "$INSTALL" = true ]; then
    header "Installing Analysis Tools"

    pip install --quiet radon vulture bandit mypy pipdeptree
    success "Installed: radon, vulture, bandit, mypy, pipdeptree"

    # Optional tools that may fail
    pip install --quiet pydeps 2>/dev/null && success "Installed: pydeps" || warning "pydeps requires graphviz"

    echo ""
fi

# ============================================================================
# Create Output Directory
# ============================================================================

mkdir -p "$OUTPUT_DIR"

# ============================================================================
# Phase 1: Basic Quality Gates
# ============================================================================

header "Phase 1: Basic Quality Gates"

subheader "Ruff Linting"
if ruff check . 2>&1; then
    success "All checks passed"
else
    error "Linting issues found"
fi

subheader "Test Suite"
TEST_OUTPUT=$(python -m pytest tests/ -q --tb=no 2>&1)
echo "$TEST_OUTPUT" | tail -5
if echo "$TEST_OUTPUT" | grep -q "passed"; then
    success "Tests passed"
else
    error "Test failures detected"
fi

subheader "Test Coverage"
python -m pytest tests/ -q --tb=no --cov="$PACKAGE" --cov-report=term-missing 2>&1 | tail -45

# ============================================================================
# Phase 2: Complexity Metrics
# ============================================================================

header "Phase 2: Complexity Metrics"

subheader "Module Sizes (lines of code)"
echo ""
echo "Top-level modules:"
wc -l "$PACKAGE"/*.py 2>/dev/null | sort -n | tail -15
echo ""
echo "All modules (largest first):"
find "$PACKAGE" -name "*.py" -exec wc -l {} \; 2>/dev/null | sort -rn | head -15

if check_tool radon; then
    subheader "Cyclomatic Complexity (radon cc)"
    echo ""
    echo "Functions with complexity > 5:"
    radon cc "$PACKAGE" -a -s --min C 2>/dev/null || echo "All functions have acceptable complexity"
    echo ""
    echo "Average complexity:"
    radon cc "$PACKAGE" -a -s 2>/dev/null | tail -1

    subheader "Maintainability Index (radon mi)"
    echo ""
    echo "Modules by maintainability (worst first):"
    radon mi "$PACKAGE" -s 2>/dev/null | sort -t'-' -k2 | head -15
else
    warning "radon not installed. Run with --install"
fi

# ============================================================================
# Phase 3: Security Analysis
# ============================================================================

header "Phase 3: Security Analysis"

if check_tool bandit; then
    subheader "Bandit Security Scan"
    BANDIT_OUTPUT=$(bandit -r "$PACKAGE" -ll -q 2>&1 || true)
    if [ -z "$BANDIT_OUTPUT" ] || echo "$BANDIT_OUTPUT" | grep -q "No issues"; then
        success "No medium+ severity issues found"
    else
        echo "$BANDIT_OUTPUT" | head -30
        BANDIT_ISSUES=$(echo "$BANDIT_OUTPUT" | grep -c "Issue:" || echo "0")
        warning "Found $BANDIT_ISSUES security issues"
    fi
else
    warning "bandit not installed. Run with --install"
fi

# ============================================================================
# Phase 4: Dead Code Detection
# ============================================================================

header "Phase 4: Dead Code Detection"

if check_tool vulture; then
    subheader "Vulture Dead Code Analysis"
    VULTURE_OUTPUT=$(vulture "$PACKAGE" --min-confidence 80 2>&1)
    if [ -z "$VULTURE_OUTPUT" ]; then
        success "No dead code detected (confidence >= 80%)"
    else
        echo "$VULTURE_OUTPUT" | head -20
        VULTURE_COUNT=$(echo "$VULTURE_OUTPUT" | wc -l)
        warning "Found $VULTURE_COUNT potential dead code items"
    fi
else
    warning "vulture not installed. Run with --install"
fi

# ============================================================================
# Phase 5: Type Checking
# ============================================================================

header "Phase 5: Type Checking"

if check_tool mypy; then
    subheader "MyPy Type Analysis"
    MYPY_OUTPUT=$(mypy "$PACKAGE" --ignore-missing-imports --no-error-summary 2>&1 || true)
    MYPY_ERRORS=$(echo "$MYPY_OUTPUT" | grep -c "error:" || echo "0")

    if [ "$MYPY_ERRORS" -eq 0 ]; then
        success "No type errors found"
    else
        echo "$MYPY_OUTPUT" | grep "error:" | head -15
        warning "Found $MYPY_ERRORS type errors"
    fi
else
    warning "mypy not installed. Run with --install"
fi

# ============================================================================
# Phase 6: Dependency Analysis
# ============================================================================

header "Phase 6: Dependency Analysis"

subheader "Internal Import Structure"
echo ""
echo "Cross-module imports in $PACKAGE:"
grep -rh "^from $PACKAGE" "$PACKAGE"/*.py 2>/dev/null | sort | uniq -c | sort -rn | head -15

if check_tool pipdeptree; then
    subheader "Package Dependencies"
    pipdeptree --packages langgraph-showcase 2>/dev/null || pipdeptree 2>/dev/null | head -30
fi

# ============================================================================
# Phase 7: Code Patterns
# ============================================================================

header "Phase 7: Code Patterns"

subheader "TODO/FIXME Markers"
TODO_COUNT=$(grep -rn "TODO\|FIXME\|HACK\|XXX" "$PACKAGE" --include="*.py" 2>/dev/null | wc -l || echo "0")
if [ "$TODO_COUNT" -gt 0 ]; then
    grep -rn "TODO\|FIXME\|HACK\|XXX" "$PACKAGE" --include="*.py" 2>/dev/null | head -10
    warning "Found $TODO_COUNT TODO/FIXME markers"
else
    success "No TODO/FIXME markers found"
fi

subheader "Exception Handling"
BARE_EXCEPT=$(grep -rn "except:" "$PACKAGE" --include="*.py" 2>/dev/null | grep -v "except:.*#" | wc -l || echo "0")
if [ "$BARE_EXCEPT" -gt 0 ]; then
    warning "Found $BARE_EXCEPT bare except clauses (anti-pattern)"
    grep -rn "except:" "$PACKAGE" --include="*.py" 2>/dev/null | grep -v "except:.*#" | head -5
else
    success "No bare except clauses"
fi

subheader "Docstring Coverage"
TOTAL_FUNCS=$(grep -rh "^def \|^    def " "$PACKAGE" --include="*.py" 2>/dev/null | wc -l)
DOCSTRINGS=$(grep -rh '"""' "$PACKAGE" --include="*.py" 2>/dev/null | wc -l)
# Rough estimate: docstrings come in pairs (open/close)
DOCSTRING_COUNT=$((DOCSTRINGS / 2))
echo "Functions/methods: $TOTAL_FUNCS"
echo "Docstrings (approx): $DOCSTRING_COUNT"

# ============================================================================
# Phase 8: Visualization (--full only)
# ============================================================================

if [ "$FULL" = true ]; then
    header "Phase 8: Visualization"

    if command -v pydeps &> /dev/null && command -v dot &> /dev/null; then
        subheader "Generating Dependency Graph"
        pydeps "$PACKAGE" --cluster --no-show -o "$OUTPUT_DIR/dependencies.svg" 2>/dev/null && \
            success "Created $OUTPUT_DIR/dependencies.svg" || \
            warning "Failed to generate dependency graph"
    else
        warning "pydeps or graphviz not available"
    fi

    if command -v pyreverse &> /dev/null; then
        subheader "Generating UML Diagrams"
        pyreverse -o png -p "$PACKAGE" "$PACKAGE" -d "$OUTPUT_DIR" 2>/dev/null && \
            success "Created UML diagrams in $OUTPUT_DIR/" || \
            warning "Failed to generate UML diagrams"
    fi
fi

# ============================================================================
# Summary Report
# ============================================================================

header "Analysis Summary"

echo ""
echo "Metrics:"
echo "  - Lines of code: $(find $PACKAGE -name '*.py' -exec cat {} \; | wc -l | tr -d ' ')"
echo "  - Python files: $(find $PACKAGE -name '*.py' | wc -l | tr -d ' ')"
echo "  - Test files: $(find tests -name 'test_*.py' | wc -l | tr -d ' ')"
echo ""

if [ "$FULL" = true ] && [ -d "$OUTPUT_DIR" ]; then
    echo "Generated files in $OUTPUT_DIR/:"
    ls -la "$OUTPUT_DIR/" 2>/dev/null | tail -10
fi

echo ""
echo -e "${GREEN}Analysis complete!${NC}"
echo ""
