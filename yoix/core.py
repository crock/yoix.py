"""Core functionality for building websites from markdown files."""

import os
from pathlib import Path

from .config import ConfigManager
from .template import TemplateManager
from .post import PostProcessor, PageProcessor
from .asset import AssetManager
from .pm import PluginManager

from yoix_pi.processor import process_persistent_includes


class SiteBuilder:
    """Build a website from markdown files."""
    
    def __init__(self, config=None):
        """Initialize with configuration dictionary containing paths.
        
        Args:
            config: Configuration source. Can be:
                - None: Use default configuration
                - dict: Use as-is, merged with defaults
                - str/Path: Path to TOML config file
        """
        # Initialize configuration
        self.config_manager = ConfigManager(config)
        
        # Set build paths
        paths = self.config_manager.get_build_paths()
        self.content_dir = paths['content_dir']
        self.public_dir = paths['public_dir']
        self.templates_dir = paths['templates_dir']
        self.partials_dir = paths['partials_dir']
        
        # Set site info
        site_info = self.config_manager.get_site_info()
        self.base_url = site_info['base_url']
        self.site_name = site_info['site_name']
        self.site_logo = site_info['site_logo']
        self.author = site_info['author']
        
        # Get frontmatter aliases
        self.frontmatter_aliases = self.config_manager.get_frontmatter_aliases()
        
        # Initialize managers
        self.template_manager = TemplateManager(self.templates_dir)
        self.post_processor = PostProcessor(
            self.base_url,
            self.site_name,
            self.author,
            self.frontmatter_aliases
        )
        self.page_processor = PageProcessor(
            self.base_url,
            self.site_name,
            self.author,
            self.frontmatter_aliases
        )
        self.asset_manager = AssetManager(self.public_dir, self.content_dir)
        
        # Initialize plugin manager
        plugins_dir = self.content_dir.parent / 'plugins'
        self.plugin_manager = PluginManager(plugins_dir)
        
        self.posts = []
        self.pages = []
        self.post_schemas = []
        
        self._validate_directories()
        self._load_plugins()
        
    def _validate_directories(self):
        """Create required directories if they don't exist."""
        for directory in [self.content_dir, self.public_dir, self.templates_dir, self.partials_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
    def _load_plugins(self):
        """Load and activate all plugins."""
        loaded_count = self.plugin_manager.load_all_plugins()
        if loaded_count > 0:
            print(f"Loaded {loaded_count} plugin(s)")
            
            # Activate all loaded plugins by default
            for plugin_name in self.plugin_manager.loaded_plugins:
                self.plugin_manager.activate_plugin(plugin_name)
            
    def _copy_images(self, page_data, input_dir):
        """Copy images from content directory to public directory.
        
        Args:
            page_data (dict): Page or post data containing content
            input_dir (Path): Input directory path
        """
        images = self.post_processor.extract_images(page_data['content'])
        for image_path in images:
            self.asset_manager.copy_asset(image_path, relative_to=input_dir)
            
    def _render_page(self, variables):
        """Render a page using the appropriate template.
        
        Args:
            variables (dict): Template variables
            
        Returns:
            str: Rendered HTML
        """
        # Use specified layout or default to 'default'
        layout = variables.get('layout', 'default')
        return self.template_manager.render(layout, variables)

    def _render_blog_index(self, index_data):   
        """Render the blog index page using the blog-index template.
        
        Args:
            index_data (dict): Index data including posts and site info
            
        Returns:
            str: Rendered HTML
        """
        return self.template_manager.render('blog-index', index_data)

    def write_page(self, path, variables):
        """Write a page to the output directory.
        
        Args:
            path (Path): Output path
            variables (dict): Template variables
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render_page(variables)
        with open(path, "w") as f:
            f.write(html)
        
    def write_blog_index(self, variables):
        """Write the blog index page.
        
        Args:
            variables (dict): Template variables
        """
        index_path = self.public_dir / 'blog' / 'index.html'
        index_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render_blog_index(variables)
        with open(index_path, "w") as f:
            f.write(html)
        
    def build(self, input_dir):
        """Build the website from markdown files.
        
        Args:
            input_dir (Path): Input directory containing markdown files
        """
        input_dir = Path(input_dir)
        if not input_dir.exists():
            raise ValueError(f"Input directory {input_dir} does not exist")
            
        # Call plugin hook: site build start
        self.plugin_manager.call_hook('on_site_build_start', self)
            
        # Process all markdown files recursively
        for md_file in input_dir.rglob("*.md"):
            # Process all markdown files - no longer skip non-index files
            
            # Try to process as a blog post first
            if post_data := self.post_processor.process_post(md_file, input_dir):
                # Call plugin hook: post process
                post_data = self.plugin_manager.call_hook('on_post_process', post_data, self) or post_data
                
                # Handle blog post
                self.posts.append(post_data)
                
                # Copy any images used in the post
                self._copy_images(post_data, input_dir)
                
                # Write individual post page
                post_path = self.public_dir / post_data['url_path']
                self.write_page(post_path, post_data)
                
                # Add schema for the post
                if schema := post_data.get('jsonLdSchema'):
                    self.post_schemas.append(schema)
            
            # If not a blog post, try to process as a regular page
            elif page_data := self.page_processor.process_page(md_file, input_dir):
                # Call plugin hook: page process
                page_data = self.plugin_manager.call_hook('on_page_process', page_data, self) or page_data
                
                # Handle regular page
                self.pages.append(page_data)
                
                # Copy any images used in the page
                self._copy_images(page_data, input_dir)
                
                # Determine the URL path based on the file name
                try:
                    relative_parent = md_file.parent.relative_to(input_dir)
                except ValueError:
                    # File is in the root directory
                    relative_parent = Path('')
                
                if md_file.name == 'index.md':
                    # For index.md, use the parent directory path
                    url_path = relative_parent
                else:
                    # For non-index.md files, create a directory with the file's stem name
                    url_path = relative_parent / md_file.stem
                
                # Update the page data with the new URL path
                page_data['url_path'] = url_path
                
                # Write the page
                page_path = self.public_dir / url_path / 'index.html'
                self.write_page(page_path, page_data)
            
        # Sort posts by date
        self.posts.sort(key=lambda x: x['date']['iso'], reverse=True)
        
        # Write blog index if we have any posts
        if self.posts:
            self.write_blog_index({
                'title': 'Blog',
                'description': 'Latest blog posts',
                'url': f"{self.base_url.rstrip('/')}/blog/",
                'blogPostsSchema': self.post_schemas,
                'posts': self.posts
            })
        
        # Copy static assets
        self.asset_manager.copy_static_assets()
        
        # Copy theme assets if theme directory exists
        theme_dir = self.content_dir / 'theme'
        if theme_dir.exists():
            self.asset_manager.copy_theme_assets(theme_dir)

        process_persistent_includes({
            'partials_dir': self.partials_dir,
            'public_dir': self.public_dir
        })

        # Call plugin hook: site build end
        self.plugin_manager.call_hook('on_site_build_end', self)
