"""
Plugin API for secure plugin interactions with Yoix.

This API provides a secure interface for plugins to interact with the site builder,
content, and file system while preventing malicious operations.
"""

import os
import re
from pathlib import Path
import requests
from urllib.parse import urlparse
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
        self._allowed_domains = set()
        self._request_timeout = 30
        self._db_manager = site_builder.db_manager
        
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
        
    def get_public_dir(self) -> Path:
        """Get the public output directory path."""
        return self._site_builder.public_dir
        
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

    # HTTP Request Methods (Secure)
    def add_allowed_domain(self, domain: str) -> None:
        """Add a domain to the HTTP request whitelist.
        
        Args:
            domain: Domain to allow (e.g., 'api.example.com')
        """
        # Normalize domain (remove protocol, path, etc.)
        parsed = urlparse(f"https://{domain}" if not domain.startswith(('http://', 'https://')) else domain)
        clean_domain = parsed.netloc.lower()
        
        if clean_domain:
            self._allowed_domains.add(clean_domain)
            
    def remove_allowed_domain(self, domain: str) -> None:
        """Remove a domain from the HTTP request whitelist.
        
        Args:
            domain: Domain to remove
        """
        parsed = urlparse(f"https://{domain}" if not domain.startswith(('http://', 'https://')) else domain)
        clean_domain = parsed.netloc.lower()
        self._allowed_domains.discard(clean_domain)
        
    def get_allowed_domains(self) -> List[str]:
        """Get list of allowed domains.
        
        Returns:
            List of allowed domain names
        """
        return sorted(list(self._allowed_domains))
        
    def _validate_url(self, url: str) -> bool:
        """Validate that a URL is allowed for HTTP requests.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is allowed, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Block local/private networks
            if domain in ('localhost', '127.0.0.1', '0.0.0.0'):
                return False
                
            # Block private IP ranges (simplified check)
            if domain.startswith(('192.168.', '10.', '172.')):
                return False
                
            # Check against whitelist
            if self._allowed_domains and domain not in self._allowed_domains:
                return False
                
            # Only allow HTTP/HTTPS
            if parsed.scheme not in ('http', 'https'):
                return False
                
            return True
            
        except Exception:
            return False
            
    def _sanitize_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Sanitize HTTP headers to prevent security issues.
        
        Args:
            headers: Raw headers dictionary
            
        Returns:
            Sanitized headers dictionary
        """
        if not headers:
            return {}
            
        # Default safe headers
        safe_headers = {
            'User-Agent': f'Yoix-Plugin/{self._plugin.name}',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
        
        # Allowed header keys (whitelist)
        allowed_headers = {
            'accept', 'accept-encoding', 'accept-language', 'authorization',
            'cache-control', 'content-type', 'user-agent', 'x-api-key',
            'x-auth-token', 'x-requested-with'
        }
        
        # Add user headers if they're safe
        for key, value in headers.items():
            if key.lower() in allowed_headers and isinstance(value, str):
                # Prevent header injection
                clean_value = value.replace('\n', '').replace('\r', '')
                safe_headers[key] = clean_value
                
        return safe_headers
        
    def http_get(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make a secure HTTP GET request.
        
        Args:
            url: URL to request
            headers: Optional HTTP headers
            params: Optional query parameters
            
        Returns:
            Dictionary containing response data
            
        Raises:
            SecurityError: If URL is not allowed
            PluginApiError: If request fails
        """
        if not self._validate_url(url):
            raise SecurityError(f"URL not allowed: {url}")
            
        safe_headers = self._sanitize_headers(headers)
        
        try:
            response = requests.get(
                url,
                headers=safe_headers,
                params=params,
                timeout=self._request_timeout,
                allow_redirects=True,
                verify=True  # Verify SSL certificates
            )
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                'ok': response.ok,
                'url': response.url
            }
            
        except requests.exceptions.Timeout:
            raise PluginApiError(f"Request timeout after {self._request_timeout} seconds")
        except requests.exceptions.SSLError as e:
            raise PluginApiError(f"SSL verification failed: {e}")
        except requests.exceptions.ConnectionError as e:
            raise PluginApiError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise PluginApiError(f"HTTP request failed: {e}")
        except Exception as e:
            raise PluginApiError(f"Unexpected error during HTTP request: {e}")
            
    def http_post(self, url: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, json_data: bool = True) -> Dict[str, Any]:
        """Make a secure HTTP POST request.
        
        Args:
            url: URL to request
            payload: Data to send in request body
            headers: Optional HTTP headers
            json_data: Whether to send payload as JSON (default: True)
            
        Returns:
            Dictionary containing response data
            
        Raises:
            SecurityError: If URL is not allowed
            PluginApiError: If request fails
        """
        if not self._validate_url(url):
            raise SecurityError(f"URL not allowed: {url}")
            
        safe_headers = self._sanitize_headers(headers)
        
        try:
            if json_data and payload:
                response = requests.post(
                    url,
                    json=payload,
                    headers=safe_headers,
                    timeout=self._request_timeout,
                    allow_redirects=True,
                    verify=True
                )
            else:
                response = requests.post(
                    url,
                    data=payload,
                    headers=safe_headers,
                    timeout=self._request_timeout,
                    allow_redirects=True,
                    verify=True
                )
                
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                'ok': response.ok,
                'url': response.url
            }
            
        except requests.exceptions.Timeout:
            raise PluginApiError(f"Request timeout after {self._request_timeout} seconds")
        except requests.exceptions.SSLError as e:
            raise PluginApiError(f"SSL verification failed: {e}")
        except requests.exceptions.ConnectionError as e:
            raise PluginApiError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise PluginApiError(f"HTTP request failed: {e}")
        except Exception as e:
            raise PluginApiError(f"Unexpected error during HTTP request: {e}")
            
    def http_put(self, url: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, json_data: bool = True) -> Dict[str, Any]:
        """Make a secure HTTP PUT request.
        
        Args:
            url: URL to request
            payload: Data to send in request body
            headers: Optional HTTP headers
            json_data: Whether to send payload as JSON (default: True)
            
        Returns:
            Dictionary containing response data
        """
        if not self._validate_url(url):
            raise SecurityError(f"URL not allowed: {url}")
            
        safe_headers = self._sanitize_headers(headers)
        
        try:
            if json_data and payload:
                response = requests.put(
                    url,
                    json=payload,
                    headers=safe_headers,
                    timeout=self._request_timeout,
                    verify=True
                )
            else:
                response = requests.put(
                    url,
                    data=payload,
                    headers=safe_headers,
                    timeout=self._request_timeout,
                    verify=True
                )
                
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                'ok': response.ok,
                'url': response.url
            }
            
        except requests.exceptions.RequestException as e:
            raise PluginApiError(f"HTTP PUT request failed: {e}")
        except Exception as e:
            raise PluginApiError(f"Unexpected error during HTTP PUT request: {e}")
            
    def set_request_timeout(self, timeout: int) -> None:
        """Set the timeout for HTTP requests.
        
        Args:
            timeout: Timeout in seconds (max: 120)
        """
        self._request_timeout = min(max(timeout, 1), 120)  # Clamp between 1-120 seconds
        
    # Database Access Methods (Secure)
    def db_set(self, key: str, value: Any, expires_in_seconds: Optional[int] = None) -> None:
        """Store data in plugin's database storage.
        
        Args:
            key: Storage key (namespaced to plugin)
            value: Value to store
            expires_in_seconds: Optional expiration time
        """
        self._db_manager.plugin_set_data(self._plugin.name, key, value, expires_in_seconds)
        
    def db_get(self, key: str) -> Any:
        """Get data from plugin's database storage.
        
        Args:
            key: Storage key
            
        Returns:
            Stored value or None if not found/expired
        """
        return self._db_manager.plugin_get_data(self._plugin.name, key)
        
    def db_delete(self, key: str = None) -> None:
        """Delete data from plugin's database storage.
        
        Args:
            key: Optional specific key to delete. If None, deletes all plugin data.
        """
        self._db_manager.plugin_delete_data(self._plugin.name, key)
        
    def cache_to_db(self, key: str, value: Any, expires_in_seconds: Optional[int] = None) -> None:
        """Store value in persistent database cache (survives restarts).
        
        Args:
            key: Cache key (will be namespaced to plugin)
            value: Value to cache
            expires_in_seconds: Optional expiration time
        """
        cache_key = f"plugin:{self._plugin.name}:{key}"
        self._db_manager.cache_set(cache_key, value, expires_in_seconds, "plugin")
        
    def cache_from_db(self, key: str) -> Any:
        """Get value from persistent database cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_key = f"plugin:{self._plugin.name}:{key}"
        return self._db_manager.cache_get(cache_key)
        
    def record_metric(self, metric_name: str, value: float, unit: str = None) -> None:
        """Record a custom metric for this plugin.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Optional unit (e.g., 'seconds', 'count', 'bytes')
        """
        if self._site_builder.build_hash:
            full_metric_name = f"plugin:{self._plugin.name}:{metric_name}"
            self._db_manager.record_metric(
                self._site_builder.build_hash,
                full_metric_name,
                value,
                unit,
                "plugin"
            )