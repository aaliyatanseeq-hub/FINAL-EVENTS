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
    setupCustomCursor();
    setupParallaxBackground();
});

// Page Navigation Functions
function goToPlatform() {
    document.getElementById('landingPage').classList.remove('active');
    document.getElementById('platformPage').classList.add('active');
    window.scrollTo(0, 0);
    switchPhase('phase1');
    // Ensure cursor is visible on platform page
    const cursor = document.getElementById('customCursor');
    if (cursor) {
        cursor.classList.add('active');
    }
}

function goToLanding() {
    document.getElementById('platformPage').classList.remove('active');
    document.getElementById('landingPage').classList.add('active');
    window.scrollTo(0, 0);
    // Hide cursor on landing page
    const cursor = document.getElementById('customCursor');
    if (cursor) {
        cursor.classList.remove('active');
    }
}

// Landing Page Initialization
const eventCategories = [
    { id: 1, title: 'Sports Events', description: '1,200+ Events', image: 'https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800&q=80', gradient: 'from-green-500/90 to-emerald-600/90' },
    { id: 2, title: 'Music Concerts', description: '3,500+ Events', image: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&q=80', gradient: 'from-purple-500/90 to-pink-600/90' },
    { id: 3, title: 'Conferences', description: '850+ Events', image: 'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=800&q=80', gradient: 'from-blue-500/90 to-indigo-600/90' },
    { id: 4, title: 'Tech Talks', description: '2,100+ Events', image: 'https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=800&q=80', gradient: 'from-cyan-500/90 to-blue-600/90' },
    { id: 5, title: 'Art & Exhibitions', description: '680+ Events', image: 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&q=80', gradient: 'from-orange-500/90 to-red-600/90' },
    { id: 6, title: 'Food Festivals', description: '920+ Events', image: 'https://images.unsplash.com/photo-1504674900247-0877df9c8360?w=800&q=80', gradient: 'from-yellow-500/90 to-orange-600/90' },
    { id: 7, title: 'Theater & Shows', description: '1,450+ Events', image: 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=800&q=80', gradient: 'from-red-500/90 to-rose-600/90' },
    { id: 8, title: 'Networking', description: '780+ Events', image: 'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=800&q=80', gradient: 'from-teal-500/90 to-cyan-600/90' },
    { id: 9, title: 'Comedy Shows', description: '560+ Events', image: 'https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=800&q=80', gradient: 'from-pink-500/90 to-fuchsia-600/90' },
    { id: 10, title: 'Workshops', description: '1,340+ Events', image: 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800&q=80', gradient: 'from-indigo-500/90 to-purple-600/90' },
    { id: 11, title: 'Festivals', description: '2,200+ Events', image: 'https://images.unsplash.com/photo-1478147427282-58a87a120781?w=800&q=80', gradient: 'from-violet-500/90 to-purple-600/90' },
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
    
    eventCategories.slice(0, 4).forEach((category, idx) => {
        const card = document.createElement('div');
        card.className = 'trending-card';
        card.style.animationDelay = `${idx * 0.15}s`;
        card.innerHTML = `
            <img src="${category.image}" alt="${category.title}" class="category-card-image">
            <div class="category-card-overlay"></div>
            <div class="category-card-content">
                <div class="trending-badge">
                    <i class="fas fa-chart-line"></i>
                    <span>Trending</span>
                </div>
                <h3 class="category-card-title">${category.title}</h3>
            </div>
        `;
        grid.appendChild(card);
    });
}

function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
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
    
    // Update cursor color based on active phase
    document.body.classList.remove('phase-1-active', 'phase-2-active', 'phase-3-active');
    if (phase === 'phase1') {
        document.body.classList.add('phase-1-active');
    } else if (phase === 'phase2') {
        document.body.classList.add('phase-2-active');
    } else if (phase === 'phase3') {
        document.body.classList.add('phase-3-active');
    }
    
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
    
    const categories = Array.from(document.querySelectorAll('.category-checkbox input:checked'))
        .map(checkbox => checkbox.value);
        
    if (categories.length === 0) {
        alert('Please select at least one category');
        return;
    }
    
    showLoading(`Discovering ${maxResults} events in ${location}...`);
    
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
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
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
    const subtitleElement = document.getElementById('eventsSubtitle');
    const location = document.getElementById('location').value || 'New York';
    const maxEvents = document.getElementById('maxEvents').value || 10;
    
    // Update subtitle
    if (subtitleElement) {
        subtitleElement.textContent = `Showing ${events.length} of ${events.length} events in ${location}`;
    }
    
    // Update status pills
    if (statsElement) {
        statsElement.innerHTML = `
            <span class="status-pill status-pill-blue">Found: ${events.length}</span>
            <span class="status-pill status-pill-purple">Limit: ${maxEvents}</span>
        `;
    }
    
    // Stats are already updated above
    
    tableBody.innerHTML = '';
    
    if (events.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">No events found</td></tr>';
    } else {
        events.forEach((event, index) => {
            const confidencePercent = Math.round((event.confidence_score || 0.5) * 100);
            const confidenceClass = getConfidenceClass(confidencePercent);
            const source = event.source || 'unknown';
            const sourceClass = getSourceClass(source);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${event.event_name || 'Unknown'}</strong></td>
                <td>${event.exact_date || 'Date not specified'}</td>
                <td>${event.exact_venue || event.location || 'Venue not specified'}</td>
                <td><span class="engagement-badge">${event.category || 'other'}</span></td>
                <td><span class="source-badge ${sourceClass}">${source}</span></td>
                <td><span class="${confidenceClass}">${confidencePercent}%</span></td>
                <td>
                    <button class="btn-analyze" onclick="analyzeAttendees('${(event.event_name || '').replace(/'/g, "\\'")}')">
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
    
    showLoading(`Finding ${maxResults} attendees for "${eventName}"...`);
    
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
                <td>${attendee.post_date || 'Unknown date'}</td>
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
    
    showLoading(`Performing ${action} on ${notificationUsers.length} ${action === 'message' ? 'users' : 'posts'}...`);
    
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

function showLoading(text) {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingModal').classList.remove('hidden');
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

// Custom Cursor - Follows Mouse Movement
function setupCustomCursor() {
    const cursor = document.getElementById('customCursor');
    if (!cursor) return;
    
    let mouseX = 0;
    let mouseY = 0;
    let cursorX = 0;
    let cursorY = 0;
    
    // Track mouse position
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        cursor.classList.add('active');
    });
    
    // Hide cursor when mouse leaves window
    document.addEventListener('mouseleave', () => {
        cursor.classList.remove('active');
    });
    
    // Animate cursor to follow mouse smoothly
    function animateCursor() {
        const dx = mouseX - cursorX;
        const dy = mouseY - cursorY;
        
        cursorX += dx * 0.1;
        cursorY += dy * 0.1;
        
        cursor.style.left = cursorX + 'px';
        cursor.style.top = cursorY + 'px';
        
        requestAnimationFrame(animateCursor);
    }
    
    animateCursor();
    
    // Set initial phase color (default to phase 1)
    if (!document.body.classList.contains('phase-1-active') && 
        !document.body.classList.contains('phase-2-active') && 
        !document.body.classList.contains('phase-3-active')) {
        document.body.classList.add('phase-1-active');
    }
}

// Parallax Background for Platform Page
function setupParallaxBackground() {
    const platformPage = document.getElementById('platformPage');
    if (!platformPage) return;
    
    function updateParallax() {
        const scrollY = window.scrollY || window.pageYOffset;
        
        // Layer 1 moves at 10% scroll speed
        platformPage.style.setProperty('--parallax-1', `${scrollY * 0.1}px`);
        
        // Layer 2 moves at 15% scroll speed
        platformPage.style.setProperty('--parallax-2', `${scrollY * 0.15}px`);
        
        requestAnimationFrame(updateParallax);
    }
    
    // Start parallax animation
    updateParallax();
}