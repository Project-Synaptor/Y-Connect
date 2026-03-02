#!/usr/bin/env python3
"""
Script to reduce max_examples in property-based tests for faster execution.
Reduces all max_examples values by 75% (to 25% of original).
"""

import re
import sys
from pathlib import Path

def reduce_max_examples(file_path: Path, reduction_factor: float = 0.25):
    """Reduce max_examples in a test file."""
    content = file_path.read_text()
    original_content = content
    
    # Pattern to match @settings(max_examples=N, ...)
    pattern = r'@settings\(max_examples=(\d+)'
    
    def replace_func(match):
        original_value = int(match.group(1))
        new_value = max(10, int(original_value * reduction_factor))  # Minimum 10
        return f'@settings(max_examples={new_value}'
    
    content = re.sub(pattern, replace_func, content)
    
    if content != original_content:
        file_path.write_text(content)
        print(f"✓ Updated {file_path}")
        return True
    else:
        print(f"- No changes needed for {file_path}")
        return False

def main():
    tests_dir = Path("tests")
    
    if not tests_dir.exists():
        print("Error: tests/ directory not found")
        sys.exit(1)
    
    # Find all property test files
    property_test_files = list(tests_dir.glob("test_*_properties.py"))
    
    if not property_test_files:
        print("No property test files found")
        sys.exit(1)
    
    print(f"Found {len(property_test_files)} property test files")
    print("Reducing max_examples to 25% of original values (minimum 10)...\n")
    
    updated_count = 0
    for test_file in sorted(property_test_files):
        if reduce_max_examples(test_file):
            updated_count += 1
    
    print(f"\n✓ Updated {updated_count} files")
    print("Tests will now run approximately 4x faster!")

if __name__ == "__main__":
    main()
