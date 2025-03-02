"""Tests for the SiteBuilder class."""

import os
import re
import json
import pytest
from pathlib import Path
from datetime import datetime
from yoix.core import SiteBuilder

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    content_dir = tmp_path / "content"
    partials_dir = tmp_path / "includes" / "partials"
    templates_dir = tmp_path / "includes" / "templates"
    public_dir = tmp_path / "public"
    
    for dir in [content_dir, partials_dir, templates_dir, public_dir]:
        dir.mkdir(parents=True)
        
    return {
        'content_dir': content_dir,
        'partials_dir': partials_dir, 
        'templates_dir': templates_dir,
        'public_dir': public_dir
    }

@pytest.fixture
def config_with_dirs(temp_dirs):
    """Create a config dict with test directories."""
    return {
        'build': {
            'content_dir': str(temp_dirs['content_dir']),
            'partials_dir': str(temp_dirs['partials_dir']),
            'templates_dir': str(temp_dirs['templates_dir']),
            'public_dir': str(temp_dirs['public_dir'])
        },
        'info': {
            'base_url': 'https://test.com',
            'site_name': 'Test Site',
            'site_logo': '/img/logo.png',
            'author': 'Test Author'
        },
        'frontmatter': {
            'aliases': {
                'desc': 'description',
                'tags': 'keywords'
            }
        }
    }

@pytest.fixture
def site_builder(config_with_dirs):
    """Create a SiteBuilder instance for testing."""
    return SiteBuilder(config_with_dirs)

def create_test_files(temp_dirs):
    """Helper function to create test template files."""
    # Create post template
    post_template = temp_dirs['templates_dir'] / "post.hbs"
    post_template.write_text('''
        <div class="post">
            <h2>{{title}}</h2>
            <p>{{date.formatted}}</p>
            <p>{{meta.description}}</p>
            {{{content}}}
        </div>
    ''')
    
    # Create default template
    default_template = temp_dirs['templates_dir'] / "default.hbs"
    default_template.write_text('''
        <html>
            <head>
                <script type="application/ld+json">{{{jsonLdSchema}}}</script>
            </head>
            <body>
                <h1>{{title}}</h1>
                {{{content}}}
            </body>
        </html>
    ''')
    
    # Create blog-index template
    blog_index = temp_dirs['templates_dir'] / "blog-index.hbs"
    blog_index.write_text('''
        <html>
            <head>
                <title>{{title}}</title>
                <meta name="description" content="{{meta.description}}">
            </head>
            <body>
                <div class="posts">
                    {{#each posts}}
                        {{{this}}}
                    {{/each}}
                </div>
                <script type="application/ld+json">{{{schemas}}}</script>
            </body>
        </html>
    ''')

def create_test_post(path, title="Test Post", date="2025-02-23", description="Test Description"):
    """Helper function to create a test markdown post."""
    content = f"""---
title: {title}
date: {date}
desc: {description}
tags: ["test", "blog"]
layout: post
---

# {title}

This is a test post content.

![Test Image](test.png)
"""
    path.write_text(content)
    # Create a test image
    img_path = path.parent / "test.png"
    img_path.write_bytes(b"fake image data")
    return path

def test_init_with_config(site_builder, config_with_dirs):
    """Test SiteBuilder initialization with config dict."""
    assert str(site_builder.content_dir) == str(config_with_dirs['build']['content_dir'])
    assert str(site_builder.templates_dir) == str(config_with_dirs['build']['templates_dir'])
    assert str(site_builder.public_dir) == str(config_with_dirs['build']['public_dir'])
    assert site_builder.base_url == config_with_dirs['info']['base_url']
    assert site_builder.site_name == config_with_dirs['info']['site_name']
    assert site_builder.author == config_with_dirs['info']['author']

def test_init_with_missing_dirs(tmp_path):
    """Test SiteBuilder initialization with missing directories."""
    config = {
        'build': {
            'content_dir': str(tmp_path / "content"),
            'templates_dir': str(tmp_path / "templates"),
            'public_dir': str(tmp_path / "public"),
            'partials_dir': str(tmp_path / "partials")
        }
    }
    # Should not raise error as directories are created automatically
    builder = SiteBuilder(config)
    assert Path(config['build']['templates_dir']).exists()