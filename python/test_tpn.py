# TPN Python Simulator Test Suite
# Run all TPN protocol tests

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tpn_simulator import run_all_tests

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
