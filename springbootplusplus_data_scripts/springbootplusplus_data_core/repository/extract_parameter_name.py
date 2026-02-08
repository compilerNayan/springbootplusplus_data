#!/usr/bin/env python3
"""
Script to extract parameter name from a method declaration.

This script takes a method declaration and extracts the parameter name
from the first parameter.

Examples:
    Public Virtual SomeClass FindByName(string xyz); -> xyz
    Public Virtual SomeClass FindByName(std::string xyz); -> xyz
    Public Virtual SomeClass FindByName(CStdString xyz); -> xyz
    Public Virtual SomeClass FindByName(int xyz); -> xyz
    Public Virtual SomeClass FindByName(anything xyz); -> xyz
    Public Virtual SomeClass FindByName(string abcf_ffd); -> abcf_ffd
    Public Virtual Entity Save(Entity& entity); -> entity
    Public Virtual optional<Entity> FindById(ID id); -> id

Usage:
    python extract_parameter_name.py <method_declaration>
    
Returns:
    The extracted parameter name, or None if not found
"""

import re
import sys
from typing import Optional


def extract_parameter_name(method_declaration: str) -> Optional[str]:
    """
    Extract parameter name from a method declaration.
    
    Args:
        method_declaration: Full method declaration like 
                          "Public Virtual SomeClass FindByName(string xyz);"
        
    Returns:
        Parameter name (e.g., "xyz", "abcf_ffd"), or None if not found
    """
    if not method_declaration:
        return None
    
    # Find the parameter list (content between parentheses)
    # Pattern to match: MethodName(...)
    param_pattern = r'\(([^)]*)\)'
    match = re.search(param_pattern, method_declaration)
    
    if not match:
        return None
    
    parameters = match.group(1).strip()
    
    # If no parameters, return None
    if not parameters:
        return None
    
    # Handle multiple parameters - take the first one
    # Split by comma, but be careful with template types and nested parentheses
    # For now, let's handle the simple case of single parameter or comma-separated
    # We'll take the first parameter
    
    # Split by comma, but only if not inside angle brackets or parentheses
    # For simplicity, split by comma and take first
    first_param = parameters.split(',')[0].strip()
    
    # Pattern to extract parameter name
    # The parameter name is typically the last identifier in the parameter declaration
    # Examples:
    # - string xyz -> xyz
    # - std::string xyz -> xyz
    # - const string& xyz -> xyz
    # - string* xyz -> xyz
    # - Entity& entity -> entity
    # - ID id -> id
    # - string abcf_ffd -> abcf_ffd
    
    # Pattern breakdown:
    # Match the last identifier (parameter name) which can contain letters, numbers, underscores
    # It should be at the end of the parameter declaration
    # Handle cases with const, &, *, etc. before the name
    
    # More robust pattern:
    # - Skip any leading keywords (const, volatile, etc.)
    # - Skip type (which can include ::, <>, &, *, etc.)
    # - Capture the parameter name (identifier at the end)
    
    # Pattern: match identifier at the end (after type and modifiers)
    # The parameter name is the last word-like identifier
    param_name_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*$'
    param_match = re.search(param_name_pattern, first_param)
    
    if param_match:
        return param_match.group(1)
    
    return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python extract_parameter_name.py <method_declaration>", file=sys.stderr)
        sys.exit(1)
    
    method_declaration = sys.argv[1]
    parameter_name = extract_parameter_name(method_declaration)
    
    if parameter_name:
        print(parameter_name)
        sys.exit(0)
    else:
        print(f"Could not extract parameter name from '{method_declaration}'", file=sys.stderr)
        sys.exit(1)


# Export function for other scripts to import
__all__ = [
    'extract_parameter_name',
    'main'
]


if __name__ == "__main__":
    main()

