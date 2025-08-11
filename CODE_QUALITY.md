# Code Quality Guidelines for DOH

## Overview
This project uses automated code quality tools to ensure consistent, maintainable code. All code must pass linting and formatting checks before being committed.

## Tools Used

### 1. Black (Code Formatter)
- **Purpose**: Automatically formats Python code to a consistent style
- **Config**: 88 character line length (in `.flake8`)
- **Usage**: 
  ```bash
  make format        # Auto-format all code
  make format-check  # Check if code is formatted
  ```

### 2. Flake8 (Linter)
- **Purpose**: Checks for code quality issues, style violations, and potential bugs
- **Config**: `.flake8` file in project root
- **Key rules**: 
  - Max line length: 88 characters
  - No unused imports or variables
  - Proper indentation and spacing
  - No bare `except` clauses (E722 - temporarily ignored)
- **Usage**:
  ```bash
  make lint  # Run linting on all files
  ```

### 3. Pytest (Testing)
- **Purpose**: Runs automated tests to ensure code functionality
- **Coverage**: Tracks which code is tested
- **Usage**:
  ```bash
  make test      # Run all tests
  make test-cov  # Run tests with coverage report
  ```

## Development Workflow

### Initial Setup
```bash
make dev-setup  # Install tools and setup git hooks
```

### Daily Development
1. **Before coding**: `make check` to ensure clean start
2. **While coding**: Run `make format` periodically 
3. **Before committing**: Automatic pre-commit hook runs checks
4. **If checks fail**: Run `make fix` to auto-fix issues

### Quick Commands
```bash
make help         # Show all available commands
make check        # Run all quality checks
make fix          # Auto-fix formatting + run checks  
make commit-check # Manually run pre-commit checks
```

## Rules for New Code

### ✅ Requirements for All Code Changes

1. **Formatting**: Must pass `black` formatting
   ```bash
   # This will auto-format your code:
   make format
   ```

2. **Linting**: Must pass `flake8` with no errors
   ```bash
   # Check your code:
   make lint
   ```

3. **Testing**: New/changed code must have tests
   - New functions/classes → New test functions
   - Changed behavior → Updated/new tests
   - Aim for high test coverage (>75%)

4. **Line Length**: Max 88 characters (enforced by tools)

5. **No Dead Code**: Remove unused imports and variables

### 🔄 Automated Checks

The project has a **pre-commit hook** that automatically runs when you commit:

```bash
# What happens on git commit:
git commit -m "Your message"
→ Automatic checks run
→ If checks fail: commit is rejected
→ Fix issues and try again
```

### 🛠️ Fixing Common Issues

**Problem**: "line too long (X > 88 characters)"
```python
# ❌ Too long
some_very_long_function_call_with_many_parameters(param1, param2, param3, param4)

# ✅ Fixed - split across lines
some_very_long_function_call_with_many_parameters(
    param1, param2, param3, param4
)
```

**Problem**: "unused import" 
```python
# ❌ Unused
import os
import sys  # Only sys is used
print(sys.version)

# ✅ Fixed
import sys
print(sys.version)
```

**Problem**: "unused variable"
```python
# ❌ Unused
def process_data():
    result = expensive_calculation()
    name = get_name()  # Never used
    return result

# ✅ Fixed  
def process_data():
    result = expensive_calculation()
    # name = get_name()  # Comment out or remove
    return result
```

### 📝 Testing Requirements

When you add/change code, you MUST add/update tests:

**New function** → **New test**:
```python
# src/doh/mymodule.py
def calculate_score(a, b):
    return a + b

# tests/test_mymodule.py  
def test_calculate_score():
    assert calculate_score(2, 3) == 5
    assert calculate_score(0, 0) == 0
```

**Changed behavior** → **Updated test**:
```python
# If you change how a function works,
# update its tests to match the new behavior
```

### 🚀 IDE Integration

**VS Code**: Install these extensions:
- Python
- Black Formatter  
- Flake8

**Settings** (add to `.vscode/settings.json`):
```json
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.linting.flake8Enabled": true,
    "python.linting.enabled": true,
    "editor.formatOnSave": true
}
```

## Bypassing Checks (Emergency Only)

If you need to bypass checks temporarily:

```bash
# Skip pre-commit hook (NOT RECOMMENDED)
git commit --no-verify -m "Emergency fix"

# Ignore specific flake8 errors (add to line end)
long_line = "this is really long"  # noqa: E501
```

⚠️ **Use sparingly** - bypassing checks should be rare and documented.

## Summary

The goal is **consistent, quality code** with **high test coverage**. The tools help automate this:

- **Black**: Makes code look consistent
- **Flake8**: Catches quality issues  
- **Pytest**: Ensures code works
- **Pre-commit**: Prevents bad code from being committed

When in doubt: `make check` → fix issues → `git commit` ✅
