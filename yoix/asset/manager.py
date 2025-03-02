"""Asset management for static files."""

import os
import shutil
from pathlib import Path
from typing import List, Set, Dict, Any


class AssetManager:
    """Manages static assets like images, CSS, JavaScript files."""
    
    def __init__(self, public_dir: Path, content_dir: Path):
        """Initialize the asset manager.
        
        Args:
            public_dir: Output directory for the built site
            content_dir: Input directory containing content
        """
        self.public_dir = public_dir
        self.content_dir = content_dir
        self.processed_assets: Set[str] = set()
        
    def copy_asset(self, src_path: str, relative_to: Path = None) -> bool:
        """Copy an asset to the public directory.
        
        Args:
            src_path: Path to the asset file
            relative_to: Optional base path for resolving relative paths
            
        Returns:
            bool: True if asset was copied successfully
        """
        # Skip external URLs
        if src_path.startswith(('http://', 'https://', '//')):
            return False
            
        # Convert to Path object
        src = Path(src_path)
        
        # If path is relative, try to resolve it
        if not src.is_absolute():
            if relative_to:
                # First try relative to the provided base path
                full_src = relative_to / src
                if not full_src.exists():
                    # Then try relative to content directory
                    full_src = self.content_dir / src
            else:
                # If no base path provided, use content directory
                full_src = self.content_dir / src
        else:
            full_src = src
            
        # Skip if source doesn't exist
        if not full_src.exists():
            return False
            
        # Calculate destination path
        try:
            # Try to make path relative to content directory
            rel_path = full_src.relative_to(self.content_dir)
        except ValueError:
            # If outside content directory, preserve original relative path
            rel_path = src
            
        # Construct destination path
        dst = self.public_dir / rel_path
        
        # Skip if already processed
        if str(dst) in self.processed_assets:
            return True
            
        # Create destination directory if needed
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy the file, preserving metadata
            shutil.copy2(full_src, dst)
            self.processed_assets.add(str(dst))
            return True
        except (shutil.Error, OSError):
            return False
            
    def copy_directory(self, src_dir: Path, include_patterns: List[str] = None) -> int:
        """Copy a directory of assets recursively.
        
        Args:
            src_dir: Source directory to copy
            include_patterns: Optional list of glob patterns to include
            
        Returns:
            int: Number of files copied
        """
        if not src_dir.exists():
            return 0
            
        count = 0
        patterns = include_patterns or ['*']
        
        for pattern in patterns:
            for src in src_dir.rglob(pattern):
                if src.is_file():
                    rel_path = src.relative_to(src_dir)
                    dst = self.public_dir / rel_path
                    
                    # Skip if already processed
                    if str(dst) in self.processed_assets:
                        continue
                        
                    # Create destination directory if needed
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        # Copy the file, preserving metadata
                        shutil.copy2(src, dst)
                        self.processed_assets.add(str(dst))
                        count += 1
                    except (shutil.Error, OSError):
                        continue
                        
        return count
        
    def copy_static_assets(self, static_dir: Path = None) -> int:
        """Copy static assets from the static directory.
        
        Args:
            static_dir: Optional custom static directory path
            
        Returns:
            int: Number of files copied
        """
        # Use default static directory if none provided
        static = static_dir or (self.content_dir / 'static')
        if not static.exists():
            return 0
            
        return self.copy_directory(static)
        
    def copy_theme_assets(self, theme_dir: Path) -> int:
        """Copy theme assets like CSS and JavaScript.
        
        Args:
            theme_dir: Path to theme directory
            
        Returns:
            int: Number of files copied
        """
        if not theme_dir.exists():
            return 0
            
        # Copy theme assets with specific patterns
        patterns = ['*.css', '*.js', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.woff', '*.woff2']
        return self.copy_directory(theme_dir, patterns)
        
    def clear_cache(self):
        """Clear the processed assets cache."""
        self.processed_assets.clear()
