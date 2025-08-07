"""
Security module for plugin import restrictions.

This module provides custom import hooks to prevent malicious plugins from
importing dangerous Python modules that could compromise system security.
"""

import sys
import importlib.util
from typing import Set, Optional, Any
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec


class SecurityError(Exception):
    """Raised when a plugin attempts to import a restricted module."""
    pass


class SecureImporter(MetaPathFinder, Loader):
    """Custom import hook that restricts module imports for plugin security."""
    
    # Whitelist of allowed standard library modules
    ALLOWED_MODULES = {
        # Basic Python types and utilities
        'typing', 'collections', 'itertools', 'functools', 'operator',
        'copy', 'deepcopy', 'dataclasses', 'enum', 'abc',
        
        # String and text processing
        'string', 're', 'unicodedata', 'textwrap',
        
        # Math and numbers
        'math', 'decimal', 'fractions', 'random', 'statistics',
        
        # Date and time
        'datetime', 'time', 'calendar',
        
        # Data structures
        'heapq', 'bisect', 'weakref',
        
        # File formats and parsing (safe ones)
        'json', 'csv', 'configparser', 'html', 'xml.etree.ElementTree',
        
        # Encoding and hashing (limited)
        'base64', 'hashlib', 'hmac', 'secrets',
        
        # Logging (controlled)
        'logging',
        
        # HTTP clients (we'll control this through PluginApi)
        # 'urllib', 'requests' - intentionally excluded, use PluginApi methods
        
        # Yoix-specific modules
        'yoix.pm', 'yoix.pm.api',
        
        # Third-party safe modules (commonly used for content processing)
        'mistune', 'python_slugify', 'frontmatter', 'pybars3',
    }
    
    # Explicitly blocked dangerous modules
    BLOCKED_MODULES = {
        # System and OS interaction
        'os', 'sys', 'subprocess', 'shutil', 'glob', 'pathlib',
        'tempfile', 'fileinput', 'stat', 'statvfs', 'platform',
        
        # Network and communication
        'socket', 'ssl', 'http', 'urllib', 'requests', 'ftplib',
        'smtplib', 'poplib', 'imaplib', 'telnetlib', 'socketserver',
        
        # Process and thread management
        'threading', 'multiprocessing', 'concurrent', 'asyncio',
        'signal', 'resource', 'ctypes',
        
        # File system and I/O
        'io', 'filecmp', 'linecache', 'shlex',
        
        # Database access
        'sqlite3', 'dbm',
        
        # Compression and archives
        'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma',
        
        # Debugging and introspection
        'pdb', 'trace', 'traceback', 'inspect', 'dis',
        
        # Import system manipulation
        'importlib', 'pkgutil', 'modulefinder',
        
        # Code execution
        'code', 'codeop', 'compile', 'eval', 'exec',
    }
    
    def __init__(self):
        """Initialize the secure importer."""
        self.original_meta_path = None
        self.plugin_mode = False
        
    def enable_plugin_mode(self):
        """Enable plugin security mode - install import restrictions."""
        if not self.plugin_mode:
            self.original_meta_path = sys.meta_path.copy()
            # Insert ourselves at the beginning of meta_path to catch imports first
            sys.meta_path.insert(0, self)
            self.plugin_mode = True
            
    def disable_plugin_mode(self):
        """Disable plugin security mode - restore normal imports."""
        if self.plugin_mode:
            try:
                sys.meta_path.remove(self)
            except ValueError:
                pass
            self.plugin_mode = False
            
    def find_spec(self, fullname: str, path: Optional[Any] = None, target: Optional[Any] = None) -> Optional[ModuleSpec]:
        """Find module spec with security filtering.
        
        Args:
            fullname: Full module name being imported
            path: Module path
            target: Target module
            
        Returns:
            ModuleSpec if allowed, None to defer to other finders
            
        Raises:
            SecurityError: If module is explicitly blocked
        """
        if not self.plugin_mode:
            return None
            
        # Check if module is explicitly blocked
        if self._is_blocked_module(fullname):
            raise SecurityError(f"Import of module '{fullname}' is not allowed in plugins")
            
        # Check if module is in whitelist
        if self._is_allowed_module(fullname):
            # Let the normal import system handle whitelisted modules
            return None
            
        # For unknown modules, block them by default
        raise SecurityError(f"Import of module '{fullname}' is not allowed in plugins (not in whitelist)")
        
    def _is_blocked_module(self, fullname: str) -> bool:
        """Check if a module is explicitly blocked."""
        # Check exact match and parent modules
        parts = fullname.split('.')
        for i in range(len(parts)):
            partial_name = '.'.join(parts[:i+1])
            if partial_name in self.BLOCKED_MODULES:
                return True
        return False
        
    def _is_allowed_module(self, fullname: str) -> bool:
        """Check if a module is in the whitelist."""
        # Check exact match
        if fullname in self.ALLOWED_MODULES:
            return True
            
        # Check if it's a submodule of an allowed module
        for allowed in self.ALLOWED_MODULES:
            if fullname.startswith(allowed + '.'):
                return True
                
        return False
        
    def create_module(self, spec: ModuleSpec) -> Optional[Any]:
        """Create module - not used, defer to default implementation."""
        return None
        
    def exec_module(self, module: Any) -> None:
        """Execute module - not used, defer to default implementation."""
        pass


# Global secure importer instance
_secure_importer = SecureImporter()


def enable_plugin_security():
    """Enable plugin import security restrictions."""
    _secure_importer.enable_plugin_mode()
    

def disable_plugin_security():
    """Disable plugin import security restrictions."""
    _secure_importer.disable_plugin_mode()


class PluginSecurityContext:
    """Context manager for plugin security."""
    
    def __enter__(self):
        """Enter security context - enable import restrictions."""
        enable_plugin_security()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit security context - disable import restrictions."""
        disable_plugin_security()


def load_plugin_securely(plugin_path, plugin_name: str):
    """Load a plugin module with import security enabled.
    
    Args:
        plugin_path: Path to the plugin file
        plugin_name: Name for the plugin module
        
    Returns:
        Loaded module or None if failed
        
    Raises:
        SecurityError: If plugin attempts restricted imports
    """
    try:
        # Create module spec
        spec = importlib.util.spec_from_file_location(
            f"yoix_plugin_{plugin_name}", 
            plugin_path
        )
        
        if not spec or not spec.loader:
            raise ImportError(f"Could not create module spec for {plugin_name}")
            
        # Load module with security restrictions
        with PluginSecurityContext():
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
        return module
        
    except SecurityError:
        # Re-raise security errors
        raise
    except Exception as e:
        # Wrap other exceptions
        raise ImportError(f"Error loading plugin module {plugin_name}: {e}")


def add_allowed_module(module_name: str):
    """Add a module to the whitelist (for extending allowed modules).
    
    Args:
        module_name: Module name to allow
    """
    _secure_importer.ALLOWED_MODULES.add(module_name)


def remove_allowed_module(module_name: str):
    """Remove a module from the whitelist.
    
    Args:
        module_name: Module name to remove
    """
    _secure_importer.ALLOWED_MODULES.discard(module_name)


def get_allowed_modules() -> Set[str]:
    """Get the current set of allowed modules.
    
    Returns:
        Set of allowed module names
    """
    return _secure_importer.ALLOWED_MODULES.copy()


def get_blocked_modules() -> Set[str]:
    """Get the current set of blocked modules.
    
    Returns:
        Set of blocked module names
    """
    return _secure_importer.BLOCKED_MODULES.copy()