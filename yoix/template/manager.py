"""Template management for Yoix using Handlebars."""

from pathlib import Path
from typing import Dict, Any, Optional
from pybars import Compiler

class TemplateManager:
    """Manages Handlebars templates with a focused feature set."""
    
    def __init__(self, templates_dir: Path):
        """Initialize the template manager.
        
        Args:
            templates_dir: Directory containing main templates
        """
        self.templates_dir = templates_dir
        self.compiler = Compiler()
        self._template_cache: Dict[str, str] = {}
        
    def _load_template(self, template_path: Path) -> str:
        """Load and compile a template from file.
        
        Args:
            template_path: Path to the template file
            
        Returns:
            Compiled template
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template compilation fails
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
            
        try:
            with open(template_path, "r") as f:
                template_content = f.read()
            return self.compiler.compile(template_content)
        except Exception as e:
            raise ValueError(f"Failed to compile template {template_path}: {e}")
            
    def _get_template(self, template_name: str) -> str:
        """Get a compiled template, using cache if available.
        
        Args:
            template_name: Name of the template (without extension)
            
        Returns:
            Compiled template
        """
        if template_name not in self._template_cache:
            # Try .hbs first, then .html as fallback
            hbs_path = self.templates_dir / f"{template_name}.hbs"
            html_path = self.templates_dir / f"{template_name}.html"
            
            if hbs_path.exists():
                template_path = hbs_path
            elif html_path.exists():
                template_path = html_path
            else:
                # If template not found, try default fallback
                if template_name != 'default':
                    return self._get_template('default')
                else:
                    raise FileNotFoundError(f"Template not found: {template_name} (tried .hbs and .html)")
                    
            self._template_cache[template_name] = self._load_template(template_path)
        return self._template_cache[template_name]
        
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context.
        
        Args:
            template_name: Name of the template to render (without extension)
                          Tries .hbs first, then .html, then falls back to 'default'
            context: Dictionary of variables to pass to the template
            
        Returns:
            Rendered template string
            
        Raises:
            ValueError: If template rendering fails
        """
        try:
            template = self._get_template(template_name)
            return template(context)
        except Exception as e:
            raise ValueError(f"Failed to render template {template_name}: {e}")
            
    def clear_cache(self):
        """Clear the template cache."""
        self._template_cache.clear()
