# DOH Test Suite

Comprehensive test suite for DOH (Directory Oh-no, Handle this!) - an auto-commit monitoring system for git repositories.

## Overview

This test suite covers all major functionality of DOH:
- Core functionality (DohCore, DohConfig)
- Git statistics and temp branch management (GitStats)
- CLI commands and user interface
- Configuration management
- Error handling and edge cases

## Test Files

### `test_doh.py`
Tests core DOH system functionality:
- Configuration initialization and management
- Directory monitoring and exclusion systems
- Git repository integration
- Parent directory exclusion logic
- Configuration backup system

### `test_git_stats.py`
Tests git statistics and enhanced features:
- Git repository detection
- File change statistics calculation
- Enhanced commit message generation
- Temporary branch creation and management
- Branch squashing functionality
- Untracked and staged file handling
- Binary file support

### `test_cli.py`
Tests CLI commands and user interface:
- All CLI commands (add, rm, config, status, run, etc.)
- Command aliases and shortcuts
- Error handling and user feedback
- Help system functionality
- Configuration commands

## Running Tests

### Prerequisites
```bash
pip install pytest
```

### Run All Tests
```bash
# From the tests directory
python run_tests.py

# Or using pytest directly
pytest -v

# Run specific test file
pytest test_doh.py -v
pytest test_git_stats.py -v
pytest test_cli.py -v
```

### Run Individual Test Classes
```bash
pytest test_doh.py::TestDohSystem -v
pytest test_git_stats.py::TestGitStats -v
pytest test_cli.py::TestDohCLI -v
```

## Test Coverage

The test suite covers:

### ✅ Core Functionality
- [x] Configuration management
- [x] Directory monitoring
- [x] Exclusion system
- [x] Git repository handling

### ✅ Enhanced Features  
- [x] Temporary branch strategy
- [x] Enhanced commit messages
- [x] Per-file statistics
- [x] Branch squashing

### ✅ CLI Commands
- [x] `doh add` - Add directory to monitoring
- [x] `doh rm` - Remove directory (renamed from remove)
- [x] `doh config` - Consolidated configuration (replaces configure)
- [x] `doh run` - Check and auto-commit (replaces daemon)
- [x] `doh ex` - Exclusion management (renamed from exclusions)
- [x] `doh status` - Enhanced status with temp branches
- [x] `doh squash` - Squash temp branches
- [x] `doh s` - Shorthand for squash
- [x] `doh cleanup` - Clean old temp branches

### ✅ Edge Cases
- [x] Binary file handling
- [x] Permission errors
- [x] Invalid git repositories
- [x] Missing directories
- [x] Empty repositories
- [x] Unicode/encoding issues

## Test Environment

Tests use isolated environments:
- Temporary directories for each test
- Isolated git repositories
- Separate DOH configuration
- No interference with user's actual DOH setup

## Contributing

When adding new features:
1. Add corresponding tests
2. Ensure all existing tests pass
3. Update this README if needed
4. Run the full test suite before committing

## Test Structure

```
tests/
├── __init__.py          # Test package initialization
├── run_tests.py         # Test runner script  
├── test_doh.py          # Core functionality tests
├── test_git_stats.py    # Git statistics tests
├── test_cli.py          # CLI command tests
└── README.md           # This file
```

## Continuous Integration

The test suite is designed to work in CI/CD environments:
- No external dependencies beyond pytest
- Isolated test environments
- Clear pass/fail indicators
- Verbose output for debugging

## Known Limitations

- Tests require git to be installed
- Some tests create temporary files/directories
- Network-dependent tests are avoided
- Tests assume POSIX-style paths (should work on Windows with proper setup)
