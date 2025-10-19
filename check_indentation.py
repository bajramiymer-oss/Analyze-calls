#!/usr/bin/env python3
"""
Script për të kontrolluar indentacionin në file-at Python.
"""
import os
import sys
from pathlib import Path

def check_file_indentation(file_path: Path) -> bool:
    """Kontrollon nëse file-i ka indentacion të saktë."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Kontrollon për tab-e në vend të hapësirave
            if '\t' in line:
                print(f"❌ {file_path}:{i} - Ka tab-e në vend të hapësirave")
                return False

            # Kontrollon për indentacion të pabarabartë
            stripped = line.lstrip()
            if stripped and not line.startswith(' ' * (len(line) - len(stripped))):
                print(f"❌ {file_path}:{i} - Indentacion i pabarabartë")
                return False

        return True
    except Exception as e:
        print(f"❌ Gabim gjatë leximit të {file_path}: {e}")
        return False

def main():
    """Kontrollon të gjitha file-at Python në projekt."""
    project_root = Path.cwd()
    python_files = list(project_root.rglob("*.py"))

    # Përjashto file-at e venv dhe __pycache__
    python_files = [
        f for f in python_files
        if not any(part in str(f) for part in ['venv', '__pycache__', '.git'])
    ]

    print("🔍 Kontrolloj indentacionin...")

    all_good = True
    for file_path in python_files:
        if not check_file_indentation(file_path):
            all_good = False

    if all_good:
        print("✅ Të gjitha file-at kanë indentacion të saktë!")
        sys.exit(0)
    else:
        print("❌ Gjetën probleme me indentacionin!")
        sys.exit(1)

if __name__ == "__main__":
    main()
