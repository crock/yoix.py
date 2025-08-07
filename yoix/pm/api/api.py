"""
Plugin API for secure plugin interactions with Yoix.

This API provides a secure interface for plugins to interact with the site builder,
content, and file system while preventing malicious operations.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


class PluginApiError(Exception):
    """Base exception for Plugin API errors."""
    pass


class SecurityError(PluginApiError):
    """Raised when a plugin attempts an unauthorized operation."""
    pass


class PluginApi:
    """Secure API interface for Yoix plugins."""
    
    def __init__(self, site_builder, plugin_instance, plugin_dir: Path):
        """Initialize the plugin API.
        
        Args:
            site_builder: The SiteBuilder instance
            plugin_instance: The plugin instance using this API
            plugin_dir: Directory containing the plugin files
        """
        self._site_builder = site_builder
        self._plugin = plugin_instance
        self._plugin_dir = Path(plugin_dir)
        self._cache = {}
        
        # Security: Define allowed file operations
        self._allowed_read_dirs = {
            self._plugin_dir,
            site_builder.content_dir,
            site_builder.templates_dir,
            site_builder.partials_dir
        }
        self._allowed_write_dirs = {
            site_builder.public_dir
        }
        
    # Core Site Access Methods
    def get_site_config(self) -> Dict[str, Any]:
        """Get site configuration data."""
        return {
            'base_url': self._site_builder.base_url,
            'site_name': self._site_builder.site_name,
            'site_logo': self._site_builder.site_logo,
            'author': self._site_builder.author,
            'content_dir': str(self._site_builder.content_dir),
            'public_dir': str(self._site_builder.public_dir),
            'templates_dir': str(self._site_builder.templates_dir),
            'partials_dir': str(self._site_builder.partials_dir)
        }
        
    def get_all_posts(self) -> List[Dict[str, Any]]:
        """Get all processed blog posts."""
        return self._site_builder.posts.copy()
        
    def get_all_pages(self) -> List[Dict[str, Any]]:
        """Get all processed pages."""
        return self._site_builder.pages.copy()
        
    # Content Manipulation Methods
    def add_custom_field(self, content: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """Safely add a custom field to content data."""
        if not isinstance(content, dict):
            raise PluginApiError("Content must be a dictionary")
            
        # Prevent overwriting critical fields
        protected_fields = {'title', 'content', 'url', 'date', 'layout'}
        if key in protected_fields:
            raise SecurityError(f"Cannot modify protected field: {key}")
            
        content = content.copy()
        content[key] = value
        return content
        
    def get_frontmatter(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Get frontmatter data from content."""
        frontmatter = {}
        for key, value in content.items():
            if key not in {'content', 'html_content', 'url_path'}:
                frontmatter[key] = value
        return frontmatter
        
    # File Operations (Sandboxed)
    def _validate_path(self, path: Union[str, Path], allowed_dirs: set, operation: str) -> Path:
        """Validate that a path is within allowed directories."""
        path = Path(path).resolve()
        
        for allowed_dir in allowed_dirs:
            try:
                path.relative_to(allowed_dir.resolve())
                return path
            except ValueError:
                continue
                
        raise SecurityError(f"Path '{path}' not allowed for {operation}")
        
    def read_plugin_file(self, filename: str) -> str:
        """Read a file from the plugin directory."""
        file_path = self._plugin_dir / filename
        validated_path = self._validate_path(file_path, {self._plugin_dir}, "read")
        
        try:
            with open(validated_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (IOError, OSError) as e:
            raise PluginApiError(f"Error reading file {filename}: {e}")
            
    def write_public_file(self, path: str, content: str) -> bool:
        """Write a file to the public directory with validation."""
        file_path = self._site_builder.public_dir / path
        validated_path = self._validate_path(file_path, self._allowed_write_dirs, "write")
        
        try:
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except (IOError, OSError) as e:
            raise PluginApiError(f"Error writing file {path}: {e}")
            
    def file_exists(self, path: str, directory: str = "plugin") -> bool:
        """Check if a file exists in allowed directories."""
        if directory == "plugin":
            full_path = self._plugin_dir / path
            allowed_dirs = {self._plugin_dir}
        elif directory == "content":
            full_path = self._site_builder.content_dir / path
            allowed_dirs = {self._site_builder.content_dir}
        elif directory == "public":
            full_path = self._site_builder.public_dir / path
            allowed_dirs = {self._site_builder.public_dir}
        else:
            raise PluginApiError(f"Invalid directory: {directory}")
            
        try:
            validated_path = self._validate_path(full_path, allowed_dirs, "check")
            return validated_path.exists()
        except SecurityError:
            return False
            
    # Utility Functions
    def slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        from python_slugify import slugify
        return slugify(text)
        
    def markdown_to_html(self, text: str) -> str:
        """Convert markdown to HTML safely."""
        import mistune
        markdown = mistune.create_markdown()
        return markdown(text)
        
    def get_reading_time(self, content: str, wpm: int = 200) -> int:
        """Calculate reading time for content."""
        word_count = len(content.split())
        return max(1, word_count // wpm)
        
    def extract_images(self, content: str) -> List[str]:
        """Find image references in content."""
        md_pattern = r'!\[.*?\]\(([^)]+)\)'
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        
        images = []
        images.extend(re.findall(md_pattern, content))
        images.extend(re.findall(html_pattern, content))
        
        return images
        
    def log(self, level: str, message: str) -> None:
        """Safe logging mechanism."""
        valid_levels = {'info', 'warning', 'error', 'debug'}
        if level not in valid_levels:
            level = 'info'
            
        prefix = f"[{self._plugin.name}]"
        print(f"{prefix} {level.upper()}: {message}")
        
    # Caching
    def cache_get(self, key: str) -> Any:
        """Get a value from plugin cache."""
        plugin_key = f"{self._plugin.name}:{key}"
        return self._cache.get(plugin_key)
        
    def cache_set(self, key: str, value: Any) -> None:
        """Set a value in plugin cache."""
        plugin_key = f"{self._plugin.name}:{key}"
        self._cache[plugin_key] = value