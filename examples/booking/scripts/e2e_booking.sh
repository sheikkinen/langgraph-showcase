#!/bin/bash
# E2E Booking Assistant Test Script
# Tests the complete booking flow: API + Chat + Database
#
# Usage:
#   ./e2e_booking.sh                    # Local mode: starts server on port 8001
#   ./e2e_booking.sh https://example.com  # Remote mode: tests against URL

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
YAMLGRAPH_ROOT="$(dirname "$(dirname "$PROJECT_ROOT")")"

# Check if URL provided as argument
if [ -n "$1" ]; then
    BASE_URL="$1"
    REMOTE_MODE=true
    PORT=""
else
    PORT=8001
    BASE_URL="http://localhost:$PORT"
    REMOTE_MODE=false
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    if [ "$REMOTE_MODE" = true ]; then
        return
    fi
    log_info "Cleaning up..."
    pkill -f "uvicorn.*examples.booking.main" 2>/dev/null || true
    sleep 1
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Check if virtual environment is activated
check_venv() {
    if [[ "$VIRTUAL_ENV" != *yamlgraph* ]]; then
        log_error "Please activate the yamlgraph virtual environment first:"
        echo "  source .venv/bin/activate"
        exit 1
    fi
}

# Clean database for fresh test
clean_database() {
    log_info "Cleaning database for fresh test..."
    rm -f "$YAMLGRAPH_ROOT/booking.db"
    log_success "Database cleaned"
}

# Wait for server to be ready
wait_for_server() {
    local max_attempts=30
    local attempt=1

    log_info "Waiting for server to start on port $PORT..."
    while ! curl -s "$BASE_URL/health" > /dev/null 2>&1; do
        if [ $attempt -ge $max_attempts ]; then
            log_error "Server failed to start after $max_attempts attempts"
            exit 1
        fi
        sleep 1
        ((attempt++))
    done
    log_success "Server is ready!"
}

# Test health endpoint
test_health() {
    log_info "Testing health endpoint..."
    local response
    response=$(curl -s "$BASE_URL/health")
    echo "$response" | jq .

    if echo "$response" | jq -e '.status == "ok" and .graph_loaded == true' > /dev/null; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi
}

# Seed calendar data
seed_calendar() {
    log_info "Seeding calendar data..."
    chmod +x "$SCRIPT_DIR/seed_calendar.sh"
    "$SCRIPT_DIR/seed_calendar.sh" "$BASE_URL"
    log_success "Calendar seeded successfully"
}

# Show calendar status with slots and bookings
show_calendar_status() {
    local title="$1"
    log_info "$title"

    # Get all calendars
    calendars=$(curl -s "$BASE_URL/calendars")
    echo "$calendars" | jq .

    # Get all slots (across all calendars)
    calendar_ids=$(echo "$calendars" | jq -r '.[].id')
    for calendar_id in $calendar_ids; do
        log_info "Slots for calendar $calendar_id:"
        slots=$(curl -s "$BASE_URL/calendars/$calendar_id/slots")
        echo "$slots" | jq .
    done

    # Get all appointments
    appointments=$(curl -s "$BASE_URL/appointments")
    if [ "$(echo "$appointments" | jq '. | length')" -gt 0 ]; then
        log_info "All appointments:"
        echo "$appointments" | jq .
    else
        log_info "No appointments"
    fi
}

# Test REST API endpoints
test_api_endpoints() {
    log_info "Testing REST API endpoints..."

    # Get calendars
    log_info "Getting calendars..."
    calendars=$(curl -s "$BASE_URL/calendars")
    echo "$calendars" | jq .

    # Get first calendar ID
    calendar_id=$(echo "$calendars" | jq -r '.[0].id')
    if [ "$calendar_id" = "null" ] || [ -z "$calendar_id" ]; then
        log_error "No calendars found"
        exit 1
    fi

    # Get available slots
    log_info "Getting available slots for calendar $calendar_id..."
    slots=$(curl -s "$BASE_URL/calendars/$calendar_id/slots?available=true")
    echo "$slots" | jq .

    slot_count=$(echo "$slots" | jq '. | length')
    if [ "$slot_count" -gt 0 ]; then
        log_success "Found $slot_count available slots"
    else
        log_error "No available slots found - seeding may have failed"
        exit 1
    fi
}

# Test chat flow
test_chat_flow() {
    log_info "Testing chat conversation flow..."

    local thread_id="e2e_test_$(date +%s)"

    # Start chat
    log_info "Starting chat session..."
    start_response=$(curl -s -X POST "$BASE_URL/chat/$thread_id" \
        -H "Content-Type: application/json" \
        -d '{"message": "start"}')
    echo "$start_response" | jq .

    # Check if waiting for input
    status=$(echo "$start_response" | jq -r '.status')
    if [ "$status" != "waiting" ]; then
        log_error "Expected status 'waiting', got '$status'"
        exit 1
    fi

    question=$(echo "$start_response" | jq -r '.question')
    log_success "Chat started - waiting for: $question"

    # Resume with patient name
    log_info "Providing patient name..."
    resume_response=$(curl -s -X POST "$BASE_URL/chat/$thread_id/resume" \
        -H "Content-Type: application/json" \
        -d '{"answer": "John Doe"}')
    echo "$resume_response" | jq .

    # Check if waiting for slot selection
    status=$(echo "$resume_response" | jq -r '.status')
    if [ "$status" != "waiting" ]; then
        log_error "Expected status 'waiting' for slot selection, got '$status'"
        exit 1
    fi

    question=$(echo "$resume_response" | jq -r '.question')
    log_success "Patient name accepted - waiting for slot selection: $question"

    # Get available slots from state
    available_slots=$(echo "$resume_response" | jq -r '.state.available_slots')
    if [ "$available_slots" = "null" ] || [ "$available_slots" = "[]" ]; then
        log_error "No available slots found in chat state"
        exit 1
    fi

    # Select first available slot ID
    first_slot_id=$(echo "$available_slots" | jq -r '.[0].id')
    if [ "$first_slot_id" = "null" ] || [ -z "$first_slot_id" ]; then
        log_error "No slot ID found"
        exit 1
    fi

    log_info "Selecting slot: $first_slot_id"
    final_response=$(curl -s -X POST "$BASE_URL/chat/$thread_id/resume" \
        -H "Content-Type: application/json" \
        -d "{\"answer\": \"$first_slot_id\"}")
    echo "$final_response" | jq .

    status=$(echo "$final_response" | jq -r '.status')
    if [ "$status" = "complete" ]; then
        log_success "Booking completed successfully!"

        # Verify booking was created
        booking_id=$(echo "$final_response" | jq -r '.state.booking_id')
        if [ "$booking_id" != "null" ] && [ -n "$booking_id" ]; then
            log_info "Verifying booking creation..."
            booking_check=$(curl -s "$BASE_URL/appointments/$booking_id")
            if echo "$booking_check" | jq -e '.id' > /dev/null 2>&1; then
                log_success "Booking verified in database!"
            else
                log_error "Booking not found in database"
                exit 1
            fi
        else
            log_error "No booking ID in response"
            exit 1
        fi
    else
        log_error "Booking flow did not complete, status: $status"
        exit 1
    fi
}

# Run unit tests
run_tests() {
    log_info "Running unit tests..."
    cd "$YAMLGRAPH_ROOT"
    .venv/bin/python -m pytest examples/booking/tests/ --no-cov -q
    log_success "All tests passed!"
}

# Main execution
main() {
    log_info "Starting E2E Booking Assistant Test"
    log_info "=================================="
    log_info "Target: $BASE_URL"
    log_info "Mode: $([ "$REMOTE_MODE" = true ] && echo "REMOTE" || echo "LOCAL")"

    if [ "$REMOTE_MODE" = true ]; then
        # Remote mode: just run tests against existing server
        test_health
        seed_calendar
        show_calendar_status "Calendar status after seeding:"
        test_api_endpoints
        test_chat_flow
        show_calendar_status "Calendar status after booking:"
        log_success "E2E test completed successfully! 🎉"
    else
        # Local mode: start server, run tests, cleanup
        check_venv
        clean_database

        # Start server in background
        log_info "Starting server..."
        cd "$YAMLGRAPH_ROOT"
        .venv/bin/uvicorn examples.booking.main:app --reload --port $PORT &
        SERVER_PID=$!

        # Wait for server
        wait_for_server

        # Run tests
        test_health
        seed_calendar
        show_calendar_status "Calendar status after seeding:"
        test_api_endpoints
        test_chat_flow
        show_calendar_status "Calendar status after booking:"
        run_tests

        log_success "E2E test completed successfully! 🎉"

        # Server will be cleaned up by trap
    fi
}

# Allow script to be sourced for individual functions
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi