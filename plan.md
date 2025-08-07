# Directory Website Plugin Plan

## Overview
Create a "Directory Builder" plugin that transforms Yoix into a powerful directory website generator. This plugin would enable users to create business directories, resource listings, member directories, or any categorized collection of entities.

## Core Features

### 1. Entity Management
- **Entity Types**: Define custom entity types (businesses, people, resources, events, etc.)
- **Custom Fields**: Add structured data fields (address, phone, email, website, categories, ratings)
- **Frontmatter Schema**: Extend frontmatter with directory-specific fields
- **Data Validation**: Ensure required fields are present and properly formatted

### 2. Categorization & Taxonomy
- **Categories**: Hierarchical category system (e.g., Restaurants > Italian > Pizza)
- **Tags**: Flexible tagging system for cross-cutting concerns
- **Location-based**: Geographic categorization (city, state, region)
- **Custom Taxonomies**: User-defined classification systems

### 3. Search & Discovery
- **Search Index**: Generate client-side search index (JSON)
- **Faceted Search**: Filter by category, location, rating, price range, etc.
- **Auto-complete**: Search suggestions based on entity names and categories
- **Advanced Filters**: Date ranges, custom field filters

### 4. Directory Views & Layouts
- **List Views**: Table-style listings with sortable columns
- **Grid Views**: Card-based layouts with images and key info
- **Map Integration**: Generate map data for location-based entities
- **Detail Pages**: Rich individual entity pages with all metadata

### 5. Data Enhancement
- **SEO Optimization**: Generate structured data (JSON-LD) for each entity
- **Social Media**: Open Graph and Twitter Card metadata
- **Contact Info**: Structured contact information with vCard support
- **Business Hours**: Standardized hours format with timezone support

### 6. Analytics & Features
- **View Tracking**: Generate analytics-friendly markup
- **Featured Listings**: Promote specific entities
- **Rating System**: Support for star ratings and reviews
- **Contact Forms**: Generate contact forms for each entity

## Technical Implementation

### Plugin Structure
```
directory-builder.yoixplugin
├── info.json
├── main.py
├── templates/
│   ├── directory-list.hbs
│   ├── directory-grid.hbs
│   ├── directory-detail.hbs
│   └── directory-search.hbs
├── assets/
│   ├── directory.css
│   ├── directory.js
│   └── search.js
└── schemas/
    ├── business.json
    ├── person.json
    └── event.json
```

### Data Processing Flow
1. **Entity Detection**: Scan content for directory entities based on frontmatter
2. **Data Validation**: Validate against entity schemas
3. **Categorization**: Process categories and build taxonomy
4. **Index Generation**: Create searchable indexes
5. **Page Generation**: Create directory listing pages
6. **Search Assets**: Generate search JavaScript and data files

### Entity Example (Markdown File)
```markdown
---
entity_type: business
name: "Joe's Pizza Palace"
category: ["Restaurants", "Pizza", "Italian"]
address: "123 Main St, Springfield, IL 62701"
phone: "+1-555-0123"
email: "info@joespizza.com"
website: "https://joespizza.com"
hours:
  monday: "11:00-22:00"
  tuesday: "11:00-22:00"
  wednesday: "11:00-22:00"
  thursday: "11:00-22:00"
  friday: "11:00-23:00"
  saturday: "11:00-23:00"
  sunday: "12:00-21:00"
rating: 4.5
price_range: "$$"
features: ["delivery", "takeout", "outdoor_seating"]
latitude: 39.8014
longitude: -89.6436
---

# Joe's Pizza Palace

Family-owned pizza restaurant serving authentic Italian cuisine since 1987. 
Famous for our wood-fired pizzas and homemade pasta.

## Specialties
- Wood-fired Margherita Pizza
- Homemade Lasagna
- Authentic Tiramisu
```

### Generated Directory Features
- **Category Pages**: `/directory/restaurants/`, `/directory/restaurants/pizza/`
- **Location Pages**: `/directory/springfield-il/`, `/directory/locations/`
- **Search Page**: `/directory/search/` with JavaScript-powered search
- **Entity Pages**: `/directory/businesses/joes-pizza-palace/`
- **API Endpoints**: `/api/directory.json`, `/api/search-index.json`

### Search Index Structure
```json
{
  "entities": [
    {
      "id": "joes-pizza-palace",
      "name": "Joe's Pizza Palace",
      "type": "business",
      "category": ["Restaurants", "Pizza", "Italian"],
      "location": "Springfield, IL",
      "rating": 4.5,
      "url": "/directory/businesses/joes-pizza-palace/",
      "searchTerms": ["pizza", "italian", "restaurant", "springfield"]
    }
  ],
  "categories": ["Restaurants", "Pizza", "Italian"],
  "locations": ["Springfield, IL"],
  "features": ["delivery", "takeout", "outdoor_seating"]
}
```

## Integration Points

### With PluginApi
- Use `add_custom_field()` to enhance entity data
- Use `write_public_file()` to generate search indexes and API files
- Use `render_template()` for directory page layouts
- Use `cache_set/get()` for expensive operations like geocoding

### With Template System
- Register custom Handlebars helpers for directory features
- Create reusable directory components
- Generate structured data markup

### Security Considerations
- Validate all entity data to prevent XSS
- Sanitize user-generated content
- Rate limiting for search API if implemented server-side

## Use Cases

1. **Business Directory**: Local business listings with categories, reviews, hours
2. **Member Directory**: Organization member profiles with skills, contact info
3. **Resource Directory**: Tools, services, or educational resources with ratings
4. **Event Directory**: Recurring events with dates, locations, categories
5. **Property Directory**: Real estate or rental listings with photos, specs
6. **Service Provider Directory**: Freelancers, contractors, professionals

## Development Phases

### Phase 1: Core Entity Processing
- Entity detection and validation
- Basic category system
- Simple list/grid views

### Phase 2: Search & Discovery
- Search index generation
- Client-side search implementation
- Faceted filtering

### Phase 3: Advanced Features
- Map integration
- Rating system
- Contact forms
- Analytics markup

### Phase 4: Templates & Themes
- Professional directory templates
- Mobile-responsive layouts
- Customizable styling

This plugin would position Yoix as a serious contender in the directory/listing website space, competing with specialized directory builders while maintaining the simplicity and flexibility of a static site generator.