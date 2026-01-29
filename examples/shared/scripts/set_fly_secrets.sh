#!/bin/bash
# YAMLGraph Fly.io Environment Variables Helper
# Automatically sets Fly.io environment variables from .env file
#
# Usage:
#   ./scripts/set_fly_secrets.sh [--dry-run] [env_file]
#   ./scripts/set_fly_secrets.sh --execute    # Actually set variables
#   ./scripts/set_fly_secrets.sh --dry-run    # Show what would be set (default)
#
# Examples:
#   ./scripts/set_fly_secrets.sh                    # Dry run with .env
#   ./scripts/set_fly_secrets.sh --execute         # Set variables from .env
#   ./scripts/set_fly_secrets.sh --execute .env.prod  # Set from custom file
#
# Features:
# - Includes all non-comment environment variables in key=value format
# - Automatically finds fly.toml (current dir or examples/booking/)
# - Runs fly commands from the correct directory

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default to dry run
DRY_RUN=true
ENV_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --execute)
            DRY_RUN=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            ENV_FILE="$1"
            shift
            ;;
    esac
done

# Default env file
ENV_FILE="${ENV_FILE:-.env}"

# Check if env file exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: Environment file '$ENV_FILE' not found${NC}"
    exit 1
fi

# Check if we're in a directory with fly.toml or need to find it
FLY_DIR=""
if [[ -f "fly.toml" ]]; then
    FLY_DIR="."
elif [[ -f "examples/booking/fly.toml" ]]; then
    FLY_DIR="examples/booking"
else
    echo -e "${RED}Error: Could not find fly.toml file${NC}"
    echo "Run this script from a directory with fly.toml or from the project root"
    exit 1
fi

echo -e "${BLUE}Found fly.toml in: $FLY_DIR${NC}"

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${BLUE}DRY RUN MODE - No secrets will be set${NC}"
    echo -e "${YELLOW}Use --execute to actually set the secrets${NC}"
else
    echo -e "${RED}EXECUTE MODE - Secrets will be set on Fly.io${NC}"
fi
echo -e "${BLUE}Reading secrets from: $ENV_FILE${NC}"
echo

# Read env file and extract all environment variables for Fly.io deployment
# Include all non-comment lines with = (key=value format)
secrets=$(grep -E '^[^#].*=.*' "$ENV_FILE" || true)

if [[ -z "$secrets" ]]; then
    echo -e "${RED}No environment variables found in $ENV_FILE${NC}"
    echo "Looking for lines in key=value format (not starting with #)"
    exit 1
fi

echo -e "${YELLOW}Found secrets to process:${NC}"
echo

# Process each secret
while IFS='=' read -r key value; do
    # Skip empty lines or comments
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue

    # Trim whitespace
    key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Skip if value is empty or placeholder
    [[ -z "$value" || "$value" =~ ^(set-via-secrets|your-.*|sk-.*\.\.\.)$ ]] && continue

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${GREEN}Would run: fly secrets set $key=\"[REDACTED]\"${NC}"
    else
        echo -e "${GREEN}Executing: fly secrets set $key=\"[REDACTED]\"${NC}"

        # Execute the command from the correct directory
        if (cd "$FLY_DIR" && fly secrets set "$key=$value"); then
            echo -e "${GREEN}✓ Set $key${NC}"
        else
            echo -e "${RED}✗ Failed to set $key${NC}"
        fi
    fi
    echo
done <<< "$secrets"

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${BLUE}Dry run complete! Use --execute to actually set secrets.${NC}"
else
    echo -e "${BLUE}Secret setting complete!${NC}"
fi
