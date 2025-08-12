"""
Directory Builder Plugin for Yoix

This plugin transforms Yoix into a powerful directory website generator,
enabling creation of business directories, member listings, resource catalogs, and more.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

from yoix.pm import YoixPlugin


class DirectoryBuilder(YoixPlugin):
    """Main plugin class that builds directory functionality."""
    
    def __init__(self, name: str, version: str, description: str = "", developer: str = ""):
        super().__init__(name, version, description, developer)
        
        # Directory data storage
        self.entities: List[Dict[str, Any]] = []
        self.categories: Set[str] = set()
        self.locations: Set[str] = set()
        self.entity_types: Set[str] = set()
        self.features: Set[str] = set()
        
        # Category hierarchy (parent -> children)
        self.category_tree: Dict[str, Set[str]] = defaultdict(set)
        
        # Location hierarchy (state -> cities)
        self.location_tree: Dict[str, Set[str]] = defaultdict(set)
        
        # Search index data
        self.search_index: Dict[str, Any] = {}
        
    def on_site_build_start(self, site_builder):
        """Initialize directory processing when site build starts."""
        self.log('info', 'Starting directory website build')
        self.entities.clear()
        self.categories.clear()
        self.locations.clear()
        self.entity_types.clear()
        self.features.clear()
        self.category_tree.clear()
        self.location_tree.clear()
        
    def on_post_process(self, post_data, site_builder):
        """Process posts for directory entities."""
        self.log('info', f'Processing post: {post_data.get("title", "Unknown")}')
        if self._is_directory_entity(post_data):
            self.log('info', f'Found directory entity in post: {post_data.get("name", "Unknown")}')
            entity = self._process_directory_entity(post_data)
            if entity:
                self.entities.append(entity)
                self._extract_taxonomy_data(entity)
                self.log('info', f'Processed directory entity: {entity.get("name", "Unknown")}')
        else:
            self.log('info', f'Not a directory entity (no entity_type): {post_data.get("title", "Unknown")}')
        
        return post_data
        
    def on_page_process(self, page_data, site_builder):
        """Process pages for directory entities."""
        self.log('info', f'Processing page: {page_data.get("title", "Unknown")}')
        self.log('info', f'Page data keys: {list(page_data.keys())}')
        meta = page_data.get('meta', {})
        self.log('info', f'Meta keys: {list(meta.keys())}')
        self.log('info', f'Entity type value: {page_data.get("entity_type", "NOT_FOUND")}')
        self.log('info', f'Meta entity type: {meta.get("entity_type", "NOT_FOUND")}')
        
        if self._is_directory_entity(page_data):
            self.log('info', f'Found directory entity in page: {page_data.get("name", "Unknown")}')
            entity = self._process_directory_entity(page_data)
            if entity:
                self.entities.append(entity)
                self._extract_taxonomy_data(entity)
                self.log('info', f'Processed directory entity: {entity.get("name", "Unknown")}')
        else:
            self.log('info', f'Not a directory entity (no entity_type): {page_data.get("title", "Unknown")}')
        
        return page_data
        
    def on_site_build_end(self, site_builder):
        """Generate directory pages and search index after processing all content."""
        print("DEBUG: Directory plugin on_site_build_end called!")
        print(f"DEBUG: site_builder.datasets available: {hasattr(site_builder, 'datasets')}")
        
        if hasattr(site_builder, 'datasets'):
            print(f"DEBUG: Available datasets: {list(site_builder.datasets.keys())}")
            if 'businesses' in site_builder.datasets:
                dataset = site_builder.datasets['businesses']
                print(f"DEBUG: Businesses dataset has {len(dataset.get('rows', []))} rows")
        else:
            print("DEBUG: No datasets attribute on site_builder")
        
        print(f"DEBUG: Current entities from frontmatter: {len(self.entities)}")
        
        # Check for businesses dataset first - prioritize dataset over frontmatter entities
        if hasattr(site_builder, 'datasets') and 'businesses' in site_builder.datasets:
            print("DEBUG: Using businesses dataset for directory!")
            self.log('info', 'Using businesses dataset for directory (overriding frontmatter entities)')
            self._process_businesses_dataset(site_builder)
        elif self.entities:
            print("DEBUG: Using frontmatter entities")
            self.log('info', f'Processing {len(self.entities)} directory entities from frontmatter - datasets available: {hasattr(site_builder, "datasets")}, businesses in datasets: {"businesses" in getattr(site_builder, "datasets", {})}')
            # Sort entities by name
            self.entities.sort(key=lambda x: x.get('name', '').lower())
        else:
            print("DEBUG: No entities or datasets found")
            self.log('info', 'No directory entities found and no businesses dataset')
            return
        
        # Build search index
        self._build_search_index()
        
        # Generate directory pages
        self._generate_directory_pages(site_builder)
        
        # Generate API files
        self._generate_api_files(site_builder)
        
        self.log('info', f'Directory build complete: {len(self.entities)} entities, '
                         f'{len(self.categories)} categories, {len(self.locations)} locations')
                         
    def _process_businesses_dataset(self, site_builder):
        """Convert businesses dataset to directory entities."""
        dataset = site_builder.datasets['businesses']
        mapping = dataset.get('mapping', {})
        rows = dataset.get('rows', [])
        
        self.log('info', f'Processing {len(rows)} businesses from dataset')
        self.log('info', f'Dataset mapping: {mapping}')
        
        # Clear existing entities since we're using dataset
        self.entities = []
        self.categories = set()
        self.locations = set()
        self.tags = set()
        
        for row in rows:
            entity = self._convert_business_to_entity(row, mapping)
            if entity:
                self.entities.append(entity)
                self._extract_taxonomy_data(entity)
        
        self.log('info', f'Converted {len(self.entities)} businesses to entities')
        
    def _convert_business_to_entity(self, business_row, mapping):
        """Convert a business row to directory entity format."""
        try:
            # Get mapped field values or fallback to original headers
            def get_value(canonical_field, fallback_headers=None):
                # Try mapped header first
                if canonical_field in mapping:
                    mapped_header = mapping[canonical_field]
                    if mapped_header in business_row:
                        return business_row[mapped_header]
                
                # Try fallback headers
                if fallback_headers:
                    for header in fallback_headers:
                        if header in business_row:
                            return business_row[header]
                
                return None
            
            # Required field: name
            name = get_value('name', ['business_name', 'name', 'title'])
            if not name:
                self.log('warning', 'Business missing name field')
                return None
            
            # Build entity
            entity = {
                'id': self._generate_entity_id(name),
                'name': name,
                'type': 'business',
                'title': name,
                'content': get_value('description', ['description', 'about', 'summary']) or '',
                'url': f'/directory/business/{self._generate_entity_id(name)}/',
                'created_date': datetime.now().isoformat()
            }
            
            # Add business-specific fields
            if address := get_value('address', ['address', 'street_address', 'street']):
                entity['address'] = address
            if city := get_value('city', ['city']):
                entity['city'] = city
            if state := get_value('state', ['state', 'province']):
                entity['state'] = state
            if postal_code := get_value('postal_code', ['zip_code', 'zip', 'postal_code']):
                entity['postal_code'] = postal_code
            if phone := get_value('phone', ['phone', 'phone_number', 'telephone']):
                entity['phone'] = phone
            if email := get_value('email', ['email', 'email_address']):
                entity['email'] = email
            if website := get_value('website', ['website', 'website_url', 'url']):
                entity['website'] = website
            if category := get_value('category', ['category', 'type']):
                entity['category'] = category
            if hours := get_value('hours', ['hours', 'opening_hours']):
                entity['hours'] = hours
            if rating := get_value('rating', ['rating', 'stars']):
                try:
                    entity['rating'] = float(rating)
                except (ValueError, TypeError):
                    pass
            
            # Create location string for taxonomy
            location_parts = [entity.get('city'), entity.get('state')]
            location = ', '.join(p for p in location_parts if p)
            if location:
                entity['location'] = location
            
            return entity
            
        except Exception as e:
            self.log('error', f'Error converting business to entity: {e}')
            return None
                         
    def _is_directory_entity(self, content: Dict[str, Any]) -> bool:
        """Check if content represents a directory entity."""
        return content.get('entity_type') is not None
        
    def _process_directory_entity(self, content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and validate a directory entity."""
        entity_type = content.get('entity_type')
        if not entity_type:
            return None
            
        # Required fields
        name = content.get('name')
        if not name:
            self.log('warning', f'Directory entity missing required "name" field')
            return None
            
        # Build entity data
        entity = {
            'id': self._generate_entity_id(name),
            'name': name,
            'type': entity_type,
            'title': content.get('title', name),
            'content': content.get('content', ''),
            'url': content.get('url_path', ''),
            'created_date': content.get('date', {}).get('iso', datetime.now().isoformat())
        }
        
        # Optional fields with validation
        self._add_optional_fields(entity, content)
        
        return entity
        
    def _generate_entity_id(self, name: str) -> str:
        """Generate a URL-safe ID from entity name."""
        # Convert to lowercase, replace spaces/special chars with hyphens
        entity_id = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
        entity_id = re.sub(r'\s+', '-', entity_id)
        entity_id = re.sub(r'-+', '-', entity_id)
        return entity_id.strip('-')
        
    def _add_optional_fields(self, entity: Dict[str, Any], content: Dict[str, Any]):
        """Add optional fields to entity with validation."""
        # Category handling
        categories = content.get('category', [])
        if isinstance(categories, str):
            categories = [categories]
        if categories:
            entity['categories'] = categories
            
        # Location handling
        address = content.get('address')
        if address:
            entity['address'] = address
            entity['location'] = self._extract_location_from_address(address)
            
        # Contact information
        for field in ['phone', 'email', 'website']:
            value = content.get(field)
            if value:
                entity[field] = value
                
        # Business-specific fields
        hours = content.get('hours')
        if hours and isinstance(hours, dict):
            entity['hours'] = hours
            
        rating = content.get('rating')
        if rating is not None:
            try:
                entity['rating'] = float(rating)
            except (ValueError, TypeError):
                self.log('warning', f'Invalid rating for {entity["name"]}: {rating}')
                
        price_range = content.get('price_range')
        if price_range:
            entity['price_range'] = price_range
            
        # Features and tags
        features = content.get('features', [])
        if isinstance(features, str):
            features = [features]
        if features:
            entity['features'] = features
            
        tags = content.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        if tags:
            entity['tags'] = tags
            
        # Geographic coordinates
        lat = content.get('latitude')
        lng = content.get('longitude')
        if lat is not None and lng is not None:
            try:
                entity['coordinates'] = {
                    'latitude': float(lat),
                    'longitude': float(lng)
                }
            except (ValueError, TypeError):
                self.log('warning', f'Invalid coordinates for {entity["name"]}: {lat}, {lng}')
                
    def _extract_location_from_address(self, address: str) -> str:
        """Extract city/state from address for location categorization."""
        # Simple regex to extract "City, State" pattern
        match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})', address)
        if match:
            city, state = match.groups()
            return f"{city.strip()}, {state}"
        return address
        
    def _extract_taxonomy_data(self, entity: Dict[str, Any]):
        """Extract categories, locations, and other taxonomy data from entity."""
        # Categories - handle both single category (string) and multiple categories (list)
        categories = []
        if 'categories' in entity:
            # Multiple categories (list)
            categories = entity.get('categories', [])
        elif 'category' in entity:
            # Single category (string) - convert to list
            category = entity.get('category')
            if category:
                categories = [category]
        
        for category in categories:
            self.categories.add(category)
            # Build category hierarchy (assume categories are hierarchical if separated by >)
            if ' > ' in category:
                parts = [part.strip() for part in category.split(' > ')]
                for i in range(len(parts) - 1):
                    parent = ' > '.join(parts[:i+1])
                    child = ' > '.join(parts[:i+2])
                    self.category_tree[parent].add(child)
                    
        # Locations
        location = entity.get('location')
        if location:
            self.locations.add(location)
            # Build location hierarchy (City, State)
            if ', ' in location:
                city, state = location.split(', ', 1)
                self.location_tree[state].add(location)
                
        # Entity types
        self.entity_types.add(entity['type'])
        
        # Features
        features = entity.get('features', [])
        for feature in features:
            self.features.add(feature)
            
    def _build_search_index(self):
        """Build search index for client-side search functionality."""
        search_entities = []
        
        for entity in self.entities:
            # Build searchable terms
            search_terms = [entity['name'].lower()]
            
            # Add categories to search terms
            categories = entity.get('categories', [])
            search_terms.extend([cat.lower() for cat in categories])
            
            # Add location to search terms
            location = entity.get('location', '')
            if location:
                search_terms.append(location.lower())
                
            # Add features to search terms
            features = entity.get('features', [])
            search_terms.extend([feat.lower() for feat in features])
            
            # Add tags to search terms
            tags = entity.get('tags', [])
            search_terms.extend([tag.lower() for tag in tags])
            
            search_entity = {
                'id': entity['id'],
                'name': entity['name'],
                'type': entity['type'],
                'categories': categories,
                'location': location,
                'rating': entity.get('rating'),
                'price_range': entity.get('price_range'),
                'url': entity['url'],
                'search_terms': list(set(search_terms))  # Remove duplicates
            }
            
            search_entities.append(search_entity)
            
        self.search_index = {
            'entities': search_entities,
            'categories': sorted(list(self.categories)),
            'locations': sorted(list(self.locations)),
            'entity_types': sorted(list(self.entity_types)),
            'features': sorted(list(self.features)),
            'category_tree': {k: list(v) for k, v in self.category_tree.items()},
            'location_tree': {k: list(v) for k, v in self.location_tree.items()},
            'generated_at': datetime.now().isoformat()
        }
        
    def _generate_directory_pages(self, site_builder):
        """Generate directory listing pages."""
        if not self.api:
            self.log('error', 'PluginApi not available')
            return
            
        public_dir = self.api.get_public_dir()
        
        # Main directory index
        directory_stats = {
            'total_categories': len(self.categories),
            'total_locations': len(self.locations),
            'categories': list(self.categories),
            'locations': list(self.locations)
        }
        
        self._write_directory_page(
            public_dir / 'directory' / 'index.html',
            'Directory',
            'directory-index',
            {
                'entities': self.entities, 
                'stats': self._get_directory_stats(),
                'directory_stats': directory_stats
            }
        )
        
        # Category pages
        for category in self.categories:
            # Handle both single category (string) and multiple categories (list)
            category_entities = []
            for e in self.entities:
                if 'categories' in e and category in e.get('categories', []):
                    category_entities.append(e)
                elif 'category' in e and e.get('category') == category:
                    category_entities.append(e)
            if category_entities:
                category_slug = self._generate_entity_id(category)
                self._write_directory_page(
                    public_dir / 'directory' / 'categories' / category_slug / 'index.html',
                    f'{category} Directory',
                    'directory-category',
                    {'category': category, 'entities': category_entities}
                )
                
        # Location pages
        for location in self.locations:
            location_entities = [e for e in self.entities if e.get('location') == location]
            if location_entities:
                location_slug = self._generate_entity_id(location)
                self._write_directory_page(
                    public_dir / 'directory' / 'locations' / location_slug / 'index.html',
                    f'{location} Directory',
                    'directory-location',
                    {'location': location, 'entities': location_entities}
                )
                
        # Entity type pages
        for entity_type in self.entity_types:
            type_entities = [e for e in self.entities if e['type'] == entity_type]
            if type_entities:
                type_slug = self._generate_entity_id(entity_type)
                self._write_directory_page(
                    public_dir / 'directory' / 'types' / type_slug / 'index.html',
                    f'{entity_type.title()} Directory',
                    'directory-type',
                    {'entity_type': entity_type, 'entities': type_entities}
                )
                
        # Search page
        self._write_directory_page(
            public_dir / 'directory' / 'search' / 'index.html',
            'Search Directory',
            'directory-search',
            {'search_enabled': True}
        )
        
    def _write_directory_page(self, path, title, template_type, data):
        """Write a directory page to the public directory."""
        if not self.api:
            self.log('error', 'PluginApi not available')
            return
            
        try:
            # Prepare template data
            template_data = {
                'title': title,
                'directory_data': data,
                'template_type': template_type
            }
            
            # Generate simple HTML for now (will be enhanced with templates)
            html = self._generate_directory_html(template_data)
            
            # Convert path to relative path for PluginApi
            public_dir = self.api.get_public_dir()
            relative_path = path.relative_to(public_dir)
            
            # Write file using PluginApi
            self.api.write_public_file(str(relative_path), html)
                
        except Exception as e:
            self.log('error', f'Failed to write directory page {path}: {e}')
            
    def _generate_directory_html(self, data) -> str:
        """Generate HTML for directory pages (basic implementation)."""
        title = data['title']
        directory_data = data['directory_data']
        template_type = data['template_type']
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .directory-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .entity-card {{ border: 1px solid #ddd; padding: 20px; border-radius: 8px; }}
        .entity-name {{ font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }}
        .entity-meta {{ color: #666; font-size: 0.9em; }}
        .categories {{ margin: 10px 0; }}
        .category-tag {{ background: #e9ecef; padding: 2px 8px; border-radius: 4px; margin-right: 5px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""
        
        if template_type == 'directory-index':
            stats = directory_data.get('stats', {})
            html += f"""
    <div class="directory-stats">
        <p>Total Entities: {stats.get('total_entities', 0)}</p>
        <p>Categories: {stats.get('total_categories', 0)}</p>
        <p>Locations: {stats.get('total_locations', 0)}</p>
    </div>
"""
            
        entities = directory_data.get('entities', [])
        if entities:
            html += '<div class="directory-grid">'
            for entity in entities:
                html += self._generate_entity_card_html(entity)
            html += '</div>'
        else:
            html += '<p>No entities found.</p>'
            
        html += """
</body>
</html>"""
        
        return html
        
    def _generate_entity_card_html(self, entity: Dict[str, Any]) -> str:
        """Generate HTML for an entity card."""
        name = entity.get('name', 'Unknown')
        entity_type = entity.get('type', 'entity')
        location = entity.get('location', '')
        rating = entity.get('rating')
        categories = entity.get('categories', [])
        
        html = f'<div class="entity-card">'
        html += f'<div class="entity-name">{name}</div>'
        html += f'<div class="entity-meta">Type: {entity_type}</div>'
        
        if location:
            html += f'<div class="entity-meta">Location: {location}</div>'
            
        if rating is not None:
            html += f'<div class="entity-meta">Rating: {rating}/5</div>'
            
        if categories:
            html += '<div class="categories">'
            for category in categories:
                html += f'<span class="category-tag">{category}</span>'
            html += '</div>'
            
        html += '</div>'
        return html
        
    def _get_directory_stats(self) -> Dict[str, int]:
        """Get directory statistics."""
        return {
            'total_entities': len(self.entities),
            'total_categories': len(self.categories),
            'total_locations': len(self.locations),
            'total_types': len(self.entity_types)
        }
        
    def _generate_api_files(self, site_builder):
        """Generate API files for search and data access."""
        if not self.api:
            self.log('error', 'PluginApi not available')
            return
            
        # Search index
        try:
            search_json = json.dumps(self.search_index, indent=2, ensure_ascii=False)
            self.api.write_public_file('api/directory-search.json', search_json)
        except Exception as e:
            self.log('error', f'Failed to write search index: {e}')
            
        # Full directory data
        try:
            directory_api = {
                'entities': self.entities,
                'categories': list(self.categories),
                'locations': list(self.locations),
                'entity_types': list(self.entity_types),
                'generated_at': datetime.now().isoformat()
            }
            directory_json = json.dumps(directory_api, indent=2, ensure_ascii=False)
            self.api.write_public_file('api/directory.json', directory_json)
        except Exception as e:
            self.log('error', f'Failed to write directory API: {e}')


# Plugin instance - this is what gets loaded by the plugin manager
Plugin = DirectoryBuilder