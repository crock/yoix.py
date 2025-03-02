"""Default configuration values for Yoix."""

DEFAULT_CONFIG = {
    'build': {
        'partials_dir': 'includes/partials',
        'templates_dir': 'includes/templates',
        'public_dir': 'public',
        'content_dir': 'content'
    },
    'info': {
        'base_url': 'https://example.com',
        'site_name': 'My Site',
        'site_logo': '/img/logo.png',
        'author': 'Site Author'
    },
    'frontmatter': {
        'aliases': {
            'title': ['name', 'heading'],
            'date': ['published', 'created_at', 'publishDate'],
            'description': ['desc', 'summary'],
            'author': ['writer', 'creator'],
            'slug': ['customSlug', 'permalink']
        }
    }
}
