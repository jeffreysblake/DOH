#!/usr/bin/env python3
"""
Test runner for DOH project
Run this to execute all tests
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Run all tests"""
    test_dir = Path(__file__).parent
    project_root = test_dir.parent

    print("🧪 Running DOH Test Suite")
    print("=" * 50)

    # Check if pytest is available
    try:
        import pytest  # noqa: F401  # Just checking if available
    except ImportError:
        print("❌ pytest not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], check=True)
        print("✅ pytest installed")

    # Add src to path for imports
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Run tests
    test_files = [
        test_dir / "test_doh.py",
        test_dir / "test_git_stats.py",
        test_dir / "test_cli.py",
    ]

    for test_file in test_files:
        if test_file.exists():
            print(f"\n📋 Running {test_file.name}...")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v"], cwd=project_root
            )

            if result.returncode != 0:
                print(f"❌ {test_file.name} failed")
                return result.returncode
            else:
                print(f"✅ {test_file.name} passed")

    print("\n🎉 All tests completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
