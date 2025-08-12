/**
 * Directory Search Enhancement
 * Additional search functionality and autocomplete
 */

class DirectorySearch {
    constructor(directoryApp) {
        this.app = directoryApp;
        this.autocompleteResults = [];
        this.selectedIndex = -1;
        
        this.init();
    }
    
    init() {
        this.setupAutocomplete();
        this.setupAdvancedSearch();
    }
    
    setupAutocomplete() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;
        
        // Create autocomplete dropdown
        this.createAutocompleteDropdown();
        
        // Add event listeners
        searchInput.addEventListener('input', (e) => {
            this.handleAutocompleteInput(e.target.value);
        });
        
        searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                this.hideAutocomplete();
            }
        });
    }
    
    createAutocompleteDropdown() {
        const searchBox = document.querySelector('.search-box');
        if (!searchBox) return;
        
        const dropdown = document.createElement('div');
        dropdown.className = 'autocomplete-dropdown';
        dropdown.id = 'autocompleteDropdown';
        dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e5e7eb;
            border-top: none;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        
        searchBox.appendChild(dropdown);
    }
    
    handleAutocompleteInput(query) {
        if (!query || query.length < 2) {
            this.hideAutocomplete();
            return;
        }
        
        this.generateAutocompleteResults(query.toLowerCase());
        this.displayAutocompleteResults();
    }
    
    generateAutocompleteResults(query) {
        if (!this.app.searchData) return;
        
        const results = new Set();
        const maxResults = 8;
        
        // Search in entity names
        this.app.searchData.entities.forEach(entity => {
            if (entity.name.toLowerCase().includes(query)) {
                results.add({
                    type: 'entity',
                    text: entity.name,
                    subtitle: entity.location || entity.type,
                    action: () => this.selectEntity(entity)
                });
            }
        });
        
        // Search in categories
        this.app.searchData.categories.forEach(category => {
            if (category.toLowerCase().includes(query)) {
                results.add({
                    type: 'category',
                    text: category,
                    subtitle: 'Category',
                    action: () => this.selectCategory(category)
                });
            }
        });
        
        // Search in locations
        this.app.searchData.locations.forEach(location => {
            if (location.toLowerCase().includes(query)) {
                results.add({
                    type: 'location',
                    text: location,
                    subtitle: 'Location',
                    action: () => this.selectLocation(location)
                });
            }
        });
        
        this.autocompleteResults = Array.from(results).slice(0, maxResults);
        this.selectedIndex = -1;
    }
    
    displayAutocompleteResults() {
        const dropdown = document.getElementById('autocompleteDropdown');
        if (!dropdown) return;
        
        if (this.autocompleteResults.length === 0) {
            this.hideAutocomplete();
            return;
        }
        
        dropdown.innerHTML = '';
        
        this.autocompleteResults.forEach((result, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.style.cssText = `
                padding: 12px 20px;
                cursor: pointer;
                border-bottom: 1px solid #f3f4f6;
                transition: background-color 0.2s;
            `;
            
            item.innerHTML = `
                <div style="font-weight: 500; color: #374151;">${this.escapeHtml(result.text)}</div>
                <div style="font-size: 0.85em; color: #6b7280;">${this.escapeHtml(result.subtitle)}</div>
            `;
            
            item.addEventListener('click', () => {
                result.action();
                this.hideAutocomplete();
            });
            
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });
            
            dropdown.appendChild(item);
        });
        
        dropdown.style.display = 'block';
    }
    
    handleKeyNavigation(e) {
        const dropdown = document.getElementById('autocompleteDropdown');
        if (!dropdown || dropdown.style.display === 'none') return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.autocompleteResults.length - 1);
                this.updateSelection();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.autocompleteResults[this.selectedIndex]) {
                    this.autocompleteResults[this.selectedIndex].action();
                    this.hideAutocomplete();
                }
                break;
                
            case 'Escape':
                this.hideAutocomplete();
                break;
        }
    }
    
    updateSelection() {
        const items = document.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.style.backgroundColor = '#f3f4f6';
            } else {
                item.style.backgroundColor = '';
            }
        });
    }
    
    hideAutocomplete() {
        const dropdown = document.getElementById('autocompleteDropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
        this.selectedIndex = -1;
    }
    
    selectEntity(entity) {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = entity.name;
        }
        this.app.performSearch();
    }
    
    selectCategory(category) {
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.value = category;
            this.app.updateFilter('category', category);
        }
        
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        
        this.app.performSearch();
    }
    
    selectLocation(location) {
        const locationFilter = document.getElementById('locationFilter');
        if (locationFilter) {
            locationFilter.value = location;
            this.app.updateFilter('location', location);
        }
        
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        
        this.app.performSearch();
    }
    
    setupAdvancedSearch() {
        // Add advanced search toggle
        this.createAdvancedSearchToggle();
        
        // Add saved searches functionality
        this.setupSavedSearches();
    }
    
    createAdvancedSearchToggle() {
        const searchContainer = document.querySelector('.search-container');
        if (!searchContainer) return;
        
        const toggleButton = document.createElement('button');
        toggleButton.textContent = 'Advanced Search';
        toggleButton.className = 'btn btn-outline';
        toggleButton.style.cssText = `
            margin-top: 20px;
            font-size: 0.9em;
        `;
        
        toggleButton.addEventListener('click', () => {
            this.toggleAdvancedSearch();
        });
        
        searchContainer.appendChild(toggleButton);
    }
    
    toggleAdvancedSearch() {
        const filtersContainer = document.querySelector('.search-filters');
        if (!filtersContainer) return;
        
        const isVisible = filtersContainer.style.display !== 'none';
        filtersContainer.style.display = isVisible ? 'none' : 'grid';
        
        const toggleButton = document.querySelector('.search-container .btn-outline');
        if (toggleButton) {
            toggleButton.textContent = isVisible ? 'Show Advanced Search' : 'Hide Advanced Search';
        }
    }
    
    setupSavedSearches() {
        // This would integrate with localStorage or a backend service
        // to save and restore user searches
        
        const savedSearches = this.getSavedSearches();
        if (savedSearches.length > 0) {
            this.displaySavedSearches(savedSearches);
        }
    }
    
    getSavedSearches() {
        try {
            return JSON.parse(localStorage.getItem('directorySearches') || '[]');
        } catch {
            return [];
        }
    }
    
    saveCurrentSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput ? searchInput.value : '';
        
        if (!query.trim()) return;
        
        const searchParams = {
            query,
            filters: { ...this.app.filters },
            timestamp: Date.now()
        };
        
        const savedSearches = this.getSavedSearches();
        savedSearches.unshift(searchParams);
        
        // Keep only the last 10 searches
        const trimmedSearches = savedSearches.slice(0, 10);
        
        try {
            localStorage.setItem('directorySearches', JSON.stringify(trimmedSearches));
        } catch (error) {
            console.warn('Could not save search to localStorage:', error);
        }
    }
    
    displaySavedSearches(searches) {
        // This would create a UI for displaying and selecting saved searches
        console.log('Saved searches:', searches);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize enhanced search when the directory app is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for the main directory app to initialize
    setTimeout(() => {
        if (window.directoryApp) {
            window.directorySearch = new DirectorySearch(window.directoryApp);
        }
    }, 500);
});