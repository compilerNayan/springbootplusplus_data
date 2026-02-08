#!/usr/bin/env python3
"""
Script to generate complete repository implementation body.

This script:
1. Extracts all methods from a repository interface
2. For each method, extracts:
   - Variable name (from method name)
   - Action (Find, Delete, etc.)
   - Parameter name (from method declaration)
3. Generates implementation code for each method
4. Concatenates all generated code

Usage:
    python generate_repository_implementation.py <repository_file_path>
    
Returns:
    Complete repository implementation body with all method implementations
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Add current directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from extract_repository_methods import extract_repository_methods
from extract_findby_variable_name import extract_findby_variable_name
from extract_method_action import extract_method_action
from extract_parameter_name import extract_parameter_name
from extract_entity_type import extract_entity_type
from generate_method_implementation import generate_method_implementation


def get_method_declaration(repository_file: str, method_name: str) -> Optional[str]:
    """
    Extract the full method declaration from repository file.
    
    Args:
        repository_file: Path to repository file
        method_name: Name of the method to find
        
    Returns:
        Full method declaration string, or None if not found
    """
    try:
        with open(repository_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {repository_file}: {e}", file=sys.stderr)
        return None
    
    # Remove comments for pattern matching
    content_no_comments = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content_no_comments = re.sub(r'/\*.*?\*/', '', content_no_comments, flags=re.DOTALL)
    
    # Extract class content
    class_name_match = re.search(r'DefineStandardPointers\s*\(\s*(\w+)\s*\)', content_no_comments)
    if not class_name_match:
        return None
    
    class_name = class_name_match.group(1)
    
    # Extract class body
    class_pattern = rf'class\s+{re.escape(class_name)}\s+(?:final\s+)?:\s*public\s+(?:virtual\s+)?CpaRepository\s*<\s*[^>]+\s*>\s*{{(.*?)}};'
    class_match = re.search(class_pattern, content_no_comments, re.DOTALL)
    if not class_match:
        return None
    
    class_body = class_match.group(1)
    
    # Find method declaration - look for method name followed by opening parenthesis
    # Use a simpler approach: search line by line for the method name
    lines = class_body.split('\n')
    for line in lines:
        stripped = line.strip()
        # Check if this line contains the method name followed by opening parenthesis
        # Make sure it's the exact method name (word boundary)
        if re.search(rf'\b{re.escape(method_name)}\s*\(', stripped):
            return stripped
    
    return None


def extract_method_info(repository_file: str, method_name: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Extract all information needed to generate method implementation.
    
    Args:
        repository_file: Path to repository file
        method_name: Name of the method
        
    Returns:
        Tuple of (action, variable_name, parameter_name, method_declaration) or None
    """
    # Get method declaration
    method_declaration = get_method_declaration(repository_file, method_name)
    if not method_declaration:
        return None
    
    # Extract action
    action = extract_method_action(method_name)
    if not action:
        # If not a standard action, skip this method (it's probably a base method)
        return None
    
    # Extract variable name (only for FindBy, DeleteBy, etc. methods)
    variable_name = extract_findby_variable_name(method_declaration)
    if not variable_name:
        # If no variable name extracted, it might be a base method (Save, Update, etc.)
        # Skip for now - we only generate code for custom FindBy/DeleteBy methods
        return None
    
    # Extract parameter name
    parameter_name = extract_parameter_name(method_declaration)
    if not parameter_name:
        return None
    
    return (action, variable_name, parameter_name, method_declaration)


def generate_repository_implementation(repository_file: str) -> Optional[str]:
    """
    Generate complete repository implementation body.
    
    Args:
        repository_file: Path to repository file
        
    Returns:
        Complete implementation code for all custom methods, or None on error
    """
    # Extract entity type from repository
    entity_type = extract_entity_type(repository_file)
    if not entity_type:
        # Default to Entity if extraction fails
        entity_type = "Entity"
    
    # Extract all methods from repository
    method_names = extract_repository_methods(repository_file)
    if not method_names:
        return None
    
    implementations = []
    
    # Process each method
    for method_name in method_names:
        # Extract method info
        method_info = extract_method_info(repository_file, method_name)
        if not method_info:
            continue
        
        action, variable_name, parameter_name, method_declaration = method_info
        
        # Generate implementation code with entity type
        code = generate_method_implementation(
            action, 
            variable_name, 
            parameter_name, 
            method_declaration,
            entity_type
        )
        
        if code:
            implementations.append(code)
    
    # Concatenate all implementations
    if implementations:
        return '\n\n'.join(implementations)
    
    return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python generate_repository_implementation.py <repository_file_path>", file=sys.stderr)
        sys.exit(1)
    
    repository_file = sys.argv[1]
    
    if not os.path.exists(repository_file):
        print(f"Error: Repository file not found: {repository_file}", file=sys.stderr)
        sys.exit(1)
    
    implementation_code = generate_repository_implementation(repository_file)
    
    if implementation_code:
        print(implementation_code)
        sys.exit(0)
    else:
        print(f"No custom methods found or could not generate implementation for {repository_file}", file=sys.stderr)
        sys.exit(1)


# Export functions for other scripts to import
__all__ = [
    'generate_repository_implementation',
    'extract_method_info',
    'get_method_declaration',
    'main'
]


if __name__ == "__main__":
    main()

