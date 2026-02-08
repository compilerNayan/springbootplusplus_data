#!/usr/bin/env python3
"""
S7 Extract Validation Fields Script

Generic script to extract fields with any validation annotation.
Uses discovered validation macros to find fields with validation annotations.
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Set

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    import S2_extract_dto_fields
    import S6_discover_validation_macros
except ImportError as e:
    sys.exit(1)


def is_string_type(field_type: str) -> bool:
    """Check if a field type is a string type."""
    field_type_clean = field_type.strip()
    
    if 'optional<' in field_type_clean.lower():
        match = re.search(r'(?:std::)?optional<(.+)>', field_type_clean, re.IGNORECASE)
        if match:
            inner_type = match.group(1).strip()
            field_type_clean = inner_type
    
    field_type_lower = field_type_clean.lower()
    string_types = ['stdstring', 'cstdstring', 'std::string', 'const std::string', 'string']
    return any(st in field_type_lower for st in string_types)


def get_validation_function_info(validation_macros: Dict[str, str], macro_name: str) -> Optional[Dict[str, str]]:
    """Get information about a validation function from the macro name."""
    if macro_name not in validation_macros:
        return None
    
    function_name = validation_macros[macro_name]
    requires_string_type = 'NotBlank' in function_name or 'NotEmpty' in function_name or 'String' in function_name
    
    return {
        'function_name': function_name,
        'requires_string_type': requires_string_type
    }


def extract_validation_fields(file_path: str, class_name: str, validation_macros: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
    """Extract all fields with validation annotations."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except Exception as e:
        pass
    
    boundaries = S2_extract_dto_fields.find_class_boundaries(file_path, class_name)
    if not boundaries:
        return {}
    
    start_line, end_line = boundaries
    class_lines = lines[start_line - 1:end_line]
    
    macro_names = list(validation_macros.keys())
    if not macro_names:
        return {}
    
    annotation_patterns = {}
    for macro_name in macro_names:
        annotation_patterns[macro_name] = rf'///\s*@{re.escape(macro_name)}\b'
    
    all_annotations = '|'.join(annotation_patterns.values())
    validation_pattern = rf'({all_annotations})'
    
    access_pattern = r'^\s*(public|private|protected)\s*:'
    field_pattern = r'^\s*(?:Public|Private|Protected)?\s*([A-Za-z_][A-Za-z0-9_<>*&,\s]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*[;=]'
    
    result = {macro: [] for macro in macro_names}
    
    current_access = None
    i = 0
    
    while i < len(class_lines):
        line = class_lines[i]
        stripped = line.strip()
        
        if stripped.startswith('/*'):
            i += 1
            continue
        if stripped.startswith('//') and not re.search(validation_pattern, stripped):
            i += 1
            continue
        
        if not stripped:
            i += 1
            continue
        
        access_match = re.search(access_pattern, stripped, re.IGNORECASE)
        if access_match:
            current_access = access_match.group(1).lower()
            i += 1
            continue
        
        validation_match = re.search(validation_pattern, stripped)
        if validation_match:
            matched_annotation = None
            for macro_name, pattern in annotation_patterns.items():
                if re.search(pattern, stripped):
                    matched_annotation = macro_name
                    break
            
            if matched_annotation:
                validation_info = get_validation_function_info(validation_macros, matched_annotation)
                
                if validation_info:
                    found_field = False
                    for j in range(i + 1, min(i + 11, len(class_lines))):
                        next_line = class_lines[j].strip()
                        
                        if next_line.startswith('/*'):
                            continue
                        if next_line.startswith('//') and not re.search(r'///\s*@(NotNull|NotEmpty|NotBlank|Id|Entity|Serializable)\b', next_line):
                            continue
                        
                        if not next_line:
                            continue
                        
                        if re.search(validation_pattern, next_line):
                            continue
                        
                        field_match = re.search(field_pattern, next_line)
                        if field_match:
                            field_type = field_match.group(1).strip()
                            field_name = field_match.group(2).strip()
                            if '(' not in next_line and ')' not in next_line and field_name not in ['public', 'private', 'protected']:
                                if validation_info['requires_string_type']:
                                    if is_string_type(field_type):
                                        result[matched_annotation].append({
                                            'type': field_type,
                                            'name': field_name,
                                            'access': current_access if current_access else 'none',
                                            'function_name': validation_info['function_name']
                                        })
                                else:
                                    result[matched_annotation].append({
                                        'type': field_type,
                                        'name': field_name,
                                        'access': current_access if current_access else 'none',
                                        'function_name': validation_info['function_name']
                                    })
                                found_field = True
                            break
                        
                        if next_line and (re.search(access_pattern, next_line, re.IGNORECASE) or 
                                         re.search(r'^\s*(Dto|Serializable|COMPONENT|SCOPE|VALIDATE|///\s*@(NotNull|NotEmpty|NotBlank|Id|Entity|Serializable))\s*$', next_line)):
                            break
            
            i += 1
            continue
        
        i += 1
    
    return {k: v for k, v in result.items() if v}


def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract fields with validation annotations from a class"
    )
    parser.add_argument(
        "file_path",
        help="Path to the C++ file"
    )
    parser.add_argument(
        "--class-name",
        required=True,
        help="Name of the class to extract fields from"
    )
    parser.add_argument(
        "--search-dirs",
        nargs="+",
        default=['src', 'platform'],
        help="Directories to search for validation macro definitions"
    )
    
    args = parser.parse_args()
    
    validation_macros = S6_discover_validation_macros.find_validation_macro_definitions(args.search_dirs)
    
    if not validation_macros:
        pass
    
    fields_by_macro = extract_validation_fields(args.file_path, args.class_name, validation_macros)
    
    return 0


# Export functions for other scripts to import
__all__ = [
    'extract_validation_fields',
    'get_validation_function_info',
    'is_string_type',
    'main'
]


if __name__ == "__main__":
    exit(main())

