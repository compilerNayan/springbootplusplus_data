#!/usr/bin/env python3
"""
Script to extract entity type from a repository class.

This script reads a repository file and extracts the entity type
from the CpaRepository<Entity, ID> template parameter.

Examples:
    class CustomerRepository : public CpaRepository<Customer, int>
    -> Returns: Customer
    
    template<typename Entity, typename ID>
    class UserRepository : public CpaRepository<Entity, ID>
    -> Returns: Entity (for templated repositories)

Usage:
    python extract_entity_type.py <repository_file_path>
    
Returns:
    The entity type name (e.g., "Customer", "Entity", "User")
"""

import re
import sys
from typing import Optional


def remove_comments(content: str) -> str:
    """Remove both // and /* */ style comments."""
    # Remove single-line comments
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    return content


def extract_entity_type(repository_file: str) -> Optional[str]:
    """
    Extract entity type from a repository file.
    
    Args:
        repository_file: Path to the repository file
        
    Returns:
        Entity type name (e.g., "Customer", "Entity", "User"), or None if not found
    """
    try:
        with open(repository_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {repository_file}: {e}", file=sys.stderr)
        return None
    
    # Remove comments for pattern matching
    content_no_comments = remove_comments(content)
    
    # Extract class name from DefineStandardPointers
    class_name_match = re.search(r'DefineStandardPointers\s*\(\s*(\w+)\s*\)', content_no_comments)
    if not class_name_match:
        return None
    
    class_name = class_name_match.group(1)
    
    # Check if class is templated
    is_templated = bool(re.search(rf'template\s*<\s*[^>]+\s*>\s*class\s+{re.escape(class_name)}', content_no_comments))
    
    # Extract CpaRepository template parameters
    # Pattern: class ClassName : public CpaRepository<EntityType, IDType>
    pattern = rf'class\s+{re.escape(class_name)}\s+(?:final\s+)?:\s*public\s+(?:virtual\s+)?CpaRepository\s*<\s*([^,<>]+)\s*,\s*([^,<>]+)\s*>'
    
    match = re.search(pattern, content_no_comments)
    if not match:
        return None
    
    entity_type = match.group(1).strip()
    
    # For templated repositories, return "Entity" (the template parameter)
    # For non-templated repositories, return the concrete type
    if is_templated:
        # Check if the entity type is a template parameter
        if entity_type in ['Entity', 'T', 'E']:
            return "Entity"
        else:
            # It's a concrete type even in a templated repository
            return entity_type
    else:
        # Non-templated repository, return the concrete type
        return entity_type


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python extract_entity_type.py <repository_file_path>", file=sys.stderr)
        sys.exit(1)
    
    repository_file = sys.argv[1]
    entity_type = extract_entity_type(repository_file)
    
    if entity_type:
        print(entity_type)
        sys.exit(0)
    else:
        print(f"Could not extract entity type from {repository_file}", file=sys.stderr)
        sys.exit(1)


# Export function for other scripts to import
__all__ = [
    'extract_entity_type',
    'main'
]


if __name__ == "__main__":
    main()

