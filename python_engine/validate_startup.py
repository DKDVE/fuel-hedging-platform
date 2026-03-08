#!/usr/bin/env python3
"""
Startup validation script for Fuel Hedging Platform.
Checks all critical components before application starts.
"""
import sys
from pathlib import Path

def check_structure():
    """Verify directory structure."""
    required_dirs = [
        "app",
        "app/routers",
        "app/services",
        "app/schemas",
        "app/db",
        "app/repositories",
        "app/analytics",
    ]
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            print(f"❌ Missing directory: {dir_path}")
            return False
    print("✅ Directory structure OK")
    return True

def check_files():
    """Verify critical files exist."""
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "app/auth.py",
        "app/dependencies.py",
        "app/exceptions.py",
        "app/db/models.py",
        "app/db/base.py",
        "requirements.txt",
        ".dockerignore",
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Missing file: {file_path}")
            return False
    print("✅ Required files OK")
    return True

def check_no_conflicts():
    """Check for conflicting files/directories."""
    conflicts = [
        ("app/auth.py", "app/auth/"),  # Can't have both
    ]
    
    for file_path, dir_path in conflicts:
        if Path(file_path).exists() and Path(dir_path).exists():
            print(f"❌ Conflict: Both {file_path} and {dir_path} exist")
            return False
    print("✅ No conflicts found")
    return True

def check_imports():
    """Basic import check."""
    try:
        import app.config
        import app.exceptions
        print("✅ Core modules importable")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("Fuel Hedging Platform - Startup Validation")
    print("=" * 60)
    print()
    
    checks = [
        ("Directory Structure", check_structure),
        ("Required Files", check_files),
        ("No Conflicts", check_no_conflicts),
        ("Basic Imports", check_imports),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"Checking {name}...")
        if not check_func():
            all_passed = False
        print()
    
    print("=" * 60)
    if all_passed:
        print("✅ All validation checks passed!")
        print("=" * 60)
        print()
        print("Ready to start:")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print()
        return 0
    else:
        print("❌ Some validation checks failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
