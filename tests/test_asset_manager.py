"""Tests for the AssetManager class."""

import os
import shutil
import time
from pathlib import Path
import pytest
from yoix.asset import AssetManager

@pytest.fixture
def test_dirs(tmp_path):
    """Create test directories."""
    content_dir = tmp_path / "content"
    public_dir = tmp_path / "public"
    static_dir = content_dir / "static"
    theme_dir = tmp_path / "theme"
    
    for dir in [content_dir, public_dir, static_dir, theme_dir]:
        dir.mkdir(parents=True)
        
    return {
        'content_dir': content_dir,
        'public_dir': public_dir,
        'static_dir': static_dir,
        'theme_dir': theme_dir
    }

@pytest.fixture
def asset_manager(test_dirs):
    """Create an AssetManager instance."""
    return AssetManager(test_dirs['public_dir'], test_dirs['content_dir'])

def create_test_file(path, content=b"test content"):
    """Helper to create a test file with content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path

def test_copy_asset_relative_path(asset_manager, test_dirs):
    """Test copying an asset with a relative path."""
    # Create test image in content directory
    img_path = test_dirs['content_dir'] / "images" / "test.png"
    create_test_file(img_path)
    
    # Copy using relative path
    result = asset_manager.copy_asset("images/test.png")
    assert result is True
    
    # Check file was copied
    dest_path = test_dirs['public_dir'] / "images" / "test.png"
    assert dest_path.exists()
    assert dest_path.read_bytes() == img_path.read_bytes()

def test_copy_asset_absolute_path(asset_manager, test_dirs):
    """Test copying an asset with an absolute path."""
    # Create test file
    src_path = test_dirs['content_dir'] / "files" / "test.txt"
    create_test_file(src_path)
    
    # Copy using absolute path
    result = asset_manager.copy_asset(str(src_path))
    assert result is True
    
    # Check file was copied
    dest_path = test_dirs['public_dir'] / "files" / "test.txt"
    assert dest_path.exists()

def test_copy_asset_relative_to(asset_manager, test_dirs):
    """Test copying an asset relative to a specific directory."""
    # Create test file in a subdirectory
    base_dir = test_dirs['content_dir'] / "posts" / "my-post"
    img_path = base_dir / "images" / "test.jpg"
    create_test_file(img_path)
    
    # Copy relative to the post directory
    result = asset_manager.copy_asset("images/test.jpg", relative_to=base_dir)
    assert result is True
    
    # Check file was copied maintaining directory structure
    dest_path = test_dirs['public_dir'] / "posts" / "my-post" / "images" / "test.jpg"
    assert dest_path.exists()

def test_copy_asset_external_url(asset_manager):
    """Test handling of external URLs."""
    result = asset_manager.copy_asset("https://example.com/image.jpg")
    assert result is False

def test_copy_asset_nonexistent(asset_manager):
    """Test copying a nonexistent asset."""
    result = asset_manager.copy_asset("nonexistent.png")
    assert result is False

def test_copy_directory(asset_manager, test_dirs):
    """Test copying a directory of assets."""
    # Create test files
    files = [
        "css/style.css",
        "js/main.js",
        "images/logo.png",
        "images/bg.jpg"
    ]
    
    for file in files:
        create_test_file(test_dirs['static_dir'] / file)
    
    # Copy directory
    count = asset_manager.copy_directory(test_dirs['static_dir'])
    assert count == len(files)
    
    # Check all files were copied
    for file in files:
        assert (test_dirs['public_dir'] / file).exists()

def test_copy_directory_with_patterns(asset_manager, test_dirs):
    """Test copying a directory with specific patterns."""
    # Create various file types
    files = {
        "style.css": True,      # Should copy
        "script.js": True,      # Should copy
        "image.png": True,      # Should copy
        "data.json": False,     # Should not copy
        "config.yml": False     # Should not copy
    }
    
    for file, _ in files.items():
        create_test_file(test_dirs['theme_dir'] / file)
    
    # Copy with specific patterns
    patterns = ["*.css", "*.js", "*.png"]
    count = asset_manager.copy_directory(test_dirs['theme_dir'], patterns)
    assert count == 3
    
    # Verify correct files were copied
    for file, should_copy in files.items():
        dest = test_dirs['public_dir'] / file
        assert dest.exists() == should_copy

def test_copy_static_assets(asset_manager, test_dirs):
    """Test copying static assets."""
    # Create some static files
    files = ["css/style.css", "js/app.js", "images/logo.png"]
    for file in files:
        create_test_file(test_dirs['static_dir'] / file)
    
    # Copy static assets
    count = asset_manager.copy_static_assets()
    assert count == len(files)
    
    # Check files were copied
    for file in files:
        assert (test_dirs['public_dir'] / file).exists()

def test_copy_theme_assets(asset_manager, test_dirs):
    """Test copying theme assets."""
    # Create theme files
    theme_files = {
        "style.css": True,
        "script.js": True,
        "font.woff2": True,
        "logo.svg": True,
        "README.md": False,  # Should not copy
        "config.json": False  # Should not copy
    }
    
    for file, _ in theme_files.items():
        create_test_file(test_dirs['theme_dir'] / file)
    
    # Copy theme assets
    count = asset_manager.copy_theme_assets(test_dirs['theme_dir'])
    assert count == 4  # Only the allowed file types
    
    # Verify correct files were copied
    for file, should_copy in theme_files.items():
        dest = test_dirs['public_dir'] / file
        assert dest.exists() == should_copy

def test_clear_cache(asset_manager, test_dirs):
    """Test clearing the processed assets cache."""
    # Create and copy a file
    test_file = create_test_file(test_dirs['content_dir'] / "test.txt")
    asset_manager.copy_asset("test.txt")
    
    # Verify file is in cache
    dest_path = test_dirs['public_dir'] / "test.txt"
    assert str(dest_path) in asset_manager.processed_assets
    
    # Clear cache
    asset_manager.clear_cache()
    assert str(dest_path) not in asset_manager.processed_assets
    
    # Copy again - should add back to cache
    asset_manager.copy_asset("test.txt")
    assert str(dest_path) in asset_manager.processed_assets
