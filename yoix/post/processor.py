"""Post and page processing for markdown files."""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import frontmatter
import mistune
from slugify import slugify


class BaseProcessor:
    """Base class for markdown file processing."""
    
    def __init__(self, base_url: str, site_name: str, default_author: str, frontmatter_aliases: Dict[str, List[str]]):
        """Initialize the base processor.
        
        Args:
            base_url: Base URL for the site
            site_name: Name of the site
            default_author: Default author name
            frontmatter_aliases: Dictionary of frontmatter key aliases
        """
        self.base_url = base_url
        self.site_name = site_name
        self.default_author = default_author
        self.frontmatter_aliases = frontmatter_aliases
        self.markdown = mistune.create_markdown(escape=False)
        
    def _resolve_alias(self, metadata: Dict[str, Any], key: str) -> Optional[Any]:
        """Resolve a frontmatter key considering its aliases.
        
        Args:
            metadata: The frontmatter metadata
            key: The primary key to look for
            
        Returns:
            The value for the key or its aliases, or None if not found
        """
        # First check the primary key
        if key in metadata:
            return metadata[key]
            
        # Check aliases if defined
        aliases = self.frontmatter_aliases.get(key, [])
        for alias in aliases:
            if alias in metadata:
                return metadata[alias]
                
        return None
        
    def _extract_date(self, metadata: Dict[str, Any], filename: str) -> datetime:
        """Extract date from metadata or filename.
        
        Args:
            metadata: Post metadata
            filename: Name of the file (for fallback date extraction)
            
        Returns:
            datetime object
        """
        # Try to get date from metadata
        date_str = self._resolve_alias(metadata, 'date')
        if date_str:
            try:
                if isinstance(date_str, (int, str)) and len(str(date_str)) == 8:
                    # Handle YYYYMMDD format
                    return datetime.strptime(str(date_str), '%Y%m%d')
                return datetime.fromisoformat(str(date_str))
            except (ValueError, TypeError):
                pass
                
        # Try to extract date from filename (YYYY-MM-DD-title format)
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            try:
                return datetime.strptime(date_match.group(1), '%Y-%m-%d')
            except ValueError:
                pass
                
        # Fallback to file modification time
        return datetime.now()

    def extract_images(self, content: str) -> List[str]:
        """Extract image paths from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of image paths
        """
        image_pattern = r'!\[.*?\]\((.*?)\)'
        return [m.group(1) for m in re.finditer(image_pattern, content)]


class PostProcessor(BaseProcessor):
    """Processes markdown blog posts."""
    
    def __init__(self, base_url: str, site_name: str, default_author: str, frontmatter_aliases: Dict[str, List[str]], posts_dir: str = "posts"):
        """Initialize the post processor.
        
        Args:
            base_url: Base URL for the site
            site_name: Name of the site
            default_author: Default author name
            frontmatter_aliases: Dictionary of frontmatter key aliases
            posts_dir: Name of the directory containing blog posts (default: "posts")
        """
        super().__init__(base_url, site_name, default_author, frontmatter_aliases)
        self.posts_dir = posts_dir

    def _generate_slug(self, path: Path, metadata: Dict[str, Any], input_dir: Path) -> str:
        """Generate a URL slug for the post.
        
        Args:
            path: Path to the markdown file
            metadata: Post metadata
            input_dir: Base input directory
            
        Returns:
            URL slug for the post
        """
        # Use explicit slug if provided in metadata
        if slug := self._resolve_alias(metadata, 'slug'):
            return slug
            
        # Get relative path without extension
        rel_path = path.relative_to(input_dir)
        if path.name == 'index.md':
            # For index.md files, use the parent directory name
            return str(rel_path.parent)
            
        # Otherwise use the filename without extension
        stem = path.stem
        # Remove date prefix if present
        if re.match(r'^\d{4}-\d{2}-\d{2}-', stem):
            stem = stem[11:]
        return slugify(stem)

    def process_post(self, path: Path, input_dir: Path) -> Optional[Dict[str, Any]]:
        """Process a markdown post file if it's in the posts directory.
        
        Args:
            path: Path to markdown file
            input_dir: Input directory containing markdown files
            
        Returns:
            Dictionary containing processed post data, or None if not a blog post
        """
        # Check if the file is in a posts directory
        try:
            relative_path = path.relative_to(input_dir)
            path_parts = relative_path.parts
            
            # Skip if not in posts directory
            if self.posts_dir not in path_parts:
                return None
                
            # Skip if not a markdown file
            if not path.suffix.lower() in ['.md', '.markdown']:
                return None
                
            # Parse frontmatter and content
            post = frontmatter.load(path)
            metadata = post.metadata
            content = post.content
            
            # Extract date
            date = self._extract_date(metadata, path.name)
            
            # Generate slug and URL path
            slug = self._generate_slug(path, metadata, input_dir)
            url_path = f"{slug}/index.html"
            
            # Convert markdown to HTML
            html = self.markdown(content)
            
            # Build post data
            post_data = {
                'title': self._resolve_alias(metadata, 'title') or path.stem,
                'date': {
                    'iso': date.strftime('%Y-%m-%d'),
                    'display': date.strftime('%B %d, %Y')
                },
                'author': self._resolve_alias(metadata, 'author') or self.default_author,
                'content': html,
                'slug': slug,
                'url_path': f"{url_path}",  
                'url': f"/{self.posts_dir}/{slug}/",  
                'layout': self._resolve_alias(metadata, 'layout') or 'post',
                'meta': {
                    'description': self._resolve_alias(metadata, 'description') or '',
                    'keywords': metadata.get('keywords', [])
                }
            }
            
            # Generate schema
            post_data['jsonLdSchema'] = self.generate_schema(post_data)
            
            return post_data
            
        except ValueError:
            # Path is not relative to input_dir
            return None

    def generate_schema(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON-LD schema for a blog post.
        
        Args:
            post: Post data including metadata
            
        Returns:
            JSON-LD schema dictionary
        """
        return {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post["title"],
            "datePublished": post["date"]["iso"],
            "author": {
                "@type": "Person",
                "name": post["author"]
            },
            "description": post["meta"]["description"],
            "url": f"{self.base_url.rstrip('/')}{post['url']}",
            "publisher": {
                "@type": "Organization",
                "@id": self.base_url,
                "name": self.site_name
            },
            "keywords": post["meta"]["keywords"]
        }


class PageProcessor(BaseProcessor):
    """Processes markdown pages that are not blog posts."""
    
    def process_page(self, path: Path, input_dir: Path) -> Optional[Dict[str, Any]]:
        """Process a markdown page file.
        
        Args:
            path: Path to markdown file
            input_dir: Input directory containing markdown files
            
        Returns:
            Dictionary containing processed page data, or None if not a markdown file
        """
        try:
            relative_path = path.relative_to(input_dir)
            
            # Skip if not a markdown file
            if not path.suffix.lower() in ['.md', '.markdown']:
                return None
                
            # Skip if in a posts directory (those are handled by PostProcessor)
            if "posts" in relative_path.parts:
                return None
                
            # Parse frontmatter and content
            page = frontmatter.load(path)
            metadata = page.metadata
            content = page.content
            
            # Convert markdown to HTML
            html = self.markdown(content)
            
            # Generate slug from the path or metadata
            if slug := self._resolve_alias(metadata, 'slug'):
                # Use explicit slug if provided
                slug = slugify(slug)
            elif path.name == 'index.md':
                # For index.md files, use the parent directory name
                slug = path.parent.name
            else:
                # Otherwise use the filename without extension
                slug = slugify(path.stem)
            
            # Always output as index.html in a directory named after the slug
            # Special case for root index.md
            if str(relative_path) == 'index.md':
                url_path = 'index.html'
                url = '/'
            else:
                url_path = f"{slug}/index.html"
                url = f"/{slug}/"
            
            # Build page data
            page_data = {
                'title': self._resolve_alias(metadata, 'title') or path.stem,
                'content': html,
                'url_path': url_path,
                'url': url,
                'layout': self._resolve_alias(metadata, 'layout') or 'default',
                'meta': {
                    'description': self._resolve_alias(metadata, 'description') or '',
                    'keywords': metadata.get('keywords', [])
                }
            }
            
            # Add optional date if specified
            if date_str := self._resolve_alias(metadata, 'date'):
                date = self._extract_date(metadata, path.name)
                page_data['date'] = {
                    'iso': date.strftime('%Y-%m-%d'),
                    'display': date.strftime('%B %d, %Y')
                }
            
            # Add optional author if specified
            if author := self._resolve_alias(metadata, 'author'):
                page_data['author'] = author
            
            return page_data
            
        except ValueError:
            # Path is not relative to input_dir
            return None
