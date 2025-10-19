#!/usr/bin/env python3
"""
Script to fix SQL syntax errors in ajax_functions.php
Fixes:
1. Removes trailing commas before closing parenthesis in INSERT statements
2. Fixes variable name mismatches for $perqindje_kualiteti
"""

import re
import sys


def fix_sql_syntax(content: str) -> str:
    """Fix SQL syntax errors in PHP code."""

    # Fix 1: Remove trailing comma before closing parenthesis in INSERT statements
    # Pattern: },); -> });
    content = re.sub(r'},\s*\);', '});', content)

    # Fix 2: Fix variable name mismatches
    # Replace $perqindje_kualiteti with $perqindje_kualitet (except in the $_POST assignment)
    # We need to be careful not to replace the assignment itself

    # Pattern to find and replace variable usage (not assignment)
    def replace_var_usage(match):
        line = match.group(0)
        # Don't replace if it's an assignment from $_POST
        if '$_POST' in line and 'perqindje_kualitet' in line:
            # This is the assignment line, fix the variable name
            return line.replace('$perqindje_kualiteti =', '$perqindje_kualitet =')
        # Replace usage of the variable
        return line.replace('$perqindje_kualiteti', '$perqindje_kualitet')

    # Replace in the context of the function bodies
    content = re.sub(r'(\$perqindje_kualiteti\s*=)', r'$perqindje_kualitet =', content)

    return content


def main():
    """Main function to process the file."""
    input_file = 'ajax_functions.php'
    output_file = 'ajax_functions_fixed.php'

    try:
        # Read the original file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"Reading {input_file}...")
        print(f"Original file size: {len(content)} characters")

        # Apply fixes
        fixed_content = fix_sql_syntax(content)

        # Write the fixed file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        print(f"\nFixed file saved as {output_file}")
        print(f"Fixed file size: {len(fixed_content)} characters")

        # Show statistics
        original_lines = content.count('\n')
        fixed_lines = fixed_content.count('\n')
        print(f"\nLines: {original_lines} -> {fixed_lines}")

        # Count fixes
        trailing_comma_fixes = content.count('},);') - fixed_content.count('},);')
        print(f"\nFixes applied:")
        print(f"  - Trailing comma removals: {trailing_comma_fixes}")

        print("\n✓ File fixed successfully!")
        print(f"\nNext steps:")
        print(f"  1. Review {output_file}")
        print(f"  2. Test the fixed file")
        print(f"  3. Replace original with: mv {output_file} {input_file}")

    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
        print("Please make sure ajax_functions.php is in the current directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()





