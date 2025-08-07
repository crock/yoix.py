
import os
import json
import zipfile
import tempfile
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional

from .security import load_plugin_securely, SecurityError


class YoixPlugin:
    """Base class for Yoix plugins."""
    
    def __init__(self, name: str, version: str, description: str = "", developer: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.developer = developer
        self.is_active = False
        self.plugin_dir = None
        
    def activate(self):
        """Activate the plugin."""
        self.is_active = True
        
    def deactivate(self):
        """Deactivate the plugin."""
        self.is_active = False
        
    def on_site_build_start(self, site_builder):
        """Called when site build starts."""
        pass
        
    def on_site_build_end(self, site_builder):
        """Called when site build ends."""
        pass
        
    def on_post_process(self, post_data, site_builder):
        """Called when processing a post."""
        return post_data
        
    def on_page_process(self, page_data, site_builder):
        """Called when processing a page."""
        return page_data


class PluginManager:
    """Manages Yoix plugins loaded from .yoixplugin archives."""
    
    def __init__(self, plugins_dir: Path):
        """Initialize the plugin manager.
        
        Args:
            plugins_dir: Directory containing .yoixplugin files
        """
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, YoixPlugin] = {}
        self.temp_dirs: List[str] = []
        
    def discover_plugins(self) -> List[Path]:
        """Discover all .yoixplugin files in the plugins directory.
        
        Returns:
            List of paths to .yoixplugin files
        """
        if not self.plugins_dir.exists():
            return []
            
        return list(self.plugins_dir.glob("*.yoixplugin"))
        
    def load_plugin_info(self, plugin_path: Path) -> Optional[Dict[str, Any]]:
        """Load plugin info from a .yoixplugin file.
        
        Args:
            plugin_path: Path to the .yoixplugin file
            
        Returns:
            Plugin info dictionary or None if invalid
        """
        try:
            with zipfile.ZipFile(plugin_path, 'r') as zip_file:
                if 'info.json' not in zip_file.namelist():
                    print(f"Warning: {plugin_path.name} missing info.json")
                    return None
                    
                with zip_file.open('info.json') as info_file:
                    return json.loads(info_file.read().decode('utf-8'))
                    
        except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading plugin {plugin_path.name}: {e}")
            return None
            
    def extract_plugin(self, plugin_path: Path) -> Optional[Path]:
        """Extract a .yoixplugin file to a temporary directory.
        
        Args:
            plugin_path: Path to the .yoixplugin file
            
        Returns:
            Path to extracted directory or None if failed
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"yoix_plugin_{plugin_path.stem}_")
            self.temp_dirs.append(temp_dir)
            
            with zipfile.ZipFile(plugin_path, 'r') as zip_file:
                zip_file.extractall(temp_dir)
                
            return Path(temp_dir)
            
        except zipfile.BadZipFile as e:
            print(f"Error extracting plugin {plugin_path.name}: {e}")
            return None
            
    def load_plugin_module(self, plugin_dir: Path, plugin_name: str) -> Optional[Any]:
        """Load the Python module from an extracted plugin.
        
        Args:
            plugin_dir: Directory containing extracted plugin files
            plugin_name: Name of the plugin
            
        Returns:
            Loaded module or None if failed
        """
        # Look for main.py or plugin.py
        main_file = plugin_dir / "main.py"
        plugin_file = plugin_dir / "plugin.py"
        
        if main_file.exists():
            module_file = main_file
        elif plugin_file.exists():
            module_file = plugin_file
        else:
            print(f"Warning: No main.py or plugin.py found in {plugin_name}")
            return None
            
        try:
            # Use secure plugin loading with import restrictions
            return load_plugin_securely(module_file, plugin_name)
                
        except SecurityError as e:
            print(f"Security error loading plugin {plugin_name}: {e}")
            return None
        except Exception as e:
            print(f"Error loading plugin module {plugin_name}: {e}")
            return None
            
    def load_plugin(self, plugin_path: Path) -> bool:
        """Load a single plugin from a .yoixplugin file.
        
        Args:
            plugin_path: Path to the .yoixplugin file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        # Load plugin info
        plugin_info = self.load_plugin_info(plugin_path)
        if not plugin_info:
            return False
            
        plugin_name = plugin_info.get('name', plugin_path.stem)
        
        # Check if already loaded
        if plugin_name in self.loaded_plugins:
            print(f"Plugin {plugin_name} already loaded")
            return True
            
        # Extract plugin files
        plugin_dir = self.extract_plugin(plugin_path)
        if not plugin_dir:
            return False
            
        # Load plugin module
        plugin_module = self.load_plugin_module(plugin_dir, plugin_name)
        if not plugin_module:
            return False
            
        # Get plugin class
        plugin_class = getattr(plugin_module, 'Plugin', None)
        if not plugin_class:
            print(f"Warning: No Plugin class found in {plugin_name}")
            return False
            
        # Instantiate plugin
        try:
            plugin_instance = plugin_class(
                name=plugin_info.get('name', plugin_name),
                version=plugin_info.get('version', '0.0.0'),
                description=plugin_info.get('description', ''),
                developer=plugin_info.get('developer', '')
            )
            plugin_instance.plugin_dir = plugin_dir
            
            self.loaded_plugins[plugin_name] = plugin_instance
            print(f"Loaded plugin: {plugin_name} v{plugin_instance.version}")
            return True
            
        except Exception as e:
            print(f"Error instantiating plugin {plugin_name}: {e}")
            return False
            
    def load_all_plugins(self) -> int:
        """Load all plugins from the plugins directory.
        
        Returns:
            Number of successfully loaded plugins
        """
        plugin_files = self.discover_plugins()
        loaded_count = 0
        
        for plugin_file in plugin_files:
            if self.load_plugin(plugin_file):
                loaded_count += 1
                
        return loaded_count
        
    def get_plugin(self, name: str) -> Optional[YoixPlugin]:
        """Get a loaded plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        return self.loaded_plugins.get(name)
        
    def get_active_plugins(self) -> List[YoixPlugin]:
        """Get all active plugins.
        
        Returns:
            List of active plugin instances
        """
        return [plugin for plugin in self.loaded_plugins.values() if plugin.is_active]
        
    def activate_plugin(self, name: str) -> bool:
        """Activate a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            True if activated successfully, False otherwise
        """
        plugin = self.get_plugin(name)
        if plugin:
            plugin.activate()
            return True
        return False
        
    def deactivate_plugin(self, name: str) -> bool:
        """Deactivate a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            True if deactivated successfully, False otherwise
        """
        plugin = self.get_plugin(name)
        if plugin:
            plugin.deactivate()
            return True
        return False
        
    def call_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """Call a hook on all active plugins.
        
        Args:
            hook_name: Name of the hook method to call
            *args: Positional arguments to pass to hooks
            **kwargs: Keyword arguments to pass to hooks
            
        Returns:
            Modified data if applicable
        """
        data = args[0] if args else None
        
        for plugin in self.get_active_plugins():
            hook_method = getattr(plugin, hook_name, None)
            if hook_method and callable(hook_method):
                try:
                    result = hook_method(*args, **kwargs)
                    if result is not None:
                        data = result
                        if args:
                            args = (data,) + args[1:]
                except Exception as e:
                    print(f"Error calling {hook_name} on plugin {plugin.name}: {e}")
                    
        return data
        
    def cleanup(self):
        """Clean up temporary directories created for plugins."""
        import shutil
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory {temp_dir}: {e}")
        self.temp_dirs.clear()
        
    def __del__(self):
        """Cleanup when the plugin manager is destroyed."""
        self.cleanup()
