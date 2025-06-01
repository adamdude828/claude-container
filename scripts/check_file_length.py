#!/usr/bin/env python3
"""Check Python files for maximum line count."""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


def check_file_length(file_path: Path, max_lines: int) -> Tuple[bool, int]:
    """Check if a file exceeds the maximum line count.
    
    Returns:
        Tuple of (is_valid, line_count)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)
            return line_count <= max_lines, line_count
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return False, 0


def find_python_files(directory: Path, exclude_patterns: List[str]) -> List[Path]:
    """Find all Python files in directory, excluding certain patterns."""
    python_files = []
    
    for file_path in directory.rglob("*.py"):
        # Skip excluded directories
        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue
        python_files.append(file_path)
    
    return python_files


def main():
    parser = argparse.ArgumentParser(description="Check Python files for maximum line count")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=400,
        help="Maximum allowed lines per file (default: 400)"
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=["__pycache__", ".venv", "venv", "dist", "build", ".git"],
        help="Patterns to exclude from checking"
    )
    parser.add_argument(
        "path",
        type=Path,
        default=Path.cwd(),
        nargs="?",
        help="Path to check (default: current directory)"
    )
    
    args = parser.parse_args()
    
    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)
    
    violations = []
    
    if args.path.is_file() and args.path.suffix == ".py":
        # Check single file
        is_valid, line_count = check_file_length(args.path, args.max_lines)
        if not is_valid:
            violations.append((args.path, line_count))
    else:
        # Check directory
        python_files = find_python_files(args.path, args.exclude)
        
        for file_path in python_files:
            is_valid, line_count = check_file_length(file_path, args.max_lines)
            if not is_valid:
                violations.append((file_path, line_count))
    
    if violations:
        print(f"\n❌ Found {len(violations)} file(s) exceeding {args.max_lines} lines:\n")
        for file_path, line_count in sorted(violations, key=lambda x: x[1], reverse=True):
            print(f"  {file_path}: {line_count} lines")
        print()
        sys.exit(1)
    else:
        print(f"✅ All Python files are within the {args.max_lines} line limit")
        sys.exit(0)


if __name__ == "__main__":
    main()