// Auto-detect API URL - works for both localhost and production
const API_BASE_URL = 'http://localhost:8000/api';  // Explicit backend URL

let currentEvents = [];
let currentAttendees = [];
let selectedUsers = new Set();
let notificationUsers = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeDates();
    setupEventListeners();
    setupNavbarScroll();
    initializeLandingPage();
});

// Page Navigation Functions
function goToPlatform() {
    document.getElementById('landingPage').classList.remove('active');
    document.getElementById('platformPage').classList.add('active');
    window.scrollTo(0, 0);
    switchPhase('phase1');
}

function goToLanding() {
    document.getElementById('platformPage').classList.remove('active');
    document.getElementById('landingPage').classList.add('active');
    window.scrollTo(0, 0);
}

// Landing Page Initialization
const eventCategories = [
    { id: 1, title: 'Sports Events', description: '1,200+ Events', image: 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800&q=80', gradient: 'from-green-500/90 to-emerald-600/90' },
    { id: 2, title: 'Music Concerts', description: '3,500+ Events', image: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&q=80', gradient: 'from-purple-500/90 to-pink-600/90' },
    { id: 3, title: 'Conferences', description: '850+ Events', image: 'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=800&q=80', gradient: 'from-blue-500/90 to-indigo-600/90' },
    { id: 4, title: 'Tech Talks', description: '2,100+ Events', image: 'https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=800&q=80', gradient: 'from-cyan-500/90 to-blue-600/90' },
    { id: 5, title: 'Art & Exhibitions', description: '680+ Events', image: 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&q=80', gradient: 'from-orange-500/90 to-red-600/90' },
    { id: 6, title: 'Theater & Shows', description: '1,450+ Events', image: 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=800&q=80', gradient: 'from-red-500/90 to-rose-600/90' },
    { id: 7, title: 'Networking', description: '780+ Events', image: 'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=800&q=80', gradient: 'from-teal-500/90 to-cyan-600/90' },
    { id: 8, title: 'Comedy Shows', description: '560+ Events', image: 'https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=800&q=80', gradient: 'from-pink-500/90 to-fuchsia-600/90' },
    { id: 9, title: 'Workshops', description: '1,340+ Events', image: 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800&q=80', gradient: 'from-indigo-500/90 to-purple-600/90' },
    { id: 10, title: 'Festivals', description: '2,200+ Events', image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80', gradient: 'from-violet-500/90 to-purple-600/90' },
    { id: 12, title: 'Dance Performances', description: '890+ Events', image: 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=800&q=80', gradient: 'from-fuchsia-500/90 to-pink-600/90' }
];

function initializeLandingPage() {
    populateHeroGrid();
    populateCategories();
    populateTrending();
    setupSmoothScroll();
    setupLandingNavbarScroll();
}

function populateHeroGrid() {
    const heroGrid = document.getElementById('heroGrid');
    if (!heroGrid) return;
    
    heroGrid.innerHTML = '';
    const totalItems = 20;
    for (let i = 0; i < totalItems; i++) {
        const category = eventCategories[i % eventCategories.length];
        const item = document.createElement('div');
        item.className = 'hero-grid-item';
        item.style.backgroundImage = `url(${category.image})`;
        item.style.animationDelay = `${i * 0.05}s`;
        heroGrid.appendChild(item);
    }
}

function populateCategories() {
    const grid = document.getElementById('categoriesGrid');
    if (!grid) return;
    
    eventCategories.forEach((category, idx) => {
        const card = document.createElement('div');
        card.className = 'category-card-landing';
        card.style.animationDelay = `${idx * 0.1}s`;
        card.innerHTML = `
            <img src="${category.image}" alt="${category.title}" class="category-card-image">
            <div class="category-card-overlay"></div>
            <div class="category-card-content">
                <h3 class="category-card-title">${category.title}</h3>
                <p class="category-card-description">${category.description}</p>
                <div class="category-card-explore">
                    <span>Explore</span>
                    <i class="fas fa-arrow-right"></i>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function populateTrending() {
    const grid = document.getElementById('trendingGrid');
    if (!grid) return;
    
    // Create 5 custom trending cards
    for (let idx = 0; idx < 5; idx++) {
        if (idx === 0) {
            // First card: X with hype title
            const card = document.createElement('div');
            card.className = 'trending-card';
            card.style.animationDelay = `${idx * 0.15}s`;
            card.innerHTML = `
                <img src="https://admin.itsnicethat.com/images/xBxHBVODfdmcVk-SdcazyGBECiY=/243517/format-webp%7Cwidth-1440/twitter-x-logo-graphic-design-itsnicethat-02.jpeg" alt="X" class="category-card-image">
                <div class="category-card-overlay"></div>
                <div class="category-card-content">
                    <div class="trending-badge">
                        <i class="fas fa-chart-line"></i>
                        <span>Trending</span>
                    </div>
                    <h3 class="category-card-title">X<br><span style="font-size: 0.85em; font-weight: 400;">Where brands become legends</span></h3>
                </div>
            `;
            grid.appendChild(card);
        } else if (idx === 1) {
            // Second card: Facebook with hype title
            const card = document.createElement('div');
            card.className = 'trending-card';
            card.style.animationDelay = `${idx * 0.15}s`;
            card.innerHTML = `
                <img src="https://static0.makeuseofimages.com/wordpress/wp-content/uploads/2024/07/a-person-using-facebook-on-a-laptop.jpg?&fit=crop&w=1600&h=900" alt="Facebook" class="category-card-image">
                <div class="category-card-overlay"></div>
                <div class="category-card-content">
                    <div class="trending-badge">
                        <i class="fas fa-chart-line"></i>
                        <span>Trending</span>
                    </div>
                    <h3 class="category-card-title">Facebook<br><span style="font-size: 0.85em; font-weight: 400;">Privacy first, always</span></h3>
                </div>
            `;
            grid.appendChild(card);
        } else if (idx === 2) {
            // Third card: Instagram with hype title
            const card = document.createElement('div');
            card.className = 'trending-card';
            card.style.animationDelay = `${idx * 0.15}s`;
            card.innerHTML = `
                <img src="https://9to5mac.com/wp-content/uploads/sites/6/2023/01/instagram.jpg?quality=82&strip=all&w=1600" alt="Instagram" class="category-card-image">
                <div class="category-card-overlay"></div>
                <div class="category-card-content">
                    <div class="trending-badge">
                        <i class="fas fa-chart-line"></i>
                        <span>Trending</span>
                    </div>
                    <h3 class="category-card-title">Instagram<br><span style="font-size: 0.85em; font-weight: 400;">Share your story, share your world</span></h3>
                </div>
            `;
            grid.appendChild(card);
        } else if (idx === 3) {
            // Fourth card: LinkedIn with hype title
            const card = document.createElement('div');
            card.className = 'trending-card';
            card.style.animationDelay = `${idx * 0.15}s`;
            card.innerHTML = `
                <img src="https://www.quickanddirtytips.com/wp-content/uploads/2023/02/shutterstock_2039117105-scaled.jpg" alt="LinkedIn" class="category-card-image">
                <div class="category-card-overlay"></div>
                <div class="category-card-content">
                    <div class="trending-badge">
                        <i class="fas fa-chart-line"></i>
                        <span>Trending</span>
                    </div>
                    <h3 class="category-card-title">LinkedIn<br><span style="font-size: 0.85em; font-weight: 400;">Connect, grow, succeed</span></h3>
                </div>
            `;
            grid.appendChild(card);
        } else if (idx === 4) {
            // Fifth card: Reddit with hype title
            const card = document.createElement('div');
            card.className = 'trending-card';
            card.style.animationDelay = `${idx * 0.15}s`;
            card.innerHTML = `
                <img src="https://uk.themedialeader.com/wp-content/uploads/2024/06/Reddit-2.jpg" alt="Reddit" class="category-card-image">
                <div class="category-card-overlay"></div>
                <div class="category-card-content">
                    <div class="trending-badge">
                        <i class="fas fa-chart-line"></i>
                        <span>Trending</span>
                    </div>
                    <h3 class="category-card-title">Reddit<br><span style="font-size: 0.85em; font-weight: 400;">Find your people</span></h3>
                </div>
            `;
            grid.appendChild(card);
        }
    }
}

function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            
            // Fix: Skip if href is just '#' (invalid selector)
            if (href === '#' || !href || href.length <= 1) {
                return; // Do nothing for empty or invalid hrefs
            }
            
            try {
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            } catch (error) {
                // Handle invalid CSS selector gracefully
                console.warn(`Invalid selector for smooth scroll: ${href}`, error);
            }
        });
    });
}

function setupLandingNavbarScroll() {
    const navbar = document.getElementById('landingNavbar');
    if (!navbar) return;
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
}

function setupNavbarScroll() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
}

function initializeDates() {
    const today = new Date();
    const nextMonth = new Date(today);
    nextMonth.setMonth(today.getMonth() + 1);
    
    document.getElementById('startDate').value = today.toISOString().split('T')[0];
    document.getElementById('endDate').value = nextMonth.toISOString().split('T')[0];
}

function setupEventListeners() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetPhase = this.getAttribute('href').substring(1);
            switchPhase(targetPhase);
        });
    });
    
    document.getElementById('manualEvent').addEventListener('input', function() {
        if (this.value.trim()) {
            document.getElementById('eventSelect').value = '';
        }
    });
    
    document.getElementById('eventSelect').addEventListener('change', function() {
        if (this.value) {
            document.getElementById('manualEvent').value = '';
        }
    });
}

function switchPhase(phase) {
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    document.querySelector(`.nav-link[href="#${phase}"]`).classList.add('active');
    
    document.querySelectorAll('.phase-section').forEach(section => section.classList.remove('active'));
    document.getElementById(phase).classList.add('active');
    
    if (phase === 'phase3') {
        updateNotificationTable();
    }
}

async function discoverEvents() {
    const location = document.getElementById('location').value.trim();
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const maxResults = parseInt(document.getElementById('maxEvents').value);
    
    if (!location) {
        alert('Please enter a location');
        return;
    }
    
    // Get selected categories from checkboxes
    const categories = Array.from(document.querySelectorAll('.category-input:checked'))
        .map(checkbox => checkbox.value);
        
    if (categories.length === 0) {
        alert('Please select at least one category');
        return;
    }
    
    // Show progressive loading messages
    showLoading('Searching events...');
    
    // Update loading message after a delay to show progress
    setTimeout(() => {
        if (!document.getElementById('loadingModal').classList.contains('hidden')) {
            showLoading('Querying SerpAPI, PredictHQ, and Ticketmaster...');
        }
    }, 1000);
    
    setTimeout(() => {
        if (!document.getElementById('loadingModal').classList.contains('hidden')) {
            showLoading('Filtering and processing events...');
        }
    }, 3000);
    
    try {
        const response = await fetch(`${API_BASE_URL}/discover-events`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                location,
                start_date: startDate,
                end_date: endDate,
                categories,
                max_results: maxResults
            })
        });
        
        if (!response.ok) {
            // Try to parse error response
            let errorData;
            try {
                errorData = await response.json();
            } catch {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Extract error message from structured response
            let errorMessage = 'Failed to discover events';
            if (errorData.detail) {
                if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else if (errorData.detail.message) {
                    errorMessage = errorData.detail.message;
                } else if (errorData.detail.error) {
                    errorMessage = `${errorData.detail.error}: ${errorData.detail.message || ''}`;
                }
            }
            throw new Error(errorMessage);
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentEvents = result.events || [];
            displayEvents(currentEvents, result);
            updateEventDropdown(currentEvents);
        } else {
            throw new Error('Failed to discover events');
        }
        
    } catch (error) {
        alert('Error: ' + error.message);
        console.error('Event discovery error:', error);
    } finally {
        hideLoading();
    }
}

function displayEvents(events, metadata) {
    const tableBody = document.getElementById('eventsTableBody');
    const statsElement = document.getElementById('eventsStats');
    
    // Add source to stats
    const sourceCounts = {};
    events.forEach(event => {
        const source = event.source || 'unknown';
        sourceCounts[source] = (sourceCounts[source] || 0) + 1;
    });
    
    let sourceStats = '';
    for (const [source, count] of Object.entries(sourceCounts)) {
        sourceStats += `<span class="source-stat ${getSourceClass(source)}">${source}: ${count}</span>`;
    }
    
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_events || 0}</span>
        <span>Limit: ${metadata.requested_limit || 0}</span>
        ${sourceStats}
    `;
    
    tableBody.innerHTML = '';
    
    if (events.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">No events found</td></tr>';
    } else {
        events.forEach((event, index) => {
            const source = event.source || 'unknown';
            const sourceClass = getSourceClass(source);
            
            // Get source URL - check multiple possible fields
            let sourceUrl = event.source_url || 
                            (event.source_data && event.source_data.source_url) ||
                            (event.source_data && event.source_data.link) ||
                            (event.source_data && event.source_data.ticket_url) ||
                            '';
            
            // Validate and sanitize URL
            function isValidUrl(url) {
                if (!url || typeof url !== 'string') return false;
                url = url.trim();
                if (!url || url === '#' || url.length === 0) return false;
                
                // Must start with http:// or https://
                if (!url.match(/^https?:\/\//i)) {
                    // Try to add https:// if it looks like a domain
                    if (url.includes('.') && !url.includes(' ')) {
                        url = 'https://' + url;
                    } else {
                        return false;
                    }
                }
                
                // Basic URL validation
                try {
                    const urlObj = new URL(url);
                    // Must have valid domain
                    if (!urlObj.hostname || urlObj.hostname.length < 3) {
                        return false;
                    }
                    // Check for obviously invalid characters
                    if (url.includes(' ') || url.includes('\n') || url.includes('\r')) {
                        return false;
                    }
                    return true;
                } catch (e) {
                    return false;
                }
            }
            
            // Prepare link icon for event name (will be shown on hover)
            let linkIconHtml = '';
            if (sourceUrl && isValidUrl(sourceUrl)) {
                // HTML escape the URL for safety
                const escapedUrl = sourceUrl
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#x27;');
                
                // Also escape for title attribute
                const escapedTitle = escapedUrl;
                
                // Create hover icon that appears next to event name
                linkIconHtml = `<a href="${escapedUrl}" target="_blank" rel="noopener noreferrer" class="event-link-icon" title="Open event link: ${escapedTitle}" onclick="event.stopPropagation();">
                    <i class="fas fa-external-link-alt"></i>
                </a>`;
            }
            
            // Get category class for highlighting
            const categoryClass = getCategoryClass(event.category || 'other');
            
            // Format date with icons - handle "NA" and missing dates professionally
            function formatDate(dateStr) {
                if (!dateStr || dateStr === 'Date not specified' || dateStr.trim() === 'NA' || dateStr.trim() === '') {
                    return '<span style="color: #94a3b8; font-style: italic; font-size: 1rem;">NA</span>';
                }
                
                let formatted = dateStr;
                
                // Remove spaces from date format (e.g., "12 - 27 - 25" -> "12-27-25")
                formatted = formatted.replace(/(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})/, '$1-$2-$3');
                
                // Split date and time if present
                let datePart = formatted;
                let timePart = '';
                
                // Check if there's a time (format: "12-27-25 20:00:00" or "12-27-25 • 20:00:00" or "12-27-25 8 PM" or "12-27-25 8:00 PM")
                if (formatted.includes('•')) {
                    const parts = formatted.split('•');
                    datePart = parts[0].trim();
                    timePart = parts[1].trim();
                } else if (formatted.match(/\d{2}-\d{2}-\d{2}\s+.+/)) {
                    // Time format: "12-27-25 20:00:00" or "12-27-25 8:00 PM" or "12-27-25 8 PM GMT" or "12-27-25 2 PM"
                    // Match date followed by space and any time-related content (including AM/PM, GMT, timezone, etc.)
                    const match = formatted.match(/(\d{2}-\d{2}-\d{2})\s+(.+)/);
                    if (match) {
                        datePart = match[1];
                        timePart = match[2];
                    }
                }
                
                // Handle "NA" case
                if (datePart === 'NA' || datePart.trim() === '') {
                    return '<span style="color: #94a3b8; font-style: italic;">NA</span>';
                }
                
                // Build HTML with icons - vertical layout (date on top, time below)
                // Decreased font size slightly, no bold
                let html = `<div style="display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; align-items: center;">
                        <i class="fas fa-calendar-alt" style="font-size: 0.75rem; margin-right: 6px; opacity: 0.7; color: #64748b;"></i>
                        <span style="font-size: 0.875rem; font-weight: 400; color: #475569;">${datePart}</span>
                    </div>`;
                if (timePart && timePart !== 'NA' && timePart.trim() !== '') {
                    html += `<div style="display: flex; align-items: center; margin-top: 2px;">
                        <i class="fas fa-clock" style="font-size: 0.75rem; margin-right: 6px; opacity: 0.7; color: #64748b;"></i>
                        <span style="font-size: 0.875rem; font-weight: 400; color: #475569;">${timePart}</span>
                    </div>`;
                }
                html += `</div>`;
                
                return html;
            }
            
            const formattedDate = formatDate(event.exact_date);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="event-name-cell">
                    <div class="event-name-wrapper">
                        <strong class="event-name">${event.event_name || 'Unknown'}</strong>
                        ${linkIconHtml}
                    </div>
                </td>
                <td class="date-cell">${formattedDate}</td>
                <td>${event.exact_venue || event.location || 'Venue not specified'}</td>
                <td><span class="engagement-badge ${categoryClass}">${event.category || 'other'}</span></td>
                <td><span class="source-badge ${sourceClass}">${source}</span></td>
                <td>
                    <button class="btn-secondary" onclick="analyzeAttendees('${(event.event_name || '').replace(/'/g, "\\'")}')">
                        <i class="fas fa-users"></i>
                        Analyze
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
    
    document.getElementById('eventsResults').classList.remove('hidden');
}

async function exportEvents() {
    try {
        if (!currentEvents || currentEvents.length === 0) {
            alert('No events to export. Please discover events first.');
            return;
        }
        
        // Show loading indicator
        const exportBtn = document.querySelector('button[onclick="exportEvents()"]');
        if (!exportBtn) {
            alert('Export button not found');
            return;
        }
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
        exportBtn.disabled = true;
        
        // Prepare data for export
        const exportData = {
            events: currentEvents
        };
        
        // Call export endpoint
        const response = await fetch(`${API_BASE_URL}/export-events`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportData)
        });
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }
        
        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'events_export.xlsx';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Reset button
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
        
        console.log(`✅ Exported ${currentEvents.length} events to ${filename}`);
    } catch (error) {
        console.error('❌ Export error:', error);
        alert('Failed to export events. Please try again.');
        const exportBtn = document.querySelector('button[onclick="exportEvents()"]');
        if (exportBtn) {
            exportBtn.innerHTML = '<i class="fas fa-file-excel"></i> Export to Excel';
            exportBtn.disabled = false;
        }
    }
}

function getHypeClass(hypePercent) {
    if (hypePercent >= 70) return 'hype-high';
    if (hypePercent >= 40) return 'hype-medium';
    return 'hype-low';
}

function updateEventDropdown(events) {
    const eventSelect = document.getElementById('eventSelect');
    
    while (eventSelect.children.length > 1) {
        eventSelect.removeChild(eventSelect.lastChild);
    }
    
    events.forEach(event => {
        const option = document.createElement('option');
        option.value = event.event_name;
        option.textContent = event.event_name;
        eventSelect.appendChild(option);
    });
}

async function discoverAttendees() {
    const eventSelect = document.getElementById('eventSelect');
    const manualEvent = document.getElementById('manualEvent').value.trim();
    const eventDate = document.getElementById('eventDate').value.trim();
    const maxResults = parseInt(document.getElementById('maxAttendees').value);
    
    let eventName = eventSelect.value || manualEvent;
    
    if (!eventName.trim()) {
        alert('Please select or enter an event name');
        return;
    }
    
    // Show progressive loading messages
    showLoading('Searching attendees...');
    
    setTimeout(() => {
        if (!document.getElementById('loadingModal').classList.contains('hidden')) {
            showLoading('Querying Twitter and social media...');
        }
    }, 1500);
    
    setTimeout(() => {
        if (!document.getElementById('loadingModal').classList.contains('hidden')) {
            showLoading('Analyzing engagement data...');
        }
    }, 3000);
    
    try {
        const response = await fetch(`${API_BASE_URL}/discover-attendees`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                event_name: eventName,
                event_date: eventDate || null,
                max_results: maxResults
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const result = await response.json();
        
        if (result.success) {
            currentAttendees = result.attendees || [];
            displayAttendees(currentAttendees, result);
        } else {
            throw new Error('Failed to discover attendees');
        }
        
    } catch (error) {
        alert('Error: ' + error.message);
        console.error('Attendee discovery error:', error);
    } finally {
        hideLoading();
    }
}

function displayAttendees(attendees, metadata) {
    const tableBody = document.getElementById('attendeesTableBody');
    const statsElement = document.getElementById('attendeesStats');
    
    // Add source to stats
    const sourceCounts = {};
    attendees.forEach(attendee => {
        const source = attendee.source || 'unknown';
        sourceCounts[source] = (sourceCounts[source] || 0) + 1;
    });
    
    let sourceStats = '';
    for (const [source, count] of Object.entries(sourceCounts)) {
        sourceStats += `<span class="source-stat ${getSourceClass(source)}">${source}: ${count}</span>`;
    }
    
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_attendees || 0}</span>
        <span>Limit: ${metadata.requested_limit || 0}</span>
        ${sourceStats}
    `;
    
    tableBody.innerHTML = '';
    selectedUsers.clear();
    updateSelectionUI();
    
    if (attendees.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 2rem;">No attendees found</td></tr>';
    } else {
        attendees.forEach(attendee => {
            const engagementClass = getEngagementClass(attendee.engagement_type);
            const source = attendee.source || 'unknown';
            const sourceClass = getSourceClass(source);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox" class="user-checkbox" value="${attendee.username}" onchange="toggleUserSelection('${attendee.username}')">
                </td>
                <td>
                    <strong>${attendee.username || '@unknown'}</strong>
                    ${attendee.verified ? ' <i class="fas fa-badge-check" style="color: #1d9bf0;"></i>' : ''}
                </td>
                <td><span class="source-badge ${sourceClass}">${source}</span></td>
                <td><span class="engagement-badge ${engagementClass}">${attendee.engagement_type || 'mention'}</span></td>
                <td title="${attendee.post_content || 'No content'}">
                    ${(attendee.post_content || 'No content').length > 60 ? 
                      (attendee.post_content || 'No content').substring(0, 60) + '...' : 
                      (attendee.post_content || 'No content')}
                </td>
                <td class="date-cell">
                    ${attendee.post_date ? 
                        `<i class="fas fa-calendar-alt" style="font-size: 0.75rem; margin-right: 4px; opacity: 0.7;"></i>${attendee.post_date.replace(/(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})/, '$1-$2-$3')}` : 
                        '<i class="fas fa-calendar-alt" style="font-size: 0.75rem; margin-right: 4px; opacity: 0.7;"></i>Unknown date'
                    }
                </td>
                <td>${attendee.location || 'N/A'}</td>
                <td>${(attendee.followers_count || 0).toLocaleString()}</td>
                <td>
                    <a href="${attendee.post_link || '#'}" target="_blank" class="btn-secondary">
                        <i class="fas fa-external-link-alt"></i>
                        View
                    </a>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
    
    document.getElementById('attendeesResults').classList.remove('hidden');
}

async function exportAttendees() {
    try {
        if (!currentAttendees || currentAttendees.length === 0) {
            alert('No attendees to export. Please discover attendees first.');
            return;
        }
        
        // Show loading indicator
        const exportBtn = document.querySelector('button[onclick="exportAttendees()"]');
        if (!exportBtn) {
            alert('Export button not found');
            return;
        }
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
        exportBtn.disabled = true;
        
        // Prepare data for export
        const exportData = {
            attendees: currentAttendees
        };
        
        // Call export endpoint
        const response = await fetch(`${API_BASE_URL}/export-attendees`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportData)
        });
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }
        
        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'attendees_export.xlsx';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Reset button
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
        
        console.log(`✅ Exported ${currentAttendees.length} attendees to ${filename}`);
    } catch (error) {
        console.error('❌ Export error:', error);
        alert('Failed to export attendees. Please try again.');
        const exportBtn = document.querySelector('button[onclick="exportAttendees()"]');
        if (exportBtn) {
            exportBtn.innerHTML = '<i class="fas fa-file-excel"></i> Export to Excel';
            exportBtn.disabled = false;
        }
    }
}

function toggleUserSelection(username) {
    if (selectedUsers.has(username)) {
        selectedUsers.delete(username);
    } else {
        selectedUsers.add(username);
    }
    updateSelectionUI();
}

function toggleSelectAll() {
    const selectAll = document.getElementById('selectAllAttendees');
    const checkboxes = document.querySelectorAll('.user-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
        if (selectAll.checked) {
            selectedUsers.add(checkbox.value);
        } else {
            selectedUsers.delete(checkbox.value);
        }
    });
    
    updateSelectionUI();
}

function updateSelectionUI() {
    const selectedCount = selectedUsers.size;
    const selectionActions = document.getElementById('selectionActions');
    const selectedCountSpan = document.getElementById('selectedCount');
    const selectAllCheckbox = document.getElementById('selectAllAttendees');
    
    selectedCountSpan.textContent = `${selectedCount} users selected`;
    
    if (selectedCount > 0) {
        selectionActions.classList.remove('hidden');
    } else {
        selectionActions.classList.add('hidden');
    }
    
    const totalCheckboxes = document.querySelectorAll('.user-checkbox').length;
    selectAllCheckbox.checked = selectedCount > 0 && selectedCount === totalCheckboxes;
    selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < totalCheckboxes;
}

function sendToNotifications() {
    if (selectedUsers.size === 0) {
        alert('Please select at least one user');
        return;
    }
    
    const selectedAttendees = currentAttendees.filter(attendee => 
        selectedUsers.has(attendee.username)
    );
    
    notificationUsers = selectedAttendees;
    updateNotificationTable();
    switchPhase('phase3');
    
    alert(`Sent ${selectedAttendees.length} users to notifications phase`);
}

function updateNotificationTable() {
    const tableBody = document.getElementById('notificationsTableBody');
    const statsElement = document.getElementById('totalSelected');
    
    statsElement.textContent = `${notificationUsers.length} users selected`;
    
    if (notificationUsers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 2rem; color: #666;">
                    No users selected yet. Go to Attendees phase and select users to notify.
                </td>
            </tr>
        `;
    } else {
        tableBody.innerHTML = '';
        notificationUsers.forEach(user => {
            const engagementClass = getEngagementClass(user.engagement_type);
            const source = user.source || 'unknown';
            const sourceClass = getSourceClass(source);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <strong>${user.username}</strong>
                    ${user.verified ? ' <i class="fas fa-badge-check" style="color: #1d9bf0;"></i>' : ''}
                </td>
                <td><span class="source-badge ${sourceClass}">${source}</span></td>
                <td>${(user.followers_count || 0).toLocaleString()}</td>
                <td><span class="engagement-badge ${engagementClass}">${user.engagement_type || 'mention'}</span></td>
                <td><span class="status-pending">Pending</span></td>
                <td>
                    <button class="btn-secondary danger" onclick="removeFromNotifications('${user.username}')">
                        <i class="fas fa-times"></i>
                        Remove
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
}

function removeFromNotifications(username) {
    notificationUsers = notificationUsers.filter(user => user.username !== username);
    updateNotificationTable();
}

// REAL TWITTER ACTIONS
async function sendNotifications() {
    const message = document.getElementById('notificationMessage').value.trim();
    
    if (notificationUsers.length === 0) {
        alert('No users selected for actions');
        return;
    }
    
    // Show action selection
    const action = await showActionSelection();
    if (!action) return;
    
    // For message action, require message text
    if (action === 'message') {
        if (!message) {
            alert('Please enter a message to send');
            return;
        }
    }
    
    // Show progressive loading messages
    showLoading(`Sending ${action}...`);
    
    setTimeout(() => {
        if (!document.getElementById('loadingModal').classList.contains('hidden')) {
            showLoading(`Processing ${notificationUsers.length} ${action === 'message' ? 'users' : 'posts'}...`);
        }
    }, 1000);
    
    try {
        let endpoint;
        let successKey;
        
        switch(action) {
            case 'retweet':
                endpoint = '/retweet-posts';
                successKey = 'retweeted_count';
                break;
            case 'like':
                endpoint = '/like-posts';
                successKey = 'liked_count';
                break;
            case 'comment':
                endpoint = '/post-comments';
                successKey = 'commented_count';
                break;
            case 'quote':
                endpoint = '/post-quote-tweets';
                successKey = 'quoted_count';
                break;
            case 'message':
                endpoint = '/send-messages';
                successKey = 'sent_count';
                break;
            default:
                throw new Error('Invalid action');
        }
        
        const requestBody = {
            attendees: notificationUsers
        };
        
        // Add message for comment, quote, and message actions
        if ((action === 'comment' || action === 'quote' || action === 'message') && message) {
            requestBody.message = message;
        }
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const result = await response.json();
        
        if (result.success) {
            // Update UI with actual results
            updateNotificationResults(result, action);
            
            let actionVerb = action === 'message' ? 'sent' : action + 'ed';
            let successMessage = `✅ Successfully ${actionVerb} ${result[successKey]} ${action === 'message' ? 'messages' : 'posts'}!`;
            if (result.failed_count > 0) {
                successMessage += ` (${result.failed_count} failed)`;
            }
            
            alert(successMessage);
            
            // Log detailed results
            console.log(`${action} Results:`, result);
            
        } else {
            throw new Error('API request failed');
        }
        
    } catch (error) {
        alert('Error: ' + error.message);
        console.error('Twitter action error:', error);
    } finally {
        hideLoading();
    }
}

function showActionSelection() {
    return new Promise((resolve) => {
        const action = prompt(
            `Choose Twitter action for ${notificationUsers.length} ${notificationUsers.length === 1 ? 'user' : 'users'}:\n\n` +
            `• retweet - Retweet the original posts\n` +
            `• like - Like the original posts\n` +
            `• comment - Comment on the original posts\n` +
            `• quote - Create quote tweets\n` +
            `• message - Send direct message (DM)\n\n` +
            `Enter your choice:`,
            'retweet'
        );
        
        if (action && ['retweet', 'like', 'comment', 'quote', 'message'].includes(action.toLowerCase())) {
            resolve(action.toLowerCase());
        } else if (action === null) {
            resolve(null);
        } else {
            alert('Please enter: retweet, like, comment, quote, or message');
            resolve(showActionSelection());
        }
    });
}

function updateNotificationResults(result, action) {
    const tableBody = document.getElementById('notificationsTableBody');
    const rows = tableBody.querySelectorAll('tr');
    
    rows.forEach((row, index) => {
        if (index < result.results.length) {
            const resultItem = result.results[index];
            const statusCell = row.cells[4]; // Status is in the 5th column (index 4)
            
            let statusText = '';
            if (action === 'message') {
                statusText = resultItem.status === 'sent' ? 'sent' : 'failed';
            } else if (resultItem.status === 'retweeted' || resultItem.status === 'liked' || 
                resultItem.status === 'commented' || resultItem.status === 'quoted') {
                statusText = action + 'ed';
            } else {
                statusText = 'failed';
            }
            
            if (statusText === 'sent' || statusText.endsWith('ed')) {
                statusCell.innerHTML = `<span class="status-sent">${statusText}</span>`;
            } else {
                statusCell.innerHTML = `<span class="status-pending">${statusText}</span>`;
            }
        }
    });
}

function analyzeAttendees(eventName) {
    document.getElementById('eventSelect').value = eventName;
    document.getElementById('manualEvent').value = '';
    switchPhase('phase2');
}

function getConfidenceClass(confidence) {
    if (confidence >= 70) return 'confidence-high';
    if (confidence >= 40) return 'confidence-medium';
    return 'confidence-low';
}

function getEngagementClass(engagementType) {
    switch(engagementType) {
        case 'confirmed_attendance': return 'engagement-confirmed';
        case 'interested': return 'engagement-interested';
        default: return 'engagement-mention';
    }
}

function showLoading(text, subtext = 'Please wait while we process your request') {
    const loadingText = document.getElementById('loadingText');
    const loadingSubtext = document.getElementById('loadingSubtext');
    const loadingModal = document.getElementById('loadingModal');
    
    if (loadingText) loadingText.textContent = text;
    if (loadingSubtext) loadingSubtext.textContent = subtext;
    if (loadingModal) loadingModal.classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingModal').classList.add('hidden');
}

function getSourceClass(source) {
    const sourceLower = (source || '').toLowerCase();
    
    // Event sources
    if (sourceLower.includes('serp') || sourceLower === 'serpapi') return 'source-simple';
    if (sourceLower.includes('eventbrite')) return 'source-eventbrite';
    if (sourceLower.includes('predicthq') || sourceLower === 'phq') return 'source-predicthq';
    if (sourceLower.includes('ticketmaster')) return 'source-ticketmaster';
    if (sourceLower.includes('springbee') || sourceLower.includes('scraping')) return 'source-springbee';
    if (sourceLower.includes('database')) return 'source-database';
    if (sourceLower.includes('cache')) return 'source-cache';
    if (sourceLower.includes('api')) return 'source-api';
    
    // Attendee sources
    if (sourceLower.includes('twitter')) return 'source-twitter';
    if (sourceLower.includes('reddit')) return 'source-reddit';
    
    return 'source-unknown';
}

function getCategoryClass(category) {
    // Return category-specific class for highlighting
    const categoryLower = (category || '').toLowerCase();
    const categoryMap = {
        'music': 'category-music',
        'sports': 'category-sports',
        'tech': 'category-tech',
        'arts': 'category-arts',
        'theater': 'category-theater',
        'food': 'category-food',
        'comedy': 'category-comedy',
        'conference': 'category-conference',
        'family': 'category-family'
    };
    return categoryMap[categoryLower] || 'category-other';
}

function formatSourceName(source) {
    if (!source || source === 'unknown') return 'Unknown';
    // Capitalize first letter and handle common cases
    const sourceLower = source.toLowerCase();
    if (sourceLower === 'serpapi') return 'SerpAPI';
    if (sourceLower === 'predicthq' || sourceLower === 'phq') return 'PredictHQ';
    if (sourceLower.includes('eventbrite')) return 'Eventbrite';
    if (sourceLower.includes('ticketmaster')) return 'Ticketmaster';
    if (sourceLower.includes('springbee')) return 'SpringBee';
    // Capitalize first letter
    return source.charAt(0).toUpperCase() + source.slice(1).toLowerCase();
}

function getSourceIcon(source) {
    const sourceLower = (source || '').toLowerCase();
    
    // Event source icons
    if (sourceLower.includes('serp') || sourceLower === 'serpapi') return '🔍';
    if (sourceLower.includes('eventbrite')) return '🎫';
    if (sourceLower.includes('predicthq') || sourceLower === 'phq') return '📈';
    if (sourceLower.includes('ticketmaster')) return '🎟️';
    if (sourceLower.includes('springbee') || sourceLower.includes('scraping')) return '🐝';
    if (sourceLower.includes('database')) return '💾';
    if (sourceLower.includes('cache')) return '⚡';
    if (sourceLower.includes('api')) return '🌐';
    
    // Attendee source icons
    if (sourceLower.includes('twitter')) return '🐦';
    if (sourceLower.includes('reddit')) return '📱';
    
    return '❓';
}

function displaySourceBreakdown(items, type) {
    const sourceCounts = {};
    items.forEach(item => {
        const source = item.source || 'unknown';
        sourceCounts[source] = (sourceCounts[source] || 0) + 1;
    });
    
    let breakdown = '<div class="source-breakdown">';
    for (const [source, count] of Object.entries(sourceCounts)) {
        const percentage = ((count / items.length) * 100).toFixed(1);
        const icon = getSourceIcon(source);
        breakdown += `
            <div class="source-breakdown-item">
                <span class="source-breakdown-icon">${icon}</span>
                <span class="source-breakdown-name">${source}</span>
                <span class="source-breakdown-count">${count}</span>
                <span class="source-breakdown-percentage">(${percentage}%)</span>
            </div>
        `;
    }
    breakdown += '</div>';
    
    return breakdown;
}