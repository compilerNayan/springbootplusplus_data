#!/usr/bin/env python3
"""
Extract @Id Fields Script

This script checks if a file has the @Serializable or @Entity annotation,
and if it does, extracts fields marked with @Id annotation.
The @Id annotation can be followed by validation annotations (like @NotNull, @NotBlank) 
and then the type and variable name.

Patterns supported:
- /// @Id
  int rollNo;
  
- /// @Id
  StdString name;
  
- /// @Id
  const long digit;
  
- /// @Id
  /// @NotNull
  int someVar;
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

# print("Executing springbootplusplus_data_core/extract_id_fields.py")

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_scripts_dir)

# Try to import from local serialization scripts
try:
    # Find local serialization scripts directory
    serialization_dir = Path(script_dir) / "serialization"
    if serialization_dir.exists():
        sys.path.insert(0, str(serialization_dir))
        
        try:
            import S1_check_dto_macro
            import S2_extract_dto_fields
            import S6_discover_validation_macros
            HAS_SERIALIZATIONLIB = True
        except ImportError as e:
            HAS_SERIALIZATIONLIB = False
    else:
        HAS_SERIALIZATIONLIB = False
except Exception as e:
    HAS_SERIALIZATIONLIB = False


def check_has_serializable_macro(file_path: str, serializable_macro: str = "_Entity") -> Optional[Dict[str, any]]:
    """
    Check if a file has the @Serializable or @Entity annotation.
    
    Args:
        file_path: Path to the C++ file
        serializable_macro: Name of the macro (Serializable -> @Serializable, _Entity -> @Entity)
        
    Returns:
        Dictionary with 'class_name', 'has_dto', 'line_number' if found, None otherwise
    """
    if HAS_SERIALIZATIONLIB:
        return S1_check_dto_macro.check_dto_macro(file_path, serializable_macro)
    else:
        # Fallback implementation
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except Exception as e:
            # print(f"Error reading file '{file_path}': {e}")
            return None
        
        # Determine annotation name based on macro name
        if serializable_macro == "_Entity":
            annotation_name = "@Entity"
        elif serializable_macro == "Serializable":
            annotation_name = "@Serializable"
        else:
            # Default to @Serializable for backward compatibility
            annotation_name = "@Serializable"
        
        # Pattern to match /* @Entity */ or /*@Entity*/ or /* @Serializable */ or /*@Serializable*/ annotation (ignoring whitespace)
        # Also check for already processed /*--@Entity--*/ or /*--@Serializable--*/ pattern
        annotation_pattern = rf'/\*\s*{re.escape(annotation_name)}\s*\*/'
        processed_pattern = rf'/\*--\s*{re.escape(annotation_name)}\s*--\*/'
        class_pattern = r'class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:[:{])'
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # Check if line is already processed (/*--@Entity--*/ or /*--@Serializable--*/)
            if re.search(processed_pattern, stripped_line):
                continue
            
            # Skip other comments that aren't @Entity/@Serializable annotations
            # But allow /* @Entity */ or /* @Serializable */ annotations to be processed
            if stripped_line.startswith('/*') and not re.search(annotation_pattern, stripped_line):
                continue
            # Skip single-line comments
            if stripped_line.startswith('//'):
                continue
            
            # Check for annotation (/* @Entity */ or /*@Entity*/ or /* @Serializable */ or /*@Serializable*/)
            annotation_match = re.search(annotation_pattern, stripped_line)
            if annotation_match:
                for i in range(line_num, min(line_num + 11, len(lines) + 1)):
                    if i <= len(lines):
                        next_line = lines[i - 1].strip()
                        
                        # Skip other comments that aren't annotations
                        # But allow /* @Entity */ or /* @Serializable */ annotations to be processed
                        if next_line.startswith('/*') and not re.search(annotation_pattern, next_line):
                            continue
                        # Skip single-line comments
                        if next_line.startswith('//'):
                            continue
                        
                        class_match = re.search(class_pattern, next_line)
                        if class_match:
                            class_name = class_match.group(1)
                            return {
                                'class_name': class_name,
                                'has_dto': True,
                                'dto_line': line_num,
                                'class_line': i
                            }
        
        return {'has_dto': False}


def extract_id_fields(file_path: str, class_name: str, validation_macros: Dict[str, str] = None) -> List[Dict[str, str]]:
    """
    Extract all fields marked with @Id annotation.
    
    Args:
        file_path: Path to the C++ file
        class_name: Name of the class
        validation_macros: Optional dictionary of validation macros to recognize
        
    Returns:
        List of dictionaries with 'type', 'name', and optional 'validation_macros' keys
        Example: [{'type': 'int', 'name': 'rollNo'}, {'type': 'StdString', 'name': 'name', 'validation_macros': ['NotNull']}]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except Exception as e:
        # print(f"Error reading file: {e}")
        return []
    
    # Find class boundaries
    if HAS_SERIALIZATIONLIB:
        boundaries = S2_extract_dto_fields.find_class_boundaries(file_path, class_name)
    else:
        # Fallback implementation
        boundaries = None
        class_start = None
        brace_count = 0
        in_class = False
        class_pattern = rf'class\s+{re.escape(class_name)}'
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            if stripped_line.startswith('//') or stripped_line.startswith('/*') or stripped_line.startswith('*'):
                continue
            
            if not in_class and re.search(class_pattern, stripped_line):
                class_start = line_num
                in_class = True
                brace_count = stripped_line.count('{') - stripped_line.count('}')
            elif in_class:
                brace_count += stripped_line.count('{')
                brace_count -= stripped_line.count('}')
            
            if in_class and brace_count == 0:
                boundaries = (class_start, line_num)
                break
    
    if not boundaries:
        return []
    
    start_line, end_line = boundaries
    class_lines = lines[start_line - 1:end_line]
    
    # Discover validation macros if not provided
    if validation_macros is None:
        if HAS_SERIALIZATIONLIB:
            try:
                validation_macros = S6_discover_validation_macros.find_validation_macro_definitions(None)
            except:
                validation_macros = {}
        else:
            validation_macros = {}
    
    # Build pattern for validation annotations
    macro_names = list(validation_macros.keys()) if validation_macros else []
    # Create annotation patterns (e.g., 'NotNull' -> '/* @NotNull */')
    annotation_patterns = {}
    for macro_name in macro_names:
        annotation_patterns[macro_name] = rf'/\*\s*@{re.escape(macro_name)}\s*\*/'
    
    # Combined pattern to match any validation annotation
    all_annotations = '|'.join(annotation_patterns.values()) if annotation_patterns else ''
    validation_pattern = rf'({all_annotations})' if all_annotations else None
    
    # Pattern for /* @Id */ or /*@Id*/ annotation (ignoring whitespace)
    # Also check for already processed /*--@Id--*/ pattern
    id_annotation_pattern = r'/\*\s*@Id\s*\*/'
    id_processed_pattern = r'/\*--\s*@Id\s*--\*/'
    
    # Pattern for field declaration
    # Matches: "int rollNo;", "StdString name;", "const long digit;", etc.
    field_pattern = r'^\s*(?:Public|Private|Protected)?\s*(?:const\s+)?([A-Za-z_][A-Za-z0-9_<>*&,\s]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*[;=]'
    
    result = []
    i = 0
    
    while i < len(class_lines):
        line = class_lines[i]
        stripped = line.strip()
        
        # Skip other comments that aren't @Id annotations
        # But allow /* @Id */ annotations to be processed
        if stripped.startswith('/*') and not re.search(id_annotation_pattern, stripped):
            i += 1
            continue
        # Skip single-line comments
        if stripped.startswith('//'):
            i += 1
            continue
        
        # Skip empty lines
        if not stripped:
            i += 1
            continue
        
        # Check if line is already processed (/*--@Id--*/)
        if re.search(id_processed_pattern, stripped):
            i += 1
            continue
        
        # Check for @Id annotation (/* @Id */ or /*@Id*/)
        id_match = re.search(id_annotation_pattern, stripped)
        if id_match:
            # Look ahead for field declaration (within next 15 lines, may have validation macros in between)
            found_field = False
            validation_macros_found = []
            
            for j in range(i + 1, min(i + 16, len(class_lines))):
                next_line = class_lines[j].strip()
                
                # Skip other comments that aren't annotations
                # But allow /* @Id */ and validation annotations to be processed
                if next_line.startswith('/*') and not (re.search(id_annotation_pattern, next_line) or (validation_pattern and re.search(validation_pattern, next_line))):
                    continue
                # Skip single-line comments
                if next_line.startswith('//'):
                    continue
                
                # Skip empty lines
                if not next_line:
                    continue
                
                # Check for validation annotations (can appear between @Id and field)
                if validation_pattern and re.search(validation_pattern, next_line):
                    # Find which annotation was matched
                    matched_annotation = None
                    for macro_name, pattern in annotation_patterns.items():
                        if re.search(pattern, next_line):
                            matched_annotation = macro_name
                            break
                    if matched_annotation:
                        validation_macros_found.append(matched_annotation)
                    continue
                
                # Check for field declaration
                field_match = re.search(field_pattern, next_line)
                if field_match:
                    field_type = field_match.group(1).strip()
                    field_name = field_match.group(2).strip()
                    
                    # Skip if it looks like a method declaration
                    if '(' not in next_line and ')' not in next_line and field_name not in ['public', 'private', 'protected']:
                        field_info = {
                            'type': field_type,
                            'name': field_name
                        }
                        
                        if validation_macros_found:
                            field_info['validation_macros'] = validation_macros_found
                        
                        result.append(field_info)
                        found_field = True
                    break
                
                # Stop if we hit another annotation or access specifier
                if next_line and (re.search(r'^\s*(public|private|protected)\s*:', next_line, re.IGNORECASE) or 
                                 re.search(r'^\s*(Dto|Serializable|_Entity|COMPONENT|SCOPE|VALIDATE|///\s*@(Id|Entity|Serializable|NotNull|NotEmpty|NotBlank))\s*$', next_line)):
                    # If we hit another @Id, that's okay, we'll process it in the next iteration
                    if re.search(id_annotation_pattern, next_line):
                        break
                    # Otherwise, stop looking
                    break
            
            i += 1
            continue
        
        i += 1
    
    return result


def extract_id_fields_from_file(file_path: str, serializable_macro: str = "_Entity") -> Optional[Dict[str, any]]:
    """
    Extract @Id fields from a file that has the @Serializable or @Entity annotation.
    
    Args:
        file_path: Path to the C++ file
        serializable_macro: Name of the macro (Serializable -> @Serializable, _Entity -> @Entity)
        
    Returns:
        Dictionary with 'class_name', 'has_serializable', and 'id_fields' keys, or None if error
    """
    # Check if file has @Serializable or @Entity annotation
    dto_info = check_has_serializable_macro(file_path, serializable_macro)
    
    if not dto_info or not dto_info.get('has_dto'):
        return {
            'has_serializable': False,
            'id_fields': []
        }
    
    class_name = dto_info.get('class_name')
    if not class_name:
        return {
            'has_serializable': False,
            'id_fields': []
        }
    
    # Extract @Id fields
    id_fields = extract_id_fields(file_path, class_name)
    
    return {
        'has_serializable': True,
        'class_name': class_name,
        'id_fields': id_fields
    }


def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract @Id fields from classes with @Serializable or @Entity annotation"
    )
    parser.add_argument(
        "file_path",
        help="Path to the C++ file"
    )
    parser.add_argument(
        "--macro",
        default="_Entity",
        help="Name of the macro (Serializable -> @Serializable, _Entity -> @Entity)"
    )
    
    args = parser.parse_args()
    
    result = extract_id_fields_from_file(args.file_path, args.macro)
    
    if result and result.get('has_serializable'):
        # Determine annotation name for display
        if args.macro == "_Entity":
            annotation_name = "@Entity"
        elif args.macro == "Serializable":
            annotation_name = "@Serializable"
        else:
            annotation_name = "@Serializable"
        # print(f"✅ Class '{result['class_name']}' has {annotation_name} annotation")
        id_fields = result.get('id_fields', [])
        # print(f"   Found {len(id_fields)} @Id field(s):")
        # for field in id_fields:
        #     validation_info = ""
        #     if 'validation_macros' in field and field['validation_macros']:
        #         validation_info = f" (with {', '.join(field['validation_macros'])})"
        #     print(f"     {field['type']} {field['name']}{validation_info}")
        return 0
    else:
        # Determine annotation name for display
        if args.macro == "_Entity":
            annotation_name = "@Entity"
        elif args.macro == "Serializable":
            annotation_name = "@Serializable"
        else:
            annotation_name = "@Serializable"
        # print(f"❌ No class with {annotation_name} annotation found, or no @Id fields found")
        return 1


# Export functions for other scripts to import
__all__ = [
    'check_has_serializable_macro',
    'extract_id_fields',
    'extract_id_fields_from_file',
    'main'
]


if __name__ == "__main__":
    exit(main())

