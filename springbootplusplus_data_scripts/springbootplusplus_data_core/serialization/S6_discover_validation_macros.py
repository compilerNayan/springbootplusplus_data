#!/usr/bin/env python3
"""
S6 Discover Validation Macros Script

This script discovers validation macros by scanning for the pattern:
#define MacroName /* Validation Function -> FunctionName */

Returns a dictionary mapping macro names to their validation function names.
"""

import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import get_client_files from local core
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

try:
    from get_client_files import get_client_files
except ImportError:
    get_client_files = None


def find_validation_macro_definitions(search_directories: List[str] = None) -> Dict[str, str]:
    """
    Discover all validation macros by scanning files for the pattern:
    #define MacroName /* Validation Function -> FunctionName */
    
    Args:
        search_directories: List of directories to search (default: uses get_client_files for project_dir and library_dir)
        
    Returns:
        Dictionary mapping macro names to validation function names
    """
    validation_macros = {}
    
    pattern = r'^[^/]*#define\s+(\w+)\s+/\*\s*Validation\s+Function\s*->\s*([^\*]+?)\s*\*/'
    
    header_files = []
    
    if search_directories is None:
        if get_client_files is not None:
            project_dir = os.environ.get('PROJECT_DIR') or os.environ.get('CMAKE_PROJECT_DIR')
            library_dir = os.environ.get('LIBRARY_DIR')
            
            if not project_dir and 'project_dir' in globals():
                project_dir = globals()['project_dir']
            if not library_dir and 'library_dir' in globals():
                library_dir = globals()['library_dir']
            
            if project_dir:
                try:
                    project_header_files = get_client_files(project_dir, file_extensions=['.h', '.hpp'])
                    header_files.extend(project_header_files)
                except Exception as e:
                    pass
            if library_dir:
                try:
                    library_files = get_client_files(library_dir, skip_exclusions=True)
                    library_header_files = [f for f in library_files if f.endswith(('.h', '.hpp'))]
                    header_files.extend(library_header_files)
                except Exception as e:
                    pass
            search_directories = []
        else:
            if 'client_files' in globals():
                header_files = [f for f in globals()['client_files'] if f.endswith(('.h', '.hpp'))]
                search_directories = []
    
    if header_files:
        for file_path in header_files:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('//'):
                        continue
                    
                    if '//' in line:
                        comment_pos = line.find('//')
                        define_pos = line.find('#define')
                        if define_pos != -1 and comment_pos != -1 and comment_pos < define_pos:
                            continue
                    
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        macro_name = match.group(1).strip()
                        function_name = match.group(2).strip()
                        validation_macros[macro_name] = function_name
                        
            except Exception as e:
                continue
    
    if search_directories:
        for search_dir in search_directories:
            if not os.path.exists(search_dir):
                continue
                
            for root, dirs, files in os.walk(search_dir):
                if 'build' in root or 'tempcode' in root or '.git' in root:
                    continue
                    
                for file in files:
                    if file.endswith(('.h', '.hpp')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                
                            for line in lines:
                                stripped = line.strip()
                                if stripped.startswith('//'):
                                    continue
                                
                                if '//' in line:
                                    comment_pos = line.find('//')
                                    define_pos = line.find('#define')
                                    if define_pos != -1 and comment_pos != -1 and comment_pos < define_pos:
                                        continue
                                
                                match = re.search(pattern, line, re.IGNORECASE)
                                if match:
                                    macro_name = match.group(1).strip()
                                    function_name = match.group(2).strip()
                                    validation_macros[macro_name] = function_name
                                
                        except Exception as e:
                            continue
    
    return validation_macros


def extract_validation_macros_from_file(file_path: str) -> Dict[str, str]:
    """Extract validation macro definitions from a specific file."""
    validation_macros = {}
    
    if not os.path.exists(file_path):
        return validation_macros
    
    pattern = r'#define\s+(\w+)\s+/\*\s*Validation\s+Function\s*->\s*([^\*]+?)\s*\*/'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            
            if '//' in line:
                comment_pos = line.find('//')
                define_pos = line.find('#define')
                if define_pos != -1 and comment_pos != -1 and comment_pos < define_pos:
                    continue
            
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                macro_name = match.group(1).strip()
                function_name = match.group(2).strip()
                validation_macros[macro_name] = function_name
            
    except Exception as e:
        pass
    
    return validation_macros


def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Discover validation macros from source files"
    )
    parser.add_argument(
        "--search-dirs",
        nargs="+",
        help="Directories to search for validation macro definitions"
    )
    parser.add_argument(
        "--file",
        help="Specific file to scan for validation macros"
    )
    
    args = parser.parse_args()
    
    if args.file:
        macros = extract_validation_macros_from_file(args.file)
    else:
        search_dirs = args.search_dirs if args.search_dirs else None
        macros = find_validation_macro_definitions(search_dirs)
    
    return 0


# Export functions for other scripts to import
__all__ = [
    'find_validation_macro_definitions',
    'extract_validation_macros_from_file',
    'main'
]


if __name__ == "__main__":
    exit(main())

