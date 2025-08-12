/**
 * Directory Plugin JavaScript
 * Provides interactive functionality for directory listings
 */

class DirectoryApp {
    constructor() {
        this.searchData = null;
        this.currentResults = [];
        this.filters = {
            category: '',
            location: '',
            type: '',
            rating: ''
        };
        this.sortBy = 'name';
        
        this.init();
    }
    
    async init() {
        try {
            // Load search data
            await this.loadSearchData();
            
            // Initialize search if on search page
            if (document.getElementById('searchInput')) {
                this.initSearch();
            }
            
            // Initialize any interactive features
            this.initInteractiveFeatures();
            
        } catch (error) {
            console.error('Failed to initialize directory app:', error);
        }
    }
    
    async loadSearchData() {
        try {
            const response = await fetch('/api/directory-search.json');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            this.searchData = await response.json();
        } catch (error) {
            console.error('Failed to load search data:', error);
            this.showError('Failed to load directory data');
        }
    }
    
    initSearch() {
        if (!this.searchData) {
            this.showError('Search data not available');
            return;
        }
        
        // Populate filter dropdowns
        this.populateFilters();
        
        // Set up event listeners
        this.setupSearchListeners();
        
        // Show all results initially
        this.currentResults = this.searchData.entities;
        this.displayResults();
    }
    
    populateFilters() {
        // Populate category filter
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter && this.searchData.categories) {
            this.searchData.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categoryFilter.appendChild(option);
            });
        }
        
        // Populate location filter
        const locationFilter = document.getElementById('locationFilter');
        if (locationFilter && this.searchData.locations) {
            this.searchData.locations.forEach(location => {
                const option = document.createElement('option');
                option.value = location;
                option.textContent = location;
                locationFilter.appendChild(option);
            });
        }
        
        // Populate type filter
        const typeFilter = document.getElementById('typeFilter');
        if (typeFilter && this.searchData.entity_types) {
            this.searchData.entity_types.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = this.capitalize(type);
                typeFilter.appendChild(option);
            });
        }
    }
    
    setupSearchListeners() {
        // Search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.performSearch();
            }, 300));
        }
        
        // Filter dropdowns
        ['categoryFilter', 'locationFilter', 'typeFilter', 'ratingFilter'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    this.updateFilter(id.replace('Filter', ''), element.value);
                    this.performSearch();
                });
            }
        });
        
        // Sort dropdown
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                this.sortBy = sortSelect.value;
                this.displayResults();
            });
        }
    }
    
    updateFilter(filterType, value) {
        this.filters[filterType] = value;
    }
    
    performSearch() {
        if (!this.searchData || !this.searchData.entities) {
            return;
        }
        
        const query = document.getElementById('searchInput')?.value.toLowerCase() || '';
        
        this.currentResults = this.searchData.entities.filter(entity => {
            // Text search
            if (query && !this.matchesQuery(entity, query)) {
                return false;
            }
            
            // Category filter
            if (this.filters.category && !entity.categories?.includes(this.filters.category)) {
                return false;
            }
            
            // Location filter
            if (this.filters.location && entity.location !== this.filters.location) {
                return false;
            }
            
            // Type filter
            if (this.filters.type && entity.type !== this.filters.type) {
                return false;
            }
            
            // Rating filter
            if (this.filters.rating) {
                const minRating = parseFloat(this.filters.rating);
                if (!entity.rating || entity.rating < minRating) {
                    return false;
                }
            }
            
            return true;
        });
        
        this.displayResults();
    }
    
    matchesQuery(entity, query) {
        // Check if query matches any search terms
        return entity.search_terms && entity.search_terms.some(term => 
            term.includes(query)
        );
    }
    
    displayResults() {
        const resultsContainer = document.getElementById('searchResults');
        const resultsCount = document.getElementById('resultsCount');
        const noResults = document.getElementById('noResults');
        
        if (!resultsContainer) return;
        
        // Sort results
        this.sortResults();
        
        // Update count
        if (resultsCount) {
            const count = this.currentResults.length;
            resultsCount.textContent = `${count} result${count !== 1 ? 's' : ''} found`;
        }
        
        // Show/hide no results message
        if (noResults) {
            noResults.style.display = this.currentResults.length === 0 ? 'block' : 'none';
        }
        
        // Render results
        resultsContainer.innerHTML = '';
        
        if (this.currentResults.length === 0) {
            return;
        }
        
        this.currentResults.forEach(entity => {
            const card = this.createEntityCard(entity);
            resultsContainer.appendChild(card);
        });
    }
    
    sortResults() {
        this.currentResults.sort((a, b) => {
            switch (this.sortBy) {
                case 'rating':
                    return (b.rating || 0) - (a.rating || 0);
                case 'location':
                    return (a.location || '').localeCompare(b.location || '');
                case 'name':
                default:
                    return a.name.localeCompare(b.name);
            }
        });
    }
    
    createEntityCard(entity) {
        const card = document.createElement('div');
        card.className = 'entity-card';
        card.setAttribute('data-entity-id', entity.id);
        
        let html = `
            <div class="entity-header">
                <h3 class="entity-name">
                    <a href="${entity.url}">${this.escapeHtml(entity.name)}</a>
                </h3>
                ${entity.rating ? `
                <div class="entity-rating">
                    <div class="stars">${'⭐'.repeat(Math.floor(entity.rating))}</div>
                    <span class="rating-number">(${entity.rating})</span>
                </div>
                ` : ''}
            </div>
            
            <div class="entity-meta">
                <div class="entity-type">${this.escapeHtml(entity.type)}</div>
                ${entity.location ? `<div class="entity-location">📍 ${this.escapeHtml(entity.location)}</div>` : ''}
                ${entity.price_range ? `<div class="entity-price">${this.escapeHtml(entity.price_range)}</div>` : ''}
            </div>
        `;
        
        if (entity.categories && entity.categories.length > 0) {
            html += '<div class="entity-categories">';
            entity.categories.forEach(category => {
                html += `<span class="category-tag">${this.escapeHtml(category)}</span>`;
            });
            html += '</div>';
        }
        
        html += `
            <div class="entity-actions">
                <a href="${entity.url}" class="btn btn-primary btn-sm">View Details</a>
            </div>
        `;
        
        card.innerHTML = html;
        return card;
    }
    
    initInteractiveFeatures() {
        // Add smooth scrolling to anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            });
        });
        
        // Add click tracking for analytics (if needed)
        document.querySelectorAll('.entity-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't track if clicking on a link
                if (e.target.tagName === 'A') return;
                
                const entityId = card.getAttribute('data-entity-id');
                this.trackEntityView(entityId);
            });
        });
    }
    
    trackEntityView(entityId) {
        // Placeholder for analytics tracking
        console.log('Entity viewed:', entityId);
        
        // Example: Send to analytics service
        // gtag('event', 'entity_view', { entity_id: entityId });
    }
    
    showError(message) {
        console.error('Directory error:', message);
        
        // Show user-friendly error message
        const container = document.getElementById('searchResults') || document.querySelector('.directory-grid');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Oops! Something went wrong</h3>
                    <p>${message}</p>
                    <button onclick="location.reload()" class="btn btn-primary">Try Again</button>
                </div>
            `;
        }
    }
    
    // Utility functions
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the directory app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.directoryApp = new DirectoryApp();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DirectoryApp;
}