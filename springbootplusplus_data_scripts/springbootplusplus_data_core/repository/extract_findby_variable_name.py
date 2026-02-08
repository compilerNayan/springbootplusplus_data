#!/usr/bin/env python3
"""
Script to extract variable name from a FindBy method name or method declaration.

This script takes either:
1. A method name like "FindByLastName" 
2. A full method declaration like "Public Virtual Entity FindByLastName(string lastName) = 0;"

And extracts the variable name "lastName" by converting the part after "FindBy"
from PascalCase to camelCase.

Examples:
    FindByLastName -> lastName
    Public Virtual Entity FindByLastName(string lastName) = 0; -> lastName
    Virtual Entity FindByRollNo(int rollNo) = 0; -> rollNo
    FindByName -> name
    FindByAddress -> address
    FindByFirstName -> firstName

Usage:
    python extract_findby_variable_name.py <method_name_or_declaration>
    
Returns:
    The extracted variable name in camelCase, or None if not a FindBy method
"""

import re
import sys
from typing import Optional


def pascal_to_camel(pascal_case: str) -> str:
    """
    Convert PascalCase to camelCase.
    
    Args:
        pascal_case: String in PascalCase (e.g., "LastName")
        
    Returns:
        String in camelCase (e.g., "lastName")
    """
    if not pascal_case:
        return ""
    
    # If first character is uppercase, make it lowercase
    if pascal_case[0].isupper():
        return pascal_case[0].lower() + pascal_case[1:]
    
    return pascal_case


def extract_method_name_from_declaration(method_declaration: str) -> Optional[str]:
    """
    Extract method name from a full method declaration.
    
    Args:
        method_declaration: Full method declaration like 
                          "Public Virtual Entity FindByLastName(string lastName) = 0;"
        
    Returns:
        Method name (e.g., "FindByLastName"), or None if not found
    """
    if not method_declaration:
        return None
    
    # Pattern to match method declarations
    # Matches: [Access] [Virtual/Static] ReturnType MethodName(parameters) [= 0];
    # Examples:
    # - Public Virtual Entity FindByLastName(string lastName) = 0;
    # - Virtual Entity FindByRollNo(int rollNo) = 0;
    # - Entity FindByName(string name);
    
    # Pattern breakdown:
    # (?:Public|Private|Protected|Virtual)?\s*  - Optional access modifier or Virtual
    # (?:Virtual\s+|Static\s+)?                 - Optional Virtual or Static
    # [A-Za-z_][A-Za-z0-9_<>:&*,\s]*            - Return type
    # \s+                                       - Whitespace
    # ([A-Za-z_][A-Za-z0-9_]*)                 - Method name (captured)
    # \s*\(                                     - Opening parenthesis
    
    pattern = r'(?:Public|Private|Protected|Virtual)?\s*(?:Virtual\s+|Static\s+)?[A-Za-z_][A-Za-z0-9_<>:&*,\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
    match = re.search(pattern, method_declaration)
    
    if match:
        return match.group(1)
    
    return None


def extract_findby_variable_name(method_input: str) -> Optional[str]:
    """
    Extract variable name from a FindBy method name or method declaration.
    
    Args:
        method_input: Either a method name like "FindByLastName" or 
                     a full method declaration like "Public Virtual Entity FindByLastName(string lastName) = 0;"
        
    Returns:
        Variable name in camelCase (e.g., "lastName", "name"), or None if not a FindBy method
    """
    if not method_input:
        return None
    
    # First, try to extract method name from a full declaration
    method_name = extract_method_name_from_declaration(method_input)
    
    # If extraction failed, assume the input is already just the method name
    if not method_name:
        method_name = method_input.strip()
    
    # Pattern to match FindBy methods (case-insensitive)
    # Matches: FindBy, FindByLastName, FindByName, etc.
    pattern = r'^FindBy(.+)$'
    match = re.match(pattern, method_name, re.IGNORECASE)
    
    if not match:
        return None
    
    # Extract the part after "FindBy"
    pascal_case_part = match.group(1)
    
    # Convert to camelCase
    camel_case = pascal_to_camel(pascal_case_part)
    
    return camel_case


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python extract_findby_variable_name.py <method_name_or_declaration>", file=sys.stderr)
        sys.exit(1)
    
    method_input = sys.argv[1]
    variable_name = extract_findby_variable_name(method_input)
    
    if variable_name:
        print(variable_name)
        sys.exit(0)
    else:
        print(f"'{method_input}' is not a FindBy method", file=sys.stderr)
        sys.exit(1)


# Export function for other scripts to import
__all__ = [
    'extract_findby_variable_name',
    'pascal_to_camel',
    'main'
]


if __name__ == "__main__":
    main()

