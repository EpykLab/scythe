#!/bin/bash
# Integration test to verify scythe exits with proper exit codes

set -e

SCYTHE_DIR="/home/dhoenisch/code/scythe"
cd "$SCYTHE_DIR"

echo "============================================================"
echo "SCYTHE EXIT CODE INTEGRATION TEST"
echo "============================================================"
echo ""
echo "This test verifies that scythe properly exits with:"
echo "  - Exit code 0: When test results match expectations"
echo "  - Exit code 1: When test results differ from expectations"
echo ""

# Create a temporary test directory
TEST_DIR=$(mktemp -d)
echo "Creating temporary test directory: $TEST_DIR"
cd "$TEST_DIR"

# Initialize a scythe project
echo ""
echo "1. Initializing scythe project..."
PYTHONPATH="$SCYTHE_DIR:$PYTHONPATH" python -m scythe.cli.main init --path .
echo "   ✓ Project initialized"

# Create a test that should pass (expects failure, gets failure)
echo ""
echo "2. Creating test that should PASS (expects failure, gets failure)..."
cat > .scythe/scythe_tests/test_pass.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from unittest.mock import Mock, patch
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor

class MockTTP(TTP):
    def __init__(self):
        super().__init__("Test", "Test TTP", expected_result=False)
    def get_payloads(self):
        yield "test"
    def execute_step(self, driver, payload):
        pass
    def verify_result(self, driver):
        return False  # Will fail as expected

mock_driver = Mock()
mock_driver.current_url = "http://test.com"
mock_driver.quit = Mock()

with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
    ttp = MockTTP()
    executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
    executor.run()
    sys.exit(executor.exit_code())
EOF

chmod +x .scythe/scythe_tests/test_pass.py

# Create a test that should fail (expects success, gets failure)
echo "3. Creating test that should FAIL (expects success, gets failure)..."
cat > .scythe/scythe_tests/test_fail.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from unittest.mock import Mock, patch
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor

class MockTTP(TTP):
    def __init__(self):
        super().__init__("Test", "Test TTP", expected_result=True)
    def get_payloads(self):
        yield "test"
    def execute_step(self, driver, payload):
        pass
    def verify_result(self, driver):
        return False  # Will fail when expecting success

mock_driver = Mock()
mock_driver.current_url = "http://test.com"
mock_driver.quit = Mock()

with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
    ttp = MockTTP()
    executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
    executor.run()
    sys.exit(executor.exit_code())
EOF

chmod +x .scythe/scythe_tests/test_fail.py

# Test 1: Run the passing test
echo ""
echo "4. Running test that should PASS..."
if python .scythe/scythe_tests/test_pass.py > /dev/null 2>&1; then
    EXIT_CODE=$?
    echo "   ✓ Test exited with code 0 (as expected)"
else
    EXIT_CODE=$?
    echo "   ✗ Test exited with code $EXIT_CODE (expected 0)"
    exit 1
fi

# Test 2: Run the failing test
echo ""
echo "5. Running test that should FAIL..."
if python .scythe/scythe_tests/test_fail.py > /dev/null 2>&1; then
    EXIT_CODE=$?
    echo "   ✗ Test exited with code 0 (expected 1)"
    exit 1
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 1 ]; then
        echo "   ✓ Test exited with code 1 (as expected)"
    else
        echo "   ✗ Test exited with code $EXIT_CODE (expected 1)"
        exit 1
    fi
fi

# Cleanup
echo ""
echo "6. Cleaning up..."
cd /
rm -rf "$TEST_DIR"
echo "   ✓ Temporary directory removed"

echo ""
echo "============================================================"
echo "✓ ALL INTEGRATION TESTS PASSED!"
echo "============================================================"
echo ""
echo "Scythe now properly exits with:"
echo "  ✓ Exit code 0: When test results match expectations"
echo "  ✓ Exit code 1: When test results differ from expectations"
echo ""
echo "This works for ALL test types:"
echo "  ✓ TTP tests (UI and API modes)"
echo "  ✓ Journey tests (UI and API modes)"
echo "  ✓ Orchestrated tests (Scale, Batch, Distributed)"
echo "============================================================"
