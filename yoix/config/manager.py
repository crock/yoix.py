"""Configuration management for Yoix."""

import sys
from pathlib import Path
from typing import Dict, Optional, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .defaults import DEFAULT_CONFIG


class ConfigManager:
    """Manages configuration loading and validation for Yoix.
    
    This class handles loading configuration from TOML files, merging with defaults,
    validating the configuration, and resolving paths relative to the config file.
    """
    
    def __init__(self, config: Optional[Union[Dict, str, Path]] = None):
        """Initialize the configuration manager.
        
        Args:
            config: Configuration source. Can be:
                - None: Use default configuration
                - dict: Use as-is, merged with defaults
                - str/Path: Path to TOML config file
        """
        self.config = self._load_config(config)
        self._validate_config()
        
    def _load_config(self, config: Optional[Union[Dict, str, Path]] = None) -> Dict:
        """Load and merge configuration with defaults.
        
        Args:
            config: Configuration source
            
        Returns:
            Dict: Merged configuration
        """
        if config is None:
            return DEFAULT_CONFIG.copy()
            
        if isinstance(config, (str, Path)):
            config_path = Path(config)
            if not config_path.exists():
                raise ValueError(f"Config file not found: {config_path}")
                
            try:
                with open(config_path, 'rb') as f:
                    loaded_config = tomllib.load(f)
                # Convert paths to be relative to config file
                return self._resolve_paths(loaded_config.get('site', {}), config_path.parent)
            except Exception as e:
                raise ValueError(f"Failed to parse config file {config_path}: {e}")
                
        if not isinstance(config, dict):
            raise TypeError(f"Config must be dict, str, or Path, not {type(config)}")
            
        return self._merge_configs(DEFAULT_CONFIG, config)
        
    def _resolve_paths(self, config: Dict, base_path: Path) -> Dict:
        """Resolve paths in config to be relative to config file location.
        
        Args:
            config: Configuration dictionary
            base_path: Base path for resolving relative paths
            
        Returns:
            Dict: Configuration with resolved paths
        """
        resolved = config.copy()
        
        if 'build' in resolved:
            build = resolved['build']
            for key in ['content_dir', 'public_dir', 'partials_dir', 'templates_dir']:
                if key in build:
                    build[key] = str(base_path / build[key])
                    
        return resolved
        
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two configuration dictionaries.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Dict: Merged configuration
        """
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
                
        return merged
        
    def _validate_config(self):
        """Validate the configuration.
        
        Raises:
            ValueError: If required configuration values are missing or invalid
        """
        required_sections = ['build', 'info']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")
                
        build = self.config['build']
        required_build = ['content_dir', 'public_dir', 'templates_dir', 'partials_dir']
        for key in required_build:
            if key not in build:
                raise ValueError(f"Missing required build config: {key}")
                
        info = self.config['info']
        required_info = ['base_url', 'site_name']
        for key in required_info:
            if key not in info:
                raise ValueError(f"Missing required site info: {key}")
    
    def get_build_paths(self) -> Dict[str, Path]:
        """Get build-related paths from config.
        
        Returns:
            Dict[str, Path]: Dictionary of path names to Path objects
        """
        build = self.config['build']
        return {
            'content_dir': Path(build['content_dir']),
            'public_dir': Path(build['public_dir']),
            'templates_dir': Path(build['templates_dir']),
            'partials_dir': Path(build['partials_dir'])
        }
    
    def get_site_info(self) -> Dict[str, str]:
        """Get site information from config.
        
        Returns:
            Dict[str, str]: Dictionary of site information
        """
        return self.config['info'].copy()
    
    def get_frontmatter_aliases(self) -> Dict[str, list]:
        """Get frontmatter aliases from config.
        
        Returns:
            Dict[str, list]: Dictionary of frontmatter field aliases
        """
        return self.config.get('frontmatter', {}).get('aliases', {})
