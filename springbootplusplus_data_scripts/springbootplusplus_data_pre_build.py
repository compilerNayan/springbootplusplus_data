# Import required modules first
import sys
import os
from pathlib import Path

# Print message immediately when script is loaded
# print("=" * 60)
# print("springbootplusplus_data pre-build script STARTING")
# print("=" * 60)
# __file__ may not be available in PlatformIO SCons context
try:
    script_location = __file__
except NameError:
    script_location = "unknown (running in PlatformIO SCons context)"
# print(f"Script location: {script_location}")
# print(f"Current working directory: {os.getcwd()}")
# print("=" * 60)

# Import PlatformIO environment first (if available)
env = None
try:
    Import("env")
    # print("✓ PlatformIO environment detected")
except NameError:
    # Not running in PlatformIO environment (e.g., running from CMake)
    # print("Note: Not running in PlatformIO environment - some features may be limited")
    # Create a mock env object for CMake builds
    class MockEnv:
        def get(self, key, default=None):
            return default
        def __contains__(self, key):
            return False
        def __getitem__(self, key):
            raise KeyError(key)
    env = MockEnv()
except Exception as e:
    # print(f"Note: Could not import PlatformIO env: {e}")
    import traceback
    traceback.print_exc()
    class MockEnv:
        def get(self, key, default=None):
            return default
        def __contains__(self, key):
            return False
        def __getitem__(self, key):
            raise KeyError(key)
    env = MockEnv()


def get_library_dir():
    """
    Find the springbootplusplus_data_scripts directory by searching up the directory tree.
    
    Returns:
        Path: Path to the springbootplusplus_data_scripts directory
        
    Raises:
        ImportError: If the directory cannot be found
    """
    # Try to use __file__ if available, otherwise search from current directory
    search_start = None
    try:
        # __file__ may not be available in PlatformIO SCons context
        if '__file__' in globals():
            search_start = Path(__file__).parent
    except NameError:
        pass
    
    # Start search from current working directory or script location
    if search_start and search_start.exists():
        current = search_start
    else:
        current = Path(os.getcwd())
    
    # Search up the directory tree
    for _ in range(15):  # Search up to 15 levels
        potential = current / "springbootplusplus_data_scripts"
        if potential.exists() and potential.is_dir():
            # print(f"✓ Found library path by searching up directory tree: {potential}")
            return potential
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    raise ImportError("Could not find springbootplusplus_data_scripts directory")


def get_current_library_path(project_dir=None):
    """
    Get the full path of the current library (springbootplusplus_data) when included in a client project.
    
    This function finds the library by:
    1. Checking if we're in a CMake FetchContent location (build/_deps/springbootplusplus_data-src)
    2. Checking if we're in a PlatformIO location (.pio/libdeps/)
    3. Using get_library_dir() and getting its parent
    
    Args:
        project_dir: Optional project directory. If None, tries to get from environment.
    
    Returns:
        Path: Full path to the springbootplusplus_data library root directory, or None if not found
    """
    # Get project directory if not provided
    if project_dir is None:
        project_dir = os.environ.get("CMAKE_PROJECT_DIR") or os.environ.get("PROJECT_DIR")
    
    # First, try to get library scripts directory
    try:
        library_scripts_dir = get_library_dir()
        library_root = library_scripts_dir.parent
        
        # If we're in a CMake FetchContent location, return the resolved path
        if "springbootplusplus_data-src" in str(library_root) or "_deps" in str(library_root):
            return library_root.resolve()
        
        # Otherwise, return the parent of scripts directory
        return library_root.resolve()
    except ImportError:
        pass
    
    # Try to find from project directory's build/_deps
    if project_dir:
        project_path = Path(project_dir)
        build_deps = project_path / "build" / "_deps" / "springbootplusplus_data-src"
        if build_deps.exists() and build_deps.is_dir():
            # print(f"✓ Found springbootplusplus_data library path (CMake from project): {build_deps}")
            return build_deps.resolve()
    
    # Try to find from current working directory's build/_deps
    cwd = Path(os.getcwd())
    if cwd.name == "build" or "_deps" in str(cwd):
        deps_dir = cwd / "_deps" / "springbootplusplus_data-src"
        if deps_dir.exists() and deps_dir.is_dir():
            # print(f"✓ Found springbootplusplus_data library path (CMake from CWD): {deps_dir}")
            return deps_dir.resolve()
    
    # Try PlatformIO location
    current = cwd.resolve()
    for _ in range(10):
        pio_path = current / ".pio" / "libdeps"
        if pio_path.exists() and pio_path.is_dir():
            for env_dir in pio_path.iterdir():
                if env_dir.is_dir():
                    for lib_dir in env_dir.iterdir():
                        if lib_dir.is_dir() and "springbootplusplus_data" in lib_dir.name.lower():
                            # print(f"✓ Found springbootplusplus_data library path (PlatformIO): {lib_dir}")
                            return lib_dir.resolve()
        
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # print("Warning: Could not determine current library (springbootplusplus_data) path")
    return None


def get_all_library_dirs(project_dir=None):
    """
    Get all library directories (both scripts directories and root directories).
    
    This function discovers all library directories by:
    1. Checking CMake FetchContent locations (build/_deps/)
    2. Checking PlatformIO library locations (.pio/libdeps/)
    3. Checking current directory and parent directories
    
    Args:
        project_dir: Optional project directory to search from. If None, uses get_project_dir()
    
    Returns:
        Dictionary with:
        - 'scripts_dirs': List of paths to library scripts directories (e.g., arduinolib1_scripts)
        - 'root_dirs': List of paths to library root directories (e.g., arduinolib1-src)
        - 'by_name': Dictionary mapping library names to their root directories
    """
    if project_dir is None:
        project_dir = get_project_dir()
    
    scripts_dirs = []
    root_dirs = []
    by_name = {}
    
    search_paths = []
    
    # Add current working directory
    search_paths.append(Path(os.getcwd()))
    
    # Add project directory if available
    if project_dir:
        project_path = Path(project_dir)
        search_paths.append(project_path)
        
        # Check CMake FetchContent location: build/_deps/
        build_deps = project_path / "build" / "_deps"
        if build_deps.exists() and build_deps.is_dir():
            # Find all library directories in _deps
            for lib_dir in build_deps.iterdir():
                if lib_dir.is_dir() and lib_dir.name.endswith("-src"):
                    lib_root = lib_dir.resolve()
                    root_dirs.append(lib_root)
                    
                    # Extract library name (e.g., "arduinolib1-src" -> "arduinolib1")
                    lib_name = lib_dir.name[:-4]  # Remove "-src" suffix
                    by_name[lib_name] = lib_root
                    
                    # Check for scripts directory
                    scripts_dir = lib_root / f"{lib_name}_scripts"
                    if scripts_dir.exists() and scripts_dir.is_dir():
                        scripts_dirs.append(scripts_dir.resolve())
    
    # Add library directory (parent of springbootplusplus_data_scripts)
    try:
        library_scripts_dir = get_library_dir()
        library_dir = library_scripts_dir.parent
        search_paths.append(library_dir)
        
        # If we're in a CMake build, check sibling directories in _deps
        if "springbootplusplus_data-src" in str(library_dir) or "_deps" in str(library_dir):
            parent_deps = library_dir.parent
            if parent_deps.exists() and parent_deps.name == "_deps":
                # Find all library directories in _deps
                for lib_dir in parent_deps.iterdir():
                    if lib_dir.is_dir() and lib_dir.name.endswith("-src"):
                        lib_root = lib_dir.resolve()
                        if lib_root not in root_dirs:
                            root_dirs.append(lib_root)
                            
                            # Extract library name
                            lib_name = lib_dir.name[:-4]  # Remove "-src" suffix
                            if lib_name not in by_name:
                                by_name[lib_name] = lib_root
                            
                            # Check for scripts directory
                            scripts_dir = lib_root / f"{lib_name}_scripts"
                            if scripts_dir.exists() and scripts_dir.is_dir():
                                scripts_dirs.append(scripts_dir.resolve())
    except ImportError:
        pass
    
    # Search in each path for PlatformIO libraries
    for start_path in search_paths:
        current = start_path.resolve()
        for _ in range(10):  # Search up to 10 levels
            # Check in .pio/libdeps/ (PlatformIO location)
            # Structure: .pio/libdeps/<env>/<library_name>/
            pio_path = current / ".pio" / "libdeps"
            if pio_path.exists() and pio_path.is_dir():
                # Iterate through environment directories (e.g., esp32dev, native, etc.)
                for env_dir in pio_path.iterdir():
                    if env_dir.is_dir():
                        # Now iterate through libraries in this environment
                        for lib_dir in env_dir.iterdir():
                            if lib_dir.is_dir():
                                lib_root = lib_dir.resolve()
                                if lib_root not in root_dirs:
                                    root_dirs.append(lib_root)
                                    
                                    # Try to extract library name from directory name
                                    lib_name = lib_dir.name
                                    # Use library name as key (may have duplicates across envs, but that's okay)
                                    if lib_name not in by_name:
                                        by_name[lib_name] = lib_root
                                    
                                    # Check for scripts directory (various naming patterns)
                                    possible_scripts_names = [
                                        f"{lib_name}_scripts",
                                        f"{lib_name.replace('-', '')}_scripts",
                                        "scripts"
                                    ]
                                    for scripts_name in possible_scripts_names:
                                        scripts_dir = lib_root / scripts_name
                                        if scripts_dir.exists() and scripts_dir.is_dir():
                                            if scripts_dir.resolve() not in scripts_dirs:
                                                scripts_dirs.append(scripts_dir.resolve())
                                            break
            
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent
    
    return {
        'scripts_dirs': scripts_dirs,
        'root_dirs': root_dirs,
        'by_name': by_name
    }


def get_project_dir():
    """
    Get the project directory from PlatformIO environment or CMake environment.
    
    Returns:
        str: Path to the project directory, or None if not found
    """
    # Try PlatformIO environment first (simpler approach like springbootplusplus-web)
    project_dir = None
    if env:
        try:
            project_dir = env.get("PROJECT_DIR", None)
            if project_dir:
                # print(f"✓ Found PROJECT_DIR from PlatformIO env: {project_dir}")
                pass
        except (AttributeError, TypeError, KeyError) as e:
            # print(f"Note: Could not access PROJECT_DIR from env: {e}")
            pass
    
    # If not found, try CMake environment variable
    if not project_dir:
        project_dir = os.environ.get("CMAKE_PROJECT_DIR", None)
        if project_dir:
            # print(f"✓ Found PROJECT_DIR from CMAKE_PROJECT_DIR env var: {project_dir}")
            pass
    
    # If still not found, try searching for platformio.ini file
    # This is important for PlatformIO when script runs from library directory
    if not project_dir:
        # print("Searching for platformio.ini file...")
        current = Path(os.getcwd()).resolve()
        # print(f"Starting search from: {current}")
        for i in range(15):  # Search up to 15 levels
            platformio_ini = current / "platformio.ini"
            if platformio_ini.exists() and platformio_ini.is_file():
                project_dir = str(current)
                # print(f"✓ Found project directory by searching for platformio.ini: {project_dir}")
                break
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent
            if i == 14:
                # print(f"⚠️  Reached max search depth without finding platformio.ini")
                pass
    
    if project_dir:
        # print(f"\n✓ Client project directory: {project_dir}")
        pass
    else:
        # print("⚠️  Warning: Could not determine PROJECT_DIR from environment or by searching")
        # print(f"   Current working directory: {os.getcwd()}")
        pass
    return project_dir


# Get library scripts directory and add it to Python path
library_scripts_dir = get_library_dir()
sys.path.insert(0, str(library_scripts_dir))

# Set serializable macro name to _Entity (for //@Entity annotation)
# Using _Entity (with underscore) to match the default expected by execute_scripts
os.environ['SERIALIZABLE_MACRO'] = '_Entity'

# Get project directory
project_dir = get_project_dir()

# Get current library root directory (full path of springbootplusplus_data when included in client)
library_dir = get_current_library_path(project_dir)
if library_dir is None:
    # Fallback to parent of scripts directory
    library_dir = library_scripts_dir.parent
    # print(f"Using fallback library directory: {library_dir}")
else:
    # print(f"Current library (springbootplusplus_data) path: {library_dir}")
    pass

# Print the library path with the requested message
# print(f"Hello cuckoo, this is the library full path: {library_dir}")

# Debug: Print current working directory
# print(f"Current working directory: {os.getcwd()}")

# Get all library directories and print source files from all libraries
# print(f"\n{'=' * 60}")
# print("📚 Listing source files from all libraries...")
# print(f"{'=' * 60}")

try:
    # Try to import get_client_files from local core
    try:
        from springbootplusplus_data_core.get_client_files import get_client_files
        HAS_GET_CLIENT_FILES = True
    except ImportError:
        HAS_GET_CLIENT_FILES = False
    
    # Get all library directories
    all_libs = get_all_library_dirs(project_dir)
    
    if all_libs and all_libs.get('root_dirs'):
        # print(f"\nFound {len(all_libs['root_dirs'])} library directory(ies):")
        # for lib_name, lib_dir in sorted(all_libs['by_name'].items()):
        #     print(f"   - {lib_name}: {lib_dir}")
        
        # Collect and print source files from each library (only .h files, exclude arduinojson)
        # Also collect files from the client project
        all_header_files = []
        if HAS_GET_CLIENT_FILES:
            # print(f"\n📄 Header files (.h) in all libraries (excluding arduinojson):")
            # print("=" * 60)
            for lib_name, lib_dir in sorted(all_libs['by_name'].items()):
                # Skip arduinojson library
                if "arduinojson" in lib_name.lower():
                    continue
                
                # Get only .h files
                lib_files = get_client_files(str(lib_dir), skip_exclusions=True, file_extensions=['.h'])
                if lib_files:
                    # print(f"\n{lib_name} ({len(lib_files)} .h file(s)):")
                    # for file_path in lib_files[:20]:  # Limit to first 20 files per library
                    #     print(f"   {file_path}")
                    # if len(lib_files) > 20:
                    #     print(f"   ... and {len(lib_files) - 20} more files")
                    
                    # Collect all files (not just first 20) for processing
                    all_header_files.extend(lib_files)
            
            # Also collect header files from the client project
            if project_dir:
                try:
                    client_files = get_client_files(project_dir, skip_exclusions=True, file_extensions=['.h'])
                    if client_files:
                        # print(f"\nClient Project ({len(client_files)} .h file(s)):")
                        # for file_path in client_files[:20]:  # Limit to first 20 files
                        #     print(f"   {file_path}")
                        # if len(client_files) > 20:
                        #     print(f"   ... and {len(client_files) - 20} more files")
                        
                        # Collect all client files for processing
                        all_header_files.extend(client_files)
                except Exception as e:
                    # print(f"⚠️  Warning: Could not get client files from {project_dir}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # print("⚠️  Warning: No project directory found, skipping client files")
                pass
            
            # print("=" * 60)
            
            # Process each header file with implement_repository script
            if all_header_files:
                # print(f"\n{'=' * 60}")
                # print(f"🔧 Processing {len(all_header_files)} header file(s) for repository implementation...")
                # print(f"{'=' * 60}\n")
                # print(f"Library directory: {library_dir}")
                # print(f"Project directory: {project_dir}")
                pass
                
                try:
                    # Import process_repository module
                    # __file__ may not be available in PlatformIO SCons context
                    try:
                        current_file = Path(__file__).resolve()
                        springbootplusplus_data_scripts_dir = current_file.parent
                    except NameError:
                        # Fallback: use library_scripts_dir that we already found
                        springbootplusplus_data_scripts_dir = library_scripts_dir
                    sys.path.insert(0, str(springbootplusplus_data_scripts_dir))
                    
                    from springbootplusplus_data_core.repository.process_repository import process_repository
                    
                    processed_count = 0
                    implemented_count = 0
                    
                    for file_path in all_header_files:
                        try:
                            # Process file for repository implementation
                            # This will detect @Repository annotation, create impl file, and add include
                            result = process_repository(str(file_path), str(library_dir), dry_run=False)
                            if result:
                                # print(f"  ✓ Repository implementation generated for: {file_path}")
                                implemented_count += 1
                            else:
                                # print(f"  - No repository found in: {file_path}")
                                pass
                            processed_count += 1
                        except Exception as e:
                            # print(f"⚠️  Warning: Error processing {file_path}: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # print(f"\n✅ Processed {processed_count} file(s), implemented {implemented_count} repository(ies)")
                    
                except ImportError as e:
                    # print(f"⚠️  Warning: Could not import implement_repository: {e}")
                    import traceback
                    traceback.print_exc()
                except Exception as e:
                    # print(f"⚠️  Error processing files for repository implementation: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            # print("\n⚠️  Could not import get_client_files to list source files")
            pass
    else:
        # print("\n⚠️  No library directories found")
        pass
        
except Exception as e:
    # print(f"\n⚠️  Error listing library files: {e}")
    import traceback
    traceback.print_exc()

# Import and execute scripts
try:
    # print(f"\n{'=' * 60}")
    # print("Importing and executing scripts...")
    # print(f"{'=' * 60}")
    from springbootplusplus_data_execute_scripts import execute_scripts
    execute_scripts(project_dir, library_dir)
except ImportError as e:
    # print(f"⚠️  Error importing execute_scripts: {e}")
    import traceback
    traceback.print_exc()
    # print(f"Python path: {sys.path}")
except Exception as e:
    # print(f"⚠️  Error executing scripts: {e}")
    import traceback
    traceback.print_exc()

# print("\n" + "=" * 60)
# print("springbootplusplus_data pre-build script completed")
# print("=" * 60)

