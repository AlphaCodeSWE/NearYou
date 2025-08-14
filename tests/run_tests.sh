#!/bin/bash

# NearYou Test Runner Script
# This script runs different types of tests for the NearYou project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    if ! command_exists pip; then
        print_error "pip is required but not installed."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Install test dependencies
install_test_deps() {
    print_status "Installing test dependencies..."
    
    if [ -f "tests/requirements-test.txt" ]; then
        pip install -r tests/requirements-test.txt
        print_success "Test dependencies installed"
    else
        print_warning "tests/requirements-test.txt not found, installing basic pytest"
        pip install pytest pytest-asyncio pytest-cov pytest-mock
    fi
}

# Setup test environment
setup_test_env() {
    print_status "Setting up test environment..."
    
    # Create necessary directories
    mkdir -p tests/coverage
    mkdir -p tests/reports
    
    # Set environment variables for testing
    export ENVIRONMENT=test
    export LOG_LEVEL=DEBUG
    
    print_success "Test environment setup complete"
}

# Run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    
    pytest tests/unit/ \
        -m "unit" \
        --verbose \
        --cov=src \
        --cov=services \
        --cov-report=html:tests/coverage/unit \
        --cov-report=term-missing \
        --junit-xml=tests/reports/unit-test-results.xml \
        || {
            print_error "Unit tests failed"
            return 1
        }
    
    print_success "Unit tests completed successfully"
}

# Run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    pytest tests/integration/ \
        -m "integration" \
        --verbose \
        --cov=src \
        --cov=services \
        --cov-report=html:tests/coverage/integration \
        --cov-report=term-missing \
        --junit-xml=tests/reports/integration-test-results.xml \
        || {
            print_error "Integration tests failed"
            return 1
        }
    
    print_success "Integration tests completed successfully"
}

# Run acceptance tests
run_acceptance_tests() {
    print_status "Running acceptance tests..."
    
    pytest tests/acceptance/ \
        -m "acceptance" \
        --verbose \
        --junit-xml=tests/reports/acceptance-test-results.xml \
        || {
            print_error "Acceptance tests failed"
            return 1
        }
    
    print_success "Acceptance tests completed successfully"
}

# Run all tests
run_all_tests() {
    print_status "Running all tests..."
    
    pytest tests/ \
        --verbose \
        --cov=src \
        --cov=services \
        --cov-report=html:tests/coverage/all \
        --cov-report=term-missing \
        --cov-report=xml:tests/coverage/coverage.xml \
        --junit-xml=tests/reports/all-test-results.xml \
        || {
            print_error "Some tests failed"
            return 1
        }
    
    print_success "All tests completed successfully"
}

# Run specific test file or pattern
run_specific_tests() {
    local test_pattern="$1"
    print_status "Running tests matching pattern: $test_pattern"
    
    pytest "$test_pattern" \
        --verbose \
        --cov=src \
        --cov=services \
        --cov-report=term-missing \
        || {
            print_error "Tests failed for pattern: $test_pattern"
            return 1
        }
    
    print_success "Specific tests completed successfully"
}

# Generate test report
generate_report() {
    print_status "Generating test report..."
    
    if [ -f "tests/coverage/coverage.xml" ]; then
        print_success "Coverage report available at: tests/coverage/all/index.html"
    fi
    
    if [ -f "tests/reports/all-test-results.xml" ]; then
        print_success "JUnit test results available at: tests/reports/all-test-results.xml"
    fi
    
    # Count test results
    local unit_tests=$(find tests/unit -name "test_*.py" | wc -l)
    local integration_tests=$(find tests/integration -name "test_*.py" | wc -l)
    local acceptance_tests=$(find tests/acceptance -name "test_*.py" | wc -l)
    
    echo ""
    echo "📊 Test Suite Summary:"
    echo "   Unit Tests: $unit_tests files"
    echo "   Integration Tests: $integration_tests files" 
    echo "   Acceptance Tests: $acceptance_tests files"
    echo "   Total: $((unit_tests + integration_tests + acceptance_tests)) test files"
}

# Clean test artifacts
clean_test_artifacts() {
    print_status "Cleaning test artifacts..."
    
    rm -rf tests/coverage/
    rm -rf tests/reports/
    rm -rf .pytest_cache/
    rm -rf .coverage
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_success "Test artifacts cleaned"
}

# Show help
show_help() {
    echo "NearYou Test Runner"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup              Install dependencies and setup test environment"
    echo "  unit               Run unit tests only"
    echo "  integration        Run integration tests only"
    echo "  acceptance         Run acceptance tests only"
    echo "  all                Run all tests (default)"
    echo "  specific PATTERN   Run tests matching specific pattern"
    echo "  report             Generate test reports"
    echo "  clean              Clean test artifacts"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup                           # Setup test environment"
    echo "  $0 unit                            # Run only unit tests"
    echo "  $0 integration                     # Run only integration tests"
    echo "  $0 acceptance                      # Run only acceptance tests"
    echo "  $0 all                             # Run all tests"
    echo "  $0 specific tests/unit/test_models.py  # Run specific test file"
    echo "  $0 specific -k 'test_offer'        # Run tests matching pattern"
    echo ""
}

# Main script logic
main() {
    local command="${1:-all}"
    
    case "$command" in
        "setup")
            check_prerequisites
            install_test_deps
            setup_test_env
            ;;
        "unit")
            setup_test_env
            run_unit_tests
            ;;
        "integration")
            setup_test_env
            run_integration_tests
            ;;
        "acceptance")
            setup_test_env
            run_acceptance_tests
            ;;
        "all")
            setup_test_env
            run_all_tests
            generate_report
            ;;
        "specific")
            if [ -z "$2" ]; then
                print_error "Please provide a test pattern for specific tests"
                echo "Example: $0 specific tests/unit/test_models.py"
                exit 1
            fi
            setup_test_env
            run_specific_tests "$2"
            ;;
        "report")
            generate_report
            ;;
        "clean")
            clean_test_artifacts
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
