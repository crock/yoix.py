"""Plugin manager module for Yoix."""

from .pm import PluginManager, YoixPlugin
from .security import SecurityError, add_allowed_module, remove_allowed_module

__all__ = ['PluginManager', 'YoixPlugin', 'SecurityError', 'add_allowed_module', 'remove_allowed_module']
