#!/usr/bin/env python3
"""
Script to extract action from a repository method name.

This script takes a method name like "FindByFirstName" or "DeleteByLastName"
and extracts the action part (e.g., "Find", "Delete").

The action list follows JpaRepository conventions:
- Find (FindBy, FindAll, FindById)
- Delete (DeleteBy, DeleteById, DeleteAll)
- Save
- Update
- Exists (ExistsBy, ExistsById)
- Count (CountBy, CountAll)

Examples:
    FindByFirstName -> Find
    DeleteByLastName -> Delete
    ExistsById -> Exists
    CountByStatus -> Count
    Save -> Save
    Update -> Update

Usage:
    python extract_method_action.py <method_name>
    
Returns:
    The extracted action name, or None if not a recognized action
"""

import re
import sys
from typing import Optional, List


# Standard JpaRepository actions
STANDARD_ACTIONS = [
    'Find',
    'Delete',
    'Save',
    'Update',
    'Exists',
    'Count',
]


def extract_method_action(method_name: str) -> Optional[str]:
    """
    Extract action from a repository method name.
    
    Args:
        method_name: Method name like "FindByFirstName", "DeleteByLastName", etc.
        
    Returns:
        Action name (e.g., "Find", "Delete"), or None if not a recognized action
    """
    if not method_name:
        return None
    
    # Pattern to match actions followed by "By"
    # Matches: FindBy, DeleteBy, ExistsBy, CountBy
    pattern = r'^([A-Z][a-z]+)By'
    match = re.match(pattern, method_name)
    
    if match:
        action = match.group(1)
        # Validate that it's a standard action
        if action in STANDARD_ACTIONS:
            return action
    
    # Check for methods without "By" (e.g., Save, Update, FindAll, DeleteAll, CountAll)
    # These are standalone action methods
    for action in STANDARD_ACTIONS:
        # Exact match (e.g., "Save", "Update")
        if method_name == action:
            return action
        
        # Action followed by "All" (e.g., "FindAll", "DeleteAll", "CountAll")
        if method_name == f"{action}All":
            return action
        
        # Action followed by "ById" (e.g., "FindById", "DeleteById", "ExistsById")
        if method_name == f"{action}ById":
            return action
    
    return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python extract_method_action.py <method_name>", file=sys.stderr)
        sys.exit(1)
    
    method_name = sys.argv[1]
    action = extract_method_action(method_name)
    
    if action:
        print(action)
        sys.exit(0)
    else:
        print(f"'{method_name}' does not contain a recognized action", file=sys.stderr)
        sys.exit(1)


# Export function for other scripts to import
__all__ = [
    'extract_method_action',
    'STANDARD_ACTIONS',
    'main'
]


if __name__ == "__main__":
    main()

