"""
Script to execute client file processing.
This script processes @Entity annotations using local serialization scripts.
"""

import os
import sys
import importlib.util
from pathlib import Path


def execute_scripts(project_dir, library_dir):
    """
    Execute the scripts to process client files.
    Uses local serialization scripts to process @Entity annotations.
    Primary key methods are now generated automatically as part of serialization.
    
    Args:
        project_dir: Path to the client project root (where platformio.ini is)
        library_dir: Path to the library directory
    """
    # Set project_dir in globals so scripts can access it
    globals()['project_dir'] = project_dir
    globals()['library_dir'] = library_dir
    
    # Get serializable macro name from environment or use default
    serializable_macro = os.environ.get("SERIALIZABLE_MACRO", "_Entity")
    globals()['serializable_macro'] = serializable_macro
    
    # Add springbootplusplus_data_scripts to path
    current_file = Path(__file__).resolve()
    springbootplusplus_data_scripts_dir = current_file.parent
    sys.path.insert(0, str(springbootplusplus_data_scripts_dir))
    
    # Run the master serializer script (00_process_serializable_classes.py) from local scripts
    # This now generates both serialization methods AND primary key methods in one pass
    try:
        # Get the serialization directory
        serialization_dir = springbootplusplus_data_scripts_dir / 'springbootplusplus_data_core' / 'serialization'
        
        if serialization_dir.exists():
            serializer_script_path = serialization_dir / '00_process_serializable_classes.py'
            if serializer_script_path.exists():
                try:
                    # Set environment variables so serializer script can access project_dir and library_dir
                    if project_dir:
                        os.environ['PROJECT_DIR'] = project_dir
                        os.environ['CMAKE_PROJECT_DIR'] = project_dir
                    if library_dir:
                        os.environ['LIBRARY_DIR'] = str(library_dir)
                    # Set serializable macro name
                    os.environ['SERIALIZABLE_MACRO'] = serializable_macro
                    
                    # Load and execute the serializer script
                    spec = importlib.util.spec_from_file_location("process_serializable_classes", str(serializer_script_path))
                    serializer_module = importlib.util.module_from_spec(spec)
                    
                    # Add serialization directory to path for imports
                    sys.path.insert(0, str(serialization_dir))
                    
                    # Set __file__ so script_dir can be calculated correctly
                    serializer_module.__dict__['__file__'] = str(serializer_script_path)
                    
                    # Execute the module (this will run the top-level code)
                    spec.loader.exec_module(serializer_module)
                    
                    # Set globals AFTER module execution so they're available to functions
                    serializer_module.__dict__['project_dir'] = project_dir
                    serializer_module.__dict__['library_dir'] = library_dir
                    serializer_module.__dict__['serializable_macro'] = serializable_macro
                    # Also set as attributes so they're accessible
                    serializer_module.project_dir = project_dir
                    serializer_module.library_dir = library_dir
                    serializer_module.serializable_macro = serializable_macro
                    
                    # Call the main function if it exists
                    if hasattr(serializer_module, 'main'):
                        serializer_module.main()
                    elif hasattr(serializer_module, 'process_all_serializable_classes'):
                        serializer_module.process_all_serializable_classes(dry_run=False, serializable_macro=serializable_macro)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
    except Exception as e:
        import traceback
        traceback.print_exc()

