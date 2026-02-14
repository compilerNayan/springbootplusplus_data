#!/usr/bin/env python3
"""
Script to implement repository classes.

Uses detect_repository to check if a file has @Repository annotation.
If it exists, creates a <class-name>Impl.h file in src/repository folder.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, str(script_dir))

from detect_repository import detect_repository
from generate_repository_implementation import generate_repository_implementation


def generate_impl_class(class_name: str, entity_type: str, id_type: str, source_file_path: str, is_templated: bool = True) -> str:
    """
    Generate the implementation class code.
    
    Args:
        class_name: Name of the repository class
        entity_type: Entity type (first template parameter or concrete type)
        id_type: ID type (second template parameter or concrete type)
        source_file_path: Absolute path to the source file containing the repository
        is_templated: Whether the repository class is templated
        
    Returns:
        String containing the complete class implementation
    """
    impl_class_name = f"{class_name}Impl"
    header_guard = f"_{impl_class_name.upper()}_H_"
    
    # Use the absolute path of the source file for the include
    source_path = Path(source_file_path).resolve()
    include_path = str(source_path)
    
    repository_ptr = f"{class_name}Ptr"
    
    # Generate base method implementations that delegate to CpaRepositoryImpl
    if is_templated:
        # Templated repository: use template parameters
        base_method_implementations = f"""    Public Virtual Entity Save(Entity& entity) override {{
        return CpaRepositoryImpl<Entity, ID>::Save(entity);
    }}

    Public Virtual optional<Entity> FindById(ID id) override {{
        return CpaRepositoryImpl<Entity, ID>::FindById(id);
    }}

    Public Virtual StdVector<Entity> FindAll() override {{
        return CpaRepositoryImpl<Entity, ID>::FindAll();
    }}

    Public Virtual Entity Update(Entity& entity) override {{
        return CpaRepositoryImpl<Entity, ID>::Update(entity);
    }}

    Public Virtual Void DeleteById(ID id) override {{
        CpaRepositoryImpl<Entity, ID>::DeleteById(id);
    }}

    Public Virtual Void Delete(Entity& entity) override {{
        CpaRepositoryImpl<Entity, ID>::Delete(entity);
    }}

    Public Virtual Bool ExistsById(ID id) override {{
        return CpaRepositoryImpl<Entity, ID>::ExistsById(id);
    }}"""
        
        # Generate custom method implementations (FindBy, DeleteBy, etc.)
        custom_method_implementations = None
        try:
            if os.path.exists(source_file_path):
                custom_method_implementations = generate_repository_implementation(source_file_path)
        except Exception as e:
            # If custom method generation fails, continue with base methods only
            # print(f"Warning: Could not generate custom methods: {e}", file=sys.stderr)
            pass
        
        if custom_method_implementations:
            # Add custom methods after base methods
            method_implementations = base_method_implementations + "\n\n" + custom_method_implementations
        else:
            method_implementations = base_method_implementations
        
        # Add GetInstance and template specializations
        method_implementations += f"""

    Public Static {repository_ptr} GetInstance() {{
        static {repository_ptr} instance(new {impl_class_name}<Entity, ID>());
        return instance;
    }}

}};

template <typename Entity, typename ID>
struct Implementation<{class_name}<Entity, ID>> {{
    using type = {impl_class_name}<Entity, ID>;
}};

template <typename Entity, typename ID>
struct Implementation<{class_name}<Entity, ID>*> {{
    using type = {impl_class_name}<Entity, ID>*;
}};
"""
        code = f"""#ifndef {header_guard}
#define {header_guard}

#include "CpaRepositoryImpl.h"

template<typename Entity, typename ID>
class {impl_class_name} : public {class_name}<Entity, ID>, public CpaRepositoryImpl<Entity, ID> {{
    Public Virtual ~{impl_class_name}() = default;
{method_implementations}
#endif // {header_guard}
"""
    else:
        # Non-templated repository: use concrete types
        base_method_implementations = f"""    Public Virtual {entity_type} Save({entity_type}& entity) override {{
        return CpaRepositoryImpl<{entity_type}, {id_type}>::Save(entity);
    }}

    Public Virtual optional<{entity_type}> FindById({id_type} id) override {{
        return CpaRepositoryImpl<{entity_type}, {id_type}>::FindById(id);
    }}

    Public Virtual StdVector<{entity_type}> FindAll() override {{
        return CpaRepositoryImpl<{entity_type}, {id_type}>::FindAll();
    }}

    Public Virtual {entity_type} Update({entity_type}& entity) override {{
        return CpaRepositoryImpl<{entity_type}, {id_type}>::Update(entity);
    }}

    Public Virtual Void DeleteById({id_type} id) override {{
        CpaRepositoryImpl<{entity_type}, {id_type}>::DeleteById(id);
    }}

    Public Virtual Void Delete({entity_type}& entity) override {{
        CpaRepositoryImpl<{entity_type}, {id_type}>::Delete(entity);
    }}

    Public Virtual Bool ExistsById({id_type} id) override {{
        return CpaRepositoryImpl<{entity_type}, {id_type}>::ExistsById(id);
    }}"""
        
        # Generate custom method implementations (FindBy, DeleteBy, etc.)
        custom_method_implementations = None
        try:
            if os.path.exists(source_file_path):
                custom_method_implementations = generate_repository_implementation(source_file_path)
        except Exception as e:
            # If custom method generation fails, continue with base methods only
            # print(f"Warning: Could not generate custom methods: {e}", file=sys.stderr)
            pass
        
        if custom_method_implementations:
            # Add custom methods after base methods
            method_implementations = base_method_implementations + "\n\n" + custom_method_implementations
        else:
            method_implementations = base_method_implementations
        
        # Add GetInstance and template specializations
        method_implementations += f"""

    Public Static {repository_ptr} GetInstance() {{
        static {repository_ptr} instance(new {impl_class_name}());
        return instance;
    }}

}};

template <>
struct Implementation<{class_name}> {{
    using type = {impl_class_name};
}};

template <>
struct Implementation<{class_name}*> {{
    using type = {impl_class_name}*;
}};
"""
        code = f"""#ifndef {header_guard}
#define {header_guard}

#include "CpaRepositoryImpl.h"

class {impl_class_name} : public {class_name}, public CpaRepositoryImpl<{entity_type}, {id_type}> {{
    Public Virtual ~{impl_class_name}() = default;
{method_implementations}
#endif // {header_guard}
"""
    return code


def implement_repository(file_path: str, library_dir: str, dry_run: bool = False, repository_info: Optional[Tuple[str, str, str, bool]] = None) -> bool:
    """
    Implement a repository class if @Repository annotation is found.
    
    Args:
        file_path: Path to the source file to check
        library_dir: Path to the library directory (where src/repository folder should be)
        dry_run: If True, don't actually create the file
        repository_info: Optional pre-extracted repository info tuple (class_name, entity_type, id_type, is_templated)
                       If provided, skips detection step
        
    Returns:
        True if implementation was created or would be created, False otherwise
    """
    # Use provided info or detect repository in the file
    if repository_info:
        result = repository_info
    else:
        result = detect_repository(file_path)
    
    if not result:
        return False
    
    if len(result) == 4:
        class_name, entity_type, id_type, is_templated = result
    else:
        # Backward compatibility: assume templated if not specified
        class_name, entity_type, id_type = result
        is_templated = True
    
    # Create repository directory if it doesn't exist
    repository_dir = Path(library_dir) / "src" / "repository"
    repository_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate implementation file name
    impl_file_name = f"{class_name}Impl.h"
    impl_file_path = repository_dir / impl_file_name
    
    # Check if file already exists
    if impl_file_path.exists():
        # print(f"⚠️  Implementation file already exists: {impl_file_path}")
        return False
    
    # Generate the implementation class code
    impl_code = generate_impl_class(class_name, entity_type, id_type, file_path, is_templated)
    
    if dry_run:
        # print(f"Would create implementation file: {impl_file_path}")
        # print("=" * 60)
        # print(impl_code)
        # print("=" * 60)
        return True
    
    # Write the implementation file
    try:
        with open(impl_file_path, 'w', encoding='utf-8') as f:
            f.write(impl_code)
        # print(f"✓ Created implementation file: {impl_file_path}")
        return True
    except Exception as e:
        # print(f"Error creating implementation file: {e}")
        return False


def process_file(file_path: str, library_dir: str, dry_run: bool = False) -> bool:
    """
    Process a file and implement repository if @Repository annotation is found.
    
    Args:
        file_path: Path to the source file
        library_dir: Path to the library directory
        dry_run: If True, don't actually create files
        
    Returns:
        True if repository was implemented, False otherwise
    """
    return implement_repository(file_path, library_dir, dry_run)


def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Implement repository classes for files with @Repository annotation"
    )
    parser.add_argument(
        "file_path",
        help="Path to the C++ file to check"
    )
    parser.add_argument(
        "--library-dir",
        required=True,
        help="Path to the library directory (where src/repository folder should be)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating files"
    )
    
    args = parser.parse_args()
    
    success = process_file(args.file_path, args.library_dir, args.dry_run)
    
    return 0 if success else 1


# Export functions for other scripts to import
__all__ = [
    'generate_impl_class',
    'implement_repository',
    'process_file',
    'main'
]


if __name__ == "__main__":
    exit(main())

