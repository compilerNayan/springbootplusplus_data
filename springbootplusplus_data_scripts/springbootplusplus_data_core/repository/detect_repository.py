#!/usr/bin/env python3
"""
Script to detect @Repository annotation and extract class information from C++ source files.

Detects patterns:
1. /// @Repository
   DefineStandardPointers(SomeClass)
   class SomeClass : public CpaRepository<Something, SomethingElse>

2. /// @Repository
   DefineStandardPointers(SomeClass)
   class SomeClass final : public CpaRepository<Something, SomethingElse>

3. DefineStandardPointers(SomeClass)
   /// @Repository
   class SomeClass final : public CpaRepository<Something, SomethingElse>

4. DefineStandardPointers(SomeClass)
   /// @Repository
   class SomeClass : public CpaRepository<Something, SomethingElse>

Returns: class_name, template_param1, template_param2
"""

import re
import sys
from typing import Optional, Tuple


def remove_comments(content: str) -> str:
    """Remove both // and /* */ style comments."""
    # Remove single-line comments
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    return content


def find_repository_annotation(content: str) -> bool:
    """Check if @Repository annotation is present (not processed)."""
    # Look for /// @Repository or ///@Repository annotation (ignoring whitespace)
    # Also check for already processed /* @Repository */ pattern
    # Pattern matches: /// followed by optional whitespace, then @Repository
    pattern = r'///\s*@Repository\b'
    
    # Check if annotation exists and is not already processed
    if re.search(pattern, content):
        # Check if it's already processed (/* @Repository */)
        processed_pattern = r'/\*\s*@Repository\s*\*/'
        if re.search(processed_pattern, content):
            # Already processed, don't treat as found
            return False
        return True
    
    return False


def extract_class_name_from_define_standard_pointers(content: str) -> Optional[str]:
    """Extract class name from DefineStandardPointers(ClassName)."""
    pattern = r'DefineStandardPointers\s*\(\s*(\w+)\s*\)'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None


def extract_cpaRepository_info(content: str, class_name: str) -> Optional[Tuple[str, str]]:
    """Extract template parameters from CpaRepository<Type1, Type2>."""
    # Pattern to match: class ClassName (optional final) : public (optional virtual) CpaRepository<Type1, Type2>
    # Handle both with and without 'final' keyword
    # Handle both with and without 'virtual' keyword
    pattern = rf'class\s+{re.escape(class_name)}\s+(?:final\s+)?:\s*public\s+(?:virtual\s+)?CpaRepository\s*<\s*([^,<>]+)\s*,\s*([^,<>]+)\s*>'
    
    match = re.search(pattern, content)
    if match:
        type1 = match.group(1).strip()
        type2 = match.group(2).strip()
        return (type1, type2)
    return None


def is_class_templated(content: str, class_name: str) -> bool:
    """Check if the repository class is templated."""
    # Remove comments for pattern matching
    content_no_comments = remove_comments(content)
    
    # Look for template<typename ...> before the class declaration
    # Pattern: template<typename Entity, typename ID> class ClassName
    pattern = rf'template\s*<\s*[^>]+\s*>\s*class\s+{re.escape(class_name)}'
    return bool(re.search(pattern, content_no_comments))


def detect_repository(file_path: str) -> Optional[Tuple[str, str, str, bool]]:
    """
    Detect @Repository annotation and extract class information.
    
    Returns: (class_name, template_param1, template_param2, is_templated) or None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        # print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return None
    
    # Check if @Repository annotation is present (not processed)
    annotation_found = find_repository_annotation(content)
    
    if not annotation_found:
        return None
    
    # Extract class name from DefineStandardPointers
    class_name = extract_class_name_from_define_standard_pointers(content)
    if not class_name:
        return None
    
    # Check if class is templated
    is_templated = is_class_templated(content, class_name)
    
    # Remove comments for class pattern matching (to avoid issues with commented code)
    content_no_comments = remove_comments(content)
    
    # Extract CpaRepository template parameters
    template_params = extract_cpaRepository_info(content_no_comments, class_name)
    if not template_params:
        return None
    
    type1, type2 = template_params
    return (class_name, type1, type2, is_templated)


def main():
    """Main function to run the script."""
    if len(sys.argv) < 2:
        # print("Usage: python detect_repository.py <source_file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    result = detect_repository(file_path)
    
    if result:
        if len(result) == 4:
            class_name, type1, type2, is_templated = result
            # print(f"Class: {class_name}")
            # print(f"Template Parameter 1: {type1}")
            # print(f"Template Parameter 2: {type2}")
            # print(f"Is Templated: {is_templated}")
        else:
            # Backward compatibility
            class_name, type1, type2 = result
            # print(f"Class: {class_name}")
            # print(f"Template Parameter 1: {type1}")
            # print(f"Template Parameter 2: {type2}")
        sys.exit(0)
    else:
        # print("No @Repository annotation found or pattern not matched.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

