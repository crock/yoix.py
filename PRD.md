# Product Requirements Document (PRD)
**Product Name:** Yoix — Static Directory Generator (SDG)  
**Version:** 1.0  
**Author:** Alex Crocker  
**Date:** 2025-08-09

## 1. Purpose
The purpose of this project is to build a static site generator tailored for directory-style websites (e.g., local business listings, service provider directories, property listings) rather than blogs. While most static site generators like Jekyll, Hugo, or Eleventy are optimized for chronological blog posts, this tool will focus on structured, searchable, and categorized listings with directory-specific templates and data handling.

The goal is to make it easy to:

- Create directory listings from structured data (YAML, JSON, CSV, or API import)
- Automatically generate category and location pages
- Provide fast, SEO-friendly, mobile-responsive pages without the complexity of a dynamic backend

## 2. Objectives
- Deliver a developer-friendly CLI-based generator
- Support bulk import of listings from structured data sources
- Output a fully static, CDN-friendly site with no server dependencies
- Include search, filtering, and pagination without requiring a backend
- Provide SEO-ready markup and metadata per listing and category
- Allow custom themes and templates for branding

## 3. Target Users
- Local business directories (e.g., restaurants, services, attractions)
- Niche industry directories (e.g., tech startups, attorneys, contractors)
- Event listings (e.g., local festivals, conferences)
- Real estate / property directories
- Membership or alumni directories

## 4. Key Features

### 4.1 Data Input
- Support for CSV, JSON, or YAML input files
- Optional API importer for live data sync (v2 feature)
- Schema definition file to map data fields to listing template variables
- Support for multi-language fields

### 4.2 Content Generation
- Auto-generate listing detail pages (one per item)
- Auto-generate category pages (grouped by category field)
- Auto-generate location pages (grouped by city, state, country)
- Auto-generate tag pages (if tags are provided in data)
- Pagination for categories and search results

### 4.3 Search & Filtering (Static)
- JavaScript-based client-side search
- Client-side filtering by category, location, tags
- Instant filtering without page reloads
- Optional fuzzy search

### 4.4 Theming & Templates
- Template system using Liquid, Handlebars, or similar
- Starter themes for common directory layouts
- Theme variables for branding (colors, fonts, logos)
- Support for custom templates for detail and list pages

### 4.5 SEO & Performance
- Auto-generate sitemap.xml and robots.txt
- Structured data (schema.org) for LocalBusiness or relevant schema type
- Meta titles, descriptions per listing and category
- Optimized images with automatic resizing and WebP support
- Clean, SEO-friendly URLs:
  - `/category/restaurants/`
  - `/location/new-york/`
  - `/listing/the-best-pizza-place/`

### 4.6 Deployment
- Output is fully static HTML/CSS/JS
- Compatible with Netlify, Vercel, GitHub Pages, Cloudflare Pages
- CLI command: `sdg build`
- Optional `sdg serve` for local dev preview

### 4.7 Admin & Updates
- Command to add, update, or remove listings without full rebuild (incremental builds)
- Support for Git-based content workflow
- Optional web-based admin (future)

## 5. Technical Requirements
- Written in Node.js (>= 18)
- Support Windows, macOS, Linux
- Modular architecture for easy plugin development
- Use a templating engine (Liquid/Handlebars)
- Use a lightweight JS search library (e.g., Lunr.js, Fuse.js)
- Image optimization pipeline (Sharp or similar)
- Configurable config.yml for site settings

## 6. Constraints & Assumptions
- No dynamic backend — all search/filtering is client-side
- Must handle at least 50,000 listings efficiently
- Build times under 5 minutes for up to 10,000 listings
- All themes are mobile responsive by default

## 7. Success Metrics
- A non-technical user can build a directory with < 10 CLI commands
- Pages load in < 1s on average via CDN
- SEO Lighthouse score ≥ 90
- Can handle at least 1,000 pages with no performance degradation

## 8. Milestones

### MVP
- CSV/YAML import
- Listing, category, and location pages
- Client-side search & filtering
- One default responsive theme
- Sitemap & SEO meta support

### Future Enhancements
- API data imports
- Multi-language support
- Admin panel for managing listings
- Map integration (Leaflet.js / Mapbox)

