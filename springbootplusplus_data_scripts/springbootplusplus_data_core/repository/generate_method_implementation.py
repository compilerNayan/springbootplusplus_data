#!/usr/bin/env python3
"""
Script to generate C++ method implementation code for repository methods.

This script takes action, variable name, parameter name, and function signature
as input and generates the implementation code.

Currently supports:
- Find action: generates code that finds entity by field value

Examples:
    Action: Find
    Variable name: lastName
    Parameter name: someVariableName
    Function signature: Public Virtual optional<Entity> FindByLastName(CStdString& lastName) override {
    
    Generates:
        Public Virtual optional<Entity> FindByLastName(CStdString& someVariableName) override {
            StdVector<Entity> entities = FindAll();
            for (const auto& entity : entities) {
                if (entity.lastName == someVariableName) {
                    return entity;
                }
            }
            return std::nullopt;
        }

Usage:
    python generate_method_implementation.py <action> <variable_name> <parameter_name> <function_signature>
    
Returns:
    The generated C++ method implementation code
"""

import re
import sys
from typing import Optional, Tuple


def parse_function_signature(signature: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse function signature to extract components.
    
    Args:
        signature: Function signature like "Public Virtual optional<Entity> FindByLastName(CStdString& lastName) override {"
        
    Returns:
        Tuple of (access_modifier, return_type, method_name, parameter_declaration)
    """
    if not signature:
        return (None, None, None, None)
    
    # Remove trailing "override {" or "= 0;" or just "{"
    signature = re.sub(r'\s*(override\s*)?\{?\s*$', '', signature)
    signature = re.sub(r'\s*=\s*0\s*;?\s*$', '', signature)
    signature = signature.strip()
    
    # Extract access modifier (Public, Private, Protected, or Virtual)
    access_match = re.match(r'^(Public|Private|Protected|Virtual)\s+', signature)
    access_modifier = access_match.group(1) if access_match else None
    
    # Remove access modifier from signature for further parsing
    if access_modifier:
        signature = re.sub(r'^(Public|Private|Protected|Virtual)\s+', '', signature)
    
    # Check for Virtual keyword
    has_virtual = False
    if signature.startswith('Virtual '):
        has_virtual = True
        signature = signature.replace('Virtual ', '', 1)
    
    # Reconstruct access modifier with Virtual if needed
    if access_modifier and has_virtual:
        access_modifier = f"{access_modifier} Virtual"
    elif has_virtual:
        access_modifier = "Virtual"
    elif not access_modifier:
        access_modifier = "Public"
    
    # Extract return type and method name
    # Pattern: ReturnType MethodName(parameters)
    method_pattern = r'^([A-Za-z_][A-Za-z0-9_<>:&*,\s]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)'
    match = re.match(method_pattern, signature)
    
    if not match:
        return (access_modifier, None, None, None)
    
    return_type = match.group(1).strip()
    method_name = match.group(2).strip()
    parameter_declaration = match.group(3).strip()
    
    return (access_modifier, return_type, method_name, parameter_declaration)


def generate_find_implementation(access_modifier: str, return_type: str, method_name: str, 
                                 parameter_declaration: str, variable_name: str, parameter_name: str, 
                                 entity_type: str = "Entity") -> str:
    """
    Generate implementation code for Find action.
    
    Args:
        access_modifier: Access modifier like "Public Virtual"
        return_type: Return type like "optional<Entity>" or "Entity" or "StdVector<Entity>"
        method_name: Method name like "FindByLastName"
        parameter_declaration: Parameter declaration like "CStdString& lastName"
        variable_name: Variable name in camelCase like "lastName"
        parameter_name: Parameter name like "someVariableName"
        
    Returns:
        Generated C++ method implementation code
    """
    # Determine if return type is optional, vector, or single entity
    is_optional = 'optional' in return_type or 'Optional' in return_type
    is_vector = 'StdVector' in return_type or 'vector' in return_type or 'Vector' in return_type
    
    # Build the method signature
    method_signature = f"    {access_modifier} {return_type} {method_name}({parameter_declaration}) override {{"
    
    # Generate implementation based on return type
    if is_optional:
        # Return optional<EntityType> - find first match
        code = f"""{method_signature}
        StdVector<{entity_type}> entities = FindAll();
        for (const auto& entity : entities) {{
            if (entity.{variable_name} == {parameter_name}) {{
                return entity;
            }}
        }}
        return std::nullopt;
    }}"""
    elif is_vector:
        # Return StdVector<EntityType> - find all matches
        code = f"""{method_signature}
        StdVector<{entity_type}> entities = FindAll();
        StdVector<{entity_type}> result;
        for (const auto& entity : entities) {{
            if (entity.{variable_name} == {parameter_name}) {{
                result.push_back(entity);
            }}
        }}
        return result;
    }}"""
    else:
        # Return single EntityType - find first match (may need to handle not found case)
        code = f"""{method_signature}
        StdVector<{entity_type}> entities = FindAll();
        for (const auto& entity : entities) {{
            if (entity.{variable_name} == {parameter_name}) {{
                return entity;
            }}
        }}
        // TODO: Handle case when entity not found
        return {entity_type}();
    }}"""
    
    return code


def generate_method_implementation(action: str, variable_name: str, parameter_name: str, 
                                  function_signature: str, entity_type: str = "Entity") -> Optional[str]:
    """
    Generate C++ method implementation code.
    
    Args:
        action: Action like "Find", "Delete", etc. (currently only "Find" is supported)
        variable_name: Variable name in camelCase like "lastName"
        parameter_name: Parameter name like "someVariableName"
        function_signature: Full function signature like "Public Virtual optional<Entity> FindByLastName(CStdString& lastName) override {"
        
    Returns:
        Generated C++ method implementation code, or None if action is not supported
    """
    if not action or not variable_name or not parameter_name or not function_signature:
        return None
    
    # Parse function signature
    access_modifier, return_type, method_name, parameter_declaration = parse_function_signature(function_signature)
    
    if not return_type or not method_name:
        return None
    
    # Replace parameter name in parameter_declaration with the provided parameter_name
    # Extract the type part and rebuild with new parameter name
    if parameter_declaration:
        # Find the last identifier (current parameter name) and replace it
        param_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*$'
        parameter_declaration = re.sub(param_pattern, parameter_name, parameter_declaration)
    
    # Generate implementation based on action
    if action.lower() == "find":
        return generate_find_implementation(access_modifier or "Public Virtual", return_type, 
                                           method_name, parameter_declaration or "", 
                                           variable_name, parameter_name, entity_type)
    else:
        # Other actions not yet implemented
        return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 5:
        print("Usage: python generate_method_implementation.py <action> <variable_name> <parameter_name> <function_signature>", file=sys.stderr)
        print("Example: python generate_method_implementation.py Find lastName someVariableName 'Public Virtual optional<Entity> FindByLastName(CStdString& lastName) override {'", file=sys.stderr)
        sys.exit(1)
    
    action = sys.argv[1]
    variable_name = sys.argv[2]
    parameter_name = sys.argv[3]
    function_signature = sys.argv[4]
    
    # If function signature contains spaces and wasn't quoted, join remaining args
    if len(sys.argv) > 5:
        function_signature = ' '.join(sys.argv[4:])
    
    code = generate_method_implementation(action, variable_name, parameter_name, function_signature)
    
    if code:
        print(code)
        sys.exit(0)
    else:
        print(f"Could not generate implementation for action '{action}'", file=sys.stderr)
        sys.exit(1)


# Export functions for other scripts to import
__all__ = [
    'generate_method_implementation',
    'generate_find_implementation',
    'parse_function_signature',
    'main'
]


if __name__ == "__main__":
    main()

