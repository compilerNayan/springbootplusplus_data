#!/usr/bin/env python3
"""
Script to extract all method names from a repository class.

This script reads a repository file and extracts all method declarations,
returning a list of method names.

Usage:
    python extract_repository_methods.py <repository_file_path>
    
Returns:
    List of method names found in the repository
"""

import re
import sys
from typing import List, Optional


def remove_comments(content: str) -> str:
    """Remove both // and /* */ style comments."""
    # Remove single-line comments
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    return content


def extract_class_content(content: str, class_name: str) -> Optional[str]:
    """
    Extract the content of a class definition.
    
    Args:
        content: File content as string
        class_name: Name of the class to extract
        
    Returns:
        Class body content or None if class not found
    """
    # Remove comments for pattern matching
    content_no_comments = remove_comments(content)
    
    # Pattern to match class declaration and extract its body
    # Handles: class ClassName : public CpaRepository<...> { ... };
    pattern = rf'class\s+{re.escape(class_name)}\s+(?:final\s+)?:\s*public\s+(?:virtual\s+)?CpaRepository\s*<\s*[^>]+\s*>\s*{{(.*?)}};'
    
    match = re.search(pattern, content_no_comments, re.DOTALL)
    if match:
        return match.group(1)
    
    # Also try without inheritance (in case it's a different pattern)
    pattern2 = rf'class\s+{re.escape(class_name)}\s*(?:final\s+)?{{(.*?)}};'
    match2 = re.search(pattern2, content_no_comments, re.DOTALL)
    if match2:
        return match2.group(1)
    
    return None


def extract_method_names(class_content: str) -> List[str]:
    """
    Extract method names from class content.
    
    Args:
        class_content: The body of a class definition
        
    Returns:
        List of method names found
    """
    method_names = []
    
    # Pattern to match method declarations with Public/Private/Protected
    # Matches: Public Virtual ReturnType MethodName(parameters) override;
    # Matches: Public ReturnType MethodName(parameters);
    # Matches: Public Static ReturnType MethodName(parameters);
    
    # Pattern breakdown:
    # (?:Public|Private|Protected)\s+           - Access modifier
    # (?:Virtual\s+|Static\s+)?                - Optional Virtual or Static
    # (?:const\s+)?                             - Optional const
    # ([A-Za-z_][A-Za-z0-9_<>:&*,\s]*)         - Return type (complex, can include templates)
    # \s+                                       - Whitespace
    # ([A-Za-z_][A-Za-z0-9_]*)                 - Method name
    # \s*\(                                     - Opening parenthesis
    # [^)]*                                     - Parameters (anything except closing paren)
    # \)                                        - Closing parenthesis
    # (?:\s+const)?                             - Optional const at end
    # (?:\s+override)?                         - Optional override
    # (?:\s*=\s*0)?                            - Optional = 0 for pure virtual
    # \s*;                                      - Semicolon
    
    # Primary pattern for methods with access modifiers
    pattern = r'(?:Public|Private|Protected)\s+(?:Virtual\s+|Static\s+)?(?:const\s+)?([A-Za-z_][A-Za-z0-9_<>:&*,\s]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?:\s+const)?(?:\s+override)?(?:\s*=\s*0)?\s*;'
    
    matches = re.finditer(pattern, class_content)
    for match in matches:
        method_name = match.group(2).strip()
        # Filter out keywords, destructors, and invalid names
        if (method_name and 
            method_name not in ['Public', 'Private', 'Protected', 'Virtual', 'Static', 'const', 'override'] and
            not method_name.startswith('~') and  # Exclude destructors
            method_name not in method_names):
            method_names.append(method_name)
    
    # Also try a simpler pattern for methods without explicit access modifiers
    # This handles cases where methods might be declared differently
    # Match: ReturnType MethodName(...);
    # But be careful not to match variable declarations
    simple_pattern = r'\b([A-Za-z_][A-Za-z0-9_<>:&*,\s]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?:\s+const)?(?:\s+override)?(?:\s*=\s*0)?\s*;'
    simple_matches = re.finditer(simple_pattern, class_content)
    for match in simple_matches:
        return_type = match.group(1).strip()
        method_name = match.group(2).strip()
        
        # Filter out common keywords and invalid method names
        invalid_names = ['Public', 'Private', 'Protected', 'Virtual', 'Static', 'const', 'override', 'if', 'for', 'while', 'return']
        
        # Check if it looks like a valid method (return type should not be a single keyword)
        if (method_name and 
            method_name not in invalid_names and
            method_name not in method_names and
            len(return_type.split()) > 0):  # Return type should have some content
            # Additional check: make sure it's not a variable declaration
            # Variables typically don't have 'override' or '= 0'
            if 'override' in match.group(0) or '= 0' in match.group(0):
                method_names.append(method_name)
            # Also include if it starts with uppercase (likely a method)
            elif method_name[0].isupper():
                method_names.append(method_name)
    
    return method_names


def extract_repository_methods(file_path: str) -> List[str]:
    """
    Extract all method names from a repository file.
    
    Args:
        file_path: Path to the repository file
        
    Returns:
        List of method names found in the repository
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return []
    
    # Extract class name from DefineStandardPointers
    class_name_match = re.search(r'DefineStandardPointers\s*\(\s*(\w+)\s*\)', content)
    if not class_name_match:
        print(f"Could not find DefineStandardPointers in {file_path}", file=sys.stderr)
        return []
    
    class_name = class_name_match.group(1)
    
    # Extract class content
    class_content = extract_class_content(content, class_name)
    if not class_content:
        print(f"Could not extract class content for {class_name} in {file_path}", file=sys.stderr)
        return []
    
    # Extract method names
    method_names = extract_method_names(class_content)
    
    return method_names


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python extract_repository_methods.py <repository_file_path>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    method_names = extract_repository_methods(file_path)
    
    if method_names:
        for method_name in method_names:
            print(method_name)
        sys.exit(0)
    else:
        print(f"No methods found in {file_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

