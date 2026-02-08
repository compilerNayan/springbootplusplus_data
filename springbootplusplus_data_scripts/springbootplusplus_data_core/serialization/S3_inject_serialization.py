#!/usr/bin/env python3
"""
S3 Inject Serialization Script

This script injects Serialize() and Deserialize() methods into Entity classes.
"""

import argparse
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, script_dir)
sys.path.insert(0, parent_dir)

try:
    import S1_check_dto_macro
    import S2_extract_dto_fields
    import S6_discover_validation_macros
    import S7_extract_validation_fields
    # Import extract_id_fields for primary key generation
    from extract_id_fields import extract_id_fields
except ImportError as e:
    sys.exit(1)


def check_include_exists(file_path: str, include_pattern: str) -> bool:
    """Check if an include statement already exists in the file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return include_pattern in content or f'<{include_pattern}>' in content or f'"{include_pattern}"' in content
    except Exception:
        return False


def add_include_if_needed(file_path: str, include_path: str) -> bool:
    """Add an include statement if it doesn't already exist."""
    if check_include_exists(file_path, include_path.replace('<', '').replace('>', '').replace('"', '')):
        return True
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Find the last #include line
        last_include_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('#include'):
                last_include_idx = i
        
        # Insert after the last include
        if last_include_idx >= 0:
            lines.insert(last_include_idx + 1, f'#include {include_path}\n')
        else:
            # No includes found, add after header guard
            for i, line in enumerate(lines):
                if line.strip().startswith('#define') and '_H' in line:
                    lines.insert(i + 1, f'#include {include_path}\n')
                    break
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)
        
        return True
    except Exception as e:
        pass


def is_optional_type(field_type: str) -> bool:
    """Check if a field type is an optional type."""
    field_type_clean = field_type.strip()
    return 'optional<' in field_type_clean or 'std::optional<' in field_type_clean


def extract_inner_type_from_optional(field_type: str) -> str:
    """Extract the inner type from an optional type."""
    match = re.search(r'(?:std::)?optional<(.+)>', field_type)
    if match:
        return match.group(1).strip()
    return field_type


def generate_primary_key_methods(class_name: str, id_fields: List[Dict[str, str]] = None) -> str:
    """
    Generate GetPrimaryKey(), GetPrimaryKeyName(), and GetTableName() methods.
    
    Args:
        class_name: Name of the class
        id_fields: List of @Id field dictionaries with 'type' and 'name' keys
        
    Returns:
        String containing the method definitions
    """
    methods = []
    
    # If we have @Id fields, use the first one as primary key
    if id_fields and len(id_fields) > 0:
        primary_key_field = id_fields[0]
        field_type = primary_key_field['type']
        field_name = primary_key_field['name']
        
        # GetPrimaryKey() method
        methods.append(f"    inline {field_type} GetPrimaryKey() {{")
        methods.append(f"        return {field_name};")
        methods.append(f"    }}")
        methods.append("")
        
        # GetPrimaryKeyName() method
        methods.append(f"    inline Static StdString GetPrimaryKeyName() {{")
        methods.append(f'        return "{field_name}";')
        methods.append(f"    }}")
    else:
        # No @Id field found, generate methods that return default values
        # GetPrimaryKey() method - return default constructed value
        methods.append(f"    inline int GetPrimaryKey() {{")
        methods.append(f"        return 0;")
        methods.append(f"    }}")
        methods.append("")
        
        # GetPrimaryKeyName() method - return empty string
        methods.append(f"    inline Static StdString GetPrimaryKeyName() {{")
        methods.append(f'        return "";')
        methods.append(f"    }}")
    
    methods.append("")
    
    # GetTableName() method - always generate this
    methods.append(f"    inline Static StdString GetTableName() {{")
    methods.append(f'        return "{class_name}";')
    methods.append(f"    }}")
    
    return "\n".join(methods)


def generate_serialization_methods(class_name: str, fields: List[Dict[str, str]], validation_fields_by_macro: Dict[str, List[Dict[str, str]]] = None, id_fields: List[Dict[str, str]] = None) -> str:
    """Generate Serialize() and Deserialize() methods for an Entity class, plus primary key methods."""
    if validation_fields_by_macro is None:
        validation_fields_by_macro = {}
    if id_fields is None:
        id_fields = []
    code_lines = []
    
    # Generate Serialize() method
    code_lines.append("    // Serialization method")
    code_lines.append(f"    Public StdString Serialize() const {{")
    code_lines.append("        // Create JSON document")
    code_lines.append("        JsonDocument doc;")
    code_lines.append("")
    
    # Only serialize optional fields - skip non-optional fields
    primitive_types = ['int', 'Int', 'CInt', 'long', 'Long', 'CLong', 'float', 'Float', 'CFloat', 
                      'double', 'Double', 'CDouble', 'bool', 'Bool', 'CBool', 'char', 'Char', 'CChar',
                      'unsigned', 'UInt', 'CUInt', 'short', 'Short', 'CShort']
    
    optional_fields = [field for field in fields if is_optional_type(field['type'].strip())]
    
    if not optional_fields:
        code_lines.append("        // No optional fields to serialize")
    else:
        for field in optional_fields:
            field_type = field['type'].strip()
            field_name = field['name']
            
            inner_type = extract_inner_type_from_optional(field_type)
            is_primitive = any(prim in inner_type for prim in primitive_types)
            is_string = 'StdString' in inner_type or 'CStdString' in inner_type or 'string' in inner_type.lower()
            
            code_lines.append(f"        // Serialize optional field: {field_name}")
            code_lines.append(f"        if ({field_name}.has_value()) {{")
            
            if is_string:
                code_lines.append(f"            doc[\"{field_name}\"] = {field_name}.value().c_str();")
            elif is_primitive:
                code_lines.append(f"            doc[\"{field_name}\"] = {field_name}.value();")
            else:
                # For nested object/enum types in optional, use SerializeValue
                # SerializeValue handles enums (via template specialization) and complex objects
                code_lines.append(f"            // Serialize nested object or enum: {field_name}")
                code_lines.append(f"            // SerializeValue will use template specialization for enums (returns string like \"Off\")")
                code_lines.append(f"            // or call .Serialize() for complex objects (returns JSON string)")
                code_lines.append(f"            StdString {field_name}_json = nayan::serializer::SerializeValue({field_name}.value());")
                code_lines.append(f"            // Try to parse as JSON object (for complex objects)")
                code_lines.append(f"            JsonDocument {field_name}_doc;")
                code_lines.append(f"            DeserializationError {field_name}_error = deserializeJson({field_name}_doc, {field_name}_json.c_str());")
                code_lines.append(f"            if ({field_name}_error == DeserializationError::Ok && {field_name}_doc.is<JsonObject>()) {{")
                code_lines.append(f"                // Complex object - add parsed JSON object")
                code_lines.append(f"                doc[\"{field_name}\"] = {field_name}_doc.as<JsonObject>();")
                code_lines.append(f"            }} else {{")
                code_lines.append(f"                // Enum (serialized as plain string like \"Off\" or \"On\") - add directly as string value")
                code_lines.append(f"                // This ensures enums are stored as strings, not integers")
                code_lines.append(f"                doc[\"{field_name}\"] = {field_name}_json.c_str();")
                code_lines.append(f"            }}")
            
            code_lines.append(f"        }} else {{")
            code_lines.append(f"            doc[\"{field_name}\"] = nullptr;")
            code_lines.append(f"        }}")
    
    code_lines.append("")
    code_lines.append("        // Serialize to string")
    code_lines.append("        StdString output;")
    code_lines.append("        serializeJson(doc, output);")
    code_lines.append("")
    code_lines.append("        return StdString(output.c_str());")
    code_lines.append("    }")
    code_lines.append("")
    
    # Always generate validation function (even if empty) so nested objects can call it
    code_lines.append("        // Validation method for all validation macros")
    code_lines.append("        #pragma GCC diagnostic push")
    code_lines.append("        #pragma GCC diagnostic ignored \"-Wunused-parameter\"")
    code_lines.append(f"        Public template<typename DocType>")
    code_lines.append(f"        Static StdString ValidateFields(DocType& doc) {{")
    code_lines.append("        StdString validationErrors;")
    code_lines.append("")
    
    if validation_fields_by_macro:
        all_fields_dict = {field['name']: field for field in fields}
        primitive_types = ['int', 'Int', 'CInt', 'long', 'Long', 'CLong', 'float', 'Float', 'CFloat', 
                          'double', 'Double', 'CDouble', 'bool', 'Bool', 'CBool', 'char', 'Char', 'CChar',
                          'unsigned', 'UInt', 'CUInt', 'short', 'Short', 'CShort']
        
        for macro_name, fields_list in validation_fields_by_macro.items():
            for field in fields_list:
                field_name = field['name']
                field_type = field['type'].strip()
                function_name = field['function_name']
                
                is_nested_object = False
                nested_type = None
                if is_optional_type(field_type):
                    inner_type = extract_inner_type_from_optional(field_type)
                    is_primitive = any(prim in inner_type for prim in primitive_types)
                    is_string = 'StdString' in inner_type or 'CStdString' in inner_type or 'string' in inner_type.lower()
                    if not is_primitive and not is_string:
                        is_nested_object = True
                        nested_type = inner_type
                
                if is_nested_object and nested_type:
                    code_lines.append(f"        // First validate nested object: {field_name}")
                    code_lines.append(f"        if (!doc[\"{field_name}\"].isNull()) {{")
                    code_lines.append(f"            // Extract nested object and convert to JsonDocument for validation")
                    code_lines.append(f"            JsonObject {field_name}_obj = doc[\"{field_name}\"].template as<JsonObject>();")
                    code_lines.append(f"            JsonDocument {field_name}_doc;")
                    code_lines.append(f"            // Copy the JsonObject into JsonDocument")
                    code_lines.append(f"            {field_name}_doc.set({field_name}_obj);")
                    code_lines.append(f"            // Validate nested object's fields")
                    code_lines.append(f"            StdString {field_name}_nested_errors = {nested_type}::ValidateFields({field_name}_doc);")
                    code_lines.append(f"            if (!{field_name}_nested_errors.empty()) {{")
                    code_lines.append(f"                if (!validationErrors.empty()) validationErrors += \",\\n\";")
                    code_lines.append(f"                validationErrors += \"Validation errors in nested object '{field_name}': \";")
                    code_lines.append(f"                validationErrors += {field_name}_nested_errors;")
                    code_lines.append(f"            }}")
                    code_lines.append(f"        }}")
                    code_lines.append(f"")
                
                qualified_function_name = function_name
                if not qualified_function_name.startswith('nayan::'):
                    qualified_function_name = f"nayan::validation::{qualified_function_name}"
                
                code_lines.append(f"        // Validate {macro_name} field: {field_name}")
                code_lines.append(f"        {qualified_function_name}(doc, \"{field_name}\", validationErrors);")
    else:
        code_lines.append("        // No validation macros defined for this class")
    
    code_lines.append("")
    code_lines.append("        return validationErrors;")
    code_lines.append("    }")
    code_lines.append("        #pragma GCC diagnostic pop")
    code_lines.append("")
    
    # Generate static Deserialize() method
    code_lines.append("    // Deserialization method")
    code_lines.append(f"    Public Static {class_name} Deserialize(const StdString& input) {{")
    code_lines.append("        // Create JSON document")
    code_lines.append("        JsonDocument doc;")
    code_lines.append("")
    code_lines.append("        // Deserialize JSON string")
    code_lines.append("        DeserializationError error = deserializeJson(doc, input.c_str());")
    code_lines.append("")
    code_lines.append("        if (error) {")
    code_lines.append("            StdString errorMsg = \"JSON parse error: \";")
    code_lines.append("            errorMsg += error.c_str();")
    code_lines.append("            throw std::runtime_error(errorMsg.c_str());")
    code_lines.append("        }")
    code_lines.append("")
    
    code_lines.append("        // Validate all fields with validation macros")
    code_lines.append("        StdString validationErrors = ValidateFields(doc);")
    code_lines.append("        if (!validationErrors.empty()) {")
    code_lines.append("            throw std::runtime_error(validationErrors.c_str());")
    code_lines.append("        }")
    code_lines.append("")
    
    code_lines.append("        // Create object with default constructor")
    code_lines.append(f"        {class_name} obj;")
    code_lines.append("")
    
    code_lines.append("        // Assign values from JSON if present (only optional fields)")
    primitive_types = ['int', 'Int', 'CInt', 'long', 'Long', 'CLong', 'float', 'Float', 'CFloat', 
                      'double', 'Double', 'CDouble', 'bool', 'Bool', 'CBool', 'char', 'Char', 'CChar',
                      'unsigned', 'UInt', 'CUInt', 'short', 'Short', 'CShort']
    
    optional_fields = [field for field in fields if is_optional_type(field['type'].strip())]
    
    validated_field_names = set()
    for fields_list in validation_fields_by_macro.values():
        for field in fields_list:
            validated_field_names.add(field['name'])
    
    if not optional_fields:
        code_lines.append("        // No optional fields to deserialize")
    else:
        for field in optional_fields:
            field_type = field['type'].strip()
            field_name = field['name']
            is_validated = field_name in validated_field_names
            
            inner_type = extract_inner_type_from_optional(field_type)
            is_primitive = any(prim in inner_type for prim in primitive_types)
            is_string = 'StdString' in inner_type or 'CStdString' in inner_type or 'string' in inner_type.lower()
            
            if is_validated:
                validation_macros = []
                for macro_name, fields_list in validation_fields_by_macro.items():
                    if any(f['name'] == field_name for f in fields_list):
                        validation_macros.append(macro_name)
                validation_desc = "+".join(validation_macros) if validation_macros else "validated"
                code_lines.append(f"        // Deserialize {validation_desc} field: {field_name} (already validated)")
                if is_string:
                    code_lines.append(f"        obj.{field_name} = StdString(doc[\"{field_name}\"].as<const char*>());")
                elif is_primitive:
                    if 'bool' in inner_type.lower() or 'Bool' in inner_type:
                        code_lines.append(f"        obj.{field_name} = doc[\"{field_name}\"].as<bool>();")
                    elif 'int' in inner_type.lower() or 'Int' in inner_type:
                        code_lines.append(f"        obj.{field_name} = doc[\"{field_name}\"].as<int>();")
                    elif 'float' in inner_type.lower() or 'Float' in inner_type:
                        code_lines.append(f"        obj.{field_name} = doc[\"{field_name}\"].as<float>();")
                    elif 'double' in inner_type.lower() or 'Double' in inner_type:
                        code_lines.append(f"        obj.{field_name} = doc[\"{field_name}\"].as<double>();")
                    elif 'char' in inner_type.lower() or 'Char' in inner_type:
                        code_lines.append(f"        obj.{field_name} = doc[\"{field_name}\"].as<char>();")
                    else:
                        code_lines.append(f"        obj.{field_name} = doc[\"{field_name}\"].as<{inner_type}>();")
                else:
                    # For nested object/enum types, use DeserializeValue
                    # Handle both enums (which serialize to strings) and complex objects
                    code_lines.append(f"        // Deserialize nested object or enum: {field_name}")
                    code_lines.append(f"        StdString {field_name}_json;")
                    code_lines.append(f"        if (doc[\"{field_name}\"].is<const char*>()) {{")
                    code_lines.append(f"            // Enum or string value - extract directly")
                    code_lines.append(f"            {field_name}_json = StdString(doc[\"{field_name}\"].as<const char*>());")
                    code_lines.append(f"        }} else {{")
                    code_lines.append(f"            // Complex object - serialize to JSON string")
                    code_lines.append(f"            JsonObject {field_name}_obj = doc[\"{field_name}\"].as<JsonObject>();")
                    code_lines.append(f"            serializeJson({field_name}_obj, {field_name}_json);")
                    code_lines.append(f"        }}")
                    code_lines.append(f"        obj.{field_name} = nayan::serializer::DeserializeValue<{inner_type}>({field_name}_json);")
            else:
                code_lines.append(f"        // Deserialize optional field: {field_name}")
                code_lines.append(f"        if (!doc[\"{field_name}\"].isNull()) {{")
                
                if is_string:
                    code_lines.append(f"            obj.{field_name} = StdString(doc[\"{field_name}\"].as<const char*>());")
                elif is_primitive:
                    if 'bool' in inner_type.lower() or 'Bool' in inner_type:
                        code_lines.append(f"            obj.{field_name} = doc[\"{field_name}\"].as<bool>();")
                    elif 'int' in inner_type.lower() or 'Int' in inner_type:
                        code_lines.append(f"            obj.{field_name} = doc[\"{field_name}\"].as<int>();")
                    elif 'float' in inner_type.lower() or 'Float' in inner_type:
                        code_lines.append(f"            obj.{field_name} = doc[\"{field_name}\"].as<float>();")
                    elif 'double' in inner_type.lower() or 'Double' in inner_type:
                        code_lines.append(f"            obj.{field_name} = doc[\"{field_name}\"].as<double>();")
                    elif 'char' in inner_type.lower() or 'Char' in inner_type:
                        code_lines.append(f"            obj.{field_name} = doc[\"{field_name}\"].as<char>();")
                    else:
                        code_lines.append(f"            obj.{field_name} = doc[\"{field_name}\"].as<{inner_type}>();")
                else:
                    # For nested object/enum types in optional, use DeserializeValue
                    # Handle both enums (which serialize to strings) and complex objects
                    code_lines.append(f"            // Deserialize nested object or enum: {field_name}")
                    code_lines.append(f"            StdString {field_name}_json;")
                    code_lines.append(f"            if (doc[\"{field_name}\"].is<const char*>()) {{")
                    code_lines.append(f"                // Enum or string value - extract directly")
                    code_lines.append(f"                {field_name}_json = StdString(doc[\"{field_name}\"].as<const char*>());")
                    code_lines.append(f"            }} else {{")
                    code_lines.append(f"                // Complex object - serialize to JSON string")
                    code_lines.append(f"                JsonObject {field_name}_obj = doc[\"{field_name}\"].as<JsonObject>();")
                    code_lines.append(f"                serializeJson({field_name}_obj, {field_name}_json);")
                    code_lines.append(f"            }}")
                    code_lines.append(f"            obj.{field_name} = nayan::serializer::DeserializeValue<{inner_type}>({field_name}_json);")
                
                code_lines.append(f"        }}")
    
    code_lines.append("")
    code_lines.append("        return obj;")
    code_lines.append("    }")
    code_lines.append("")
    
    # Always generate primary key methods after serialization methods
    code_lines.append("    // Primary key methods")
    primary_key_methods = generate_primary_key_methods(class_name, id_fields)
    # Split the primary key methods string into lines and append each line
    for line in primary_key_methods.split('\n'):
        code_lines.append(line)
    
    return "\n".join(code_lines)


def mark_dto_annotation_processed(file_path: str, dry_run: bool = False, serializable_annotation: str = "_Entity") -> bool:
    """Replace the /* @Entity */ or /* @Serializable */ annotation with processed marker /*--@Entity--*/ or /*--@Serializable--*/ in a C++ file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        if serializable_annotation == "_Entity":
            annotation_name = "@Entity"
        elif serializable_annotation == "Serializable":
            annotation_name = "@Serializable"
        else:
            annotation_name = "@Serializable"
        
        modified = False
        modified_lines = []
        
        processed_pattern = rf'^/\*--\s*{re.escape(annotation_name)}\s*--\*/\s*$'
        annotation_pattern = rf'^/\*\s*{re.escape(annotation_name)}\s*\*/\s*$'
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            if re.match(processed_pattern, stripped_line):
                modified_lines.append(line)
                continue
            
            if re.match(annotation_pattern, stripped_line):
                if line.startswith(' '):
                    indent = len(line) - len(line.lstrip())
                    if not dry_run:
                        modified_lines.append(' ' * indent + f'/*--{annotation_name}--*/\n')
                    else:
                        modified_lines.append(line)
                else:
                    if not dry_run:
                        modified_lines.append(f'/*--{annotation_name}--*/\n')
                    else:
                        modified_lines.append(line)
                modified = True
            else:
                modified_lines.append(line)
        
        if modified and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(modified_lines)
        
        return True
        
    except FileNotFoundError:
        return False
    except Exception as e:
        return False


def comment_dto_macro(file_path: str, dry_run: bool = False, serializable_macro: str = "_Entity") -> bool:
    """Deprecated: Use mark_dto_annotation_processed instead."""
    return mark_dto_annotation_processed(file_path, dry_run, serializable_macro)


def inject_methods_into_class(file_path: str, class_name: str, methods_code: str, dry_run: bool = False) -> bool:
    """Inject serialization methods into a class before the closing brace."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except Exception as e:
        return False
    
    boundaries = S2_extract_dto_fields.find_class_boundaries(file_path, class_name)
    if not boundaries:
        return False
    start_line, end_line = boundaries
    
    closing_line_idx = end_line - 1
    
    class_content = ''.join(lines[start_line - 1:end_line])
    if 'Serialize()' in class_content and 'Deserialize(' in class_content and 'GetPrimaryKey()' in class_content:
        return True
    
    if dry_run:
        return True
    
    insert_idx = closing_line_idx
    for i in range(closing_line_idx - 1, start_line - 2, -1):
        line = lines[i].strip()
        if line and not line.startswith('//') and not line.startswith('/*'):
            insert_idx = i + 1
            break
    
    methods_lines = methods_code.split('\n')
    indent = "    "
    if insert_idx > 0 and lines[insert_idx - 1]:
        leading_spaces = len(lines[insert_idx - 1]) - len(lines[insert_idx - 1].lstrip())
        if leading_spaces > 0:
            indent = lines[insert_idx - 1][:leading_spaces]
    
    indented_methods = []
    for line in methods_lines:
        if line.strip():
            indented_methods.append(indent + line + '\n')
        else:
            indented_methods.append('\n')
    
    lines[insert_idx:insert_idx] = ['\n'] + indented_methods
    
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)
        return True
    except Exception as e:
        return False


def main():
    """Main function to handle command line arguments and inject serialization methods."""
    parser = argparse.ArgumentParser(
        description="Inject Serialize() and Deserialize() methods into Entity classes"
    )
    parser.add_argument(
        "file_path",
        help="Path to the C++ Entity class file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be injected without modifying the file"
    )
    
    args = parser.parse_args()
    
    dto_info = S1_check_dto_macro.check_dto_macro(args.file_path)
    
    if not dto_info or not dto_info.get('has_dto'):
        return 0
    
    class_name = dto_info.get('class_name')
    if not class_name:
        return 0
    fields = S2_extract_dto_fields.extract_all_fields(args.file_path, class_name)
    
    if not fields:
        pass
    
    optional_fields = [field for field in fields if is_optional_type(field['type'].strip())]
    has_optional_fields = len(optional_fields) > 0
    
    # Extract @Id fields for primary key methods
    try:
        id_fields = extract_id_fields(args.file_path, class_name)
    except Exception:
        id_fields = []
    
    validation_macros = S6_discover_validation_macros.find_validation_macro_definitions(None)
    
    validation_fields_by_macro = S7_extract_validation_fields.extract_validation_fields(
        args.file_path, class_name, validation_macros
    )
    
    methods_code = generate_serialization_methods(class_name, fields, validation_fields_by_macro, id_fields)
    
    if not args.dry_run:
        if has_optional_fields:
            add_include_if_needed(args.file_path, "<optional>")
        
        # Check if we need NayanSerializer.h for SerializeValue/DeserializeValue
        needs_serializer = False
        for field in fields:
            field_type = field['type'].strip()
            if is_optional_type(field_type):
                inner_type = extract_inner_type_from_optional(field_type)
                is_primitive = any(prim in inner_type for prim in ['int', 'Int', 'CInt', 'long', 'Long', 'CLong', 'float', 'Float', 'CFloat', 
                      'double', 'Double', 'CDouble', 'bool', 'Bool', 'CBool', 'char', 'Char', 'CChar',
                      'unsigned', 'UInt', 'CUInt', 'short', 'Short', 'CShort'])
                is_string = 'StdString' in inner_type or 'CStdString' in inner_type or 'string' in inner_type.lower()
                if not is_primitive and not is_string:
                    needs_serializer = True
                    break
        
        if needs_serializer:
            add_include_if_needed(args.file_path, "<NayanSerializer.h>")
    
    success = inject_methods_into_class(args.file_path, class_name, methods_code, dry_run=args.dry_run)
    
    if not success:
        return 1
    
    serializable_annotation = os.environ.get("SERIALIZABLE_MACRO", "_Entity")
    if not args.dry_run:
        mark_dto_annotation_processed(args.file_path, dry_run=False, serializable_annotation=serializable_annotation)
    
    return 0


# Export functions for other scripts to import
__all__ = [
    'check_include_exists',
    'add_include_if_needed',
    'is_optional_type',
    'extract_inner_type_from_optional',
    'generate_serialization_methods',
    'mark_dto_annotation_processed',
    'comment_dto_macro',
    'inject_methods_into_class',
    'main'
]


if __name__ == "__main__":
    exit(main())

