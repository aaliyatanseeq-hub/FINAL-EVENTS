// Auto-detect API URL - works for both localhost and production
const API_BASE_URL = window.location.origin + '/api';

let currentEvents = [];
let currentAttendees = [];
let selectedUsers = new Set();
let notificationUsers = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeDates();
    setupEventListeners();
});

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
    
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_events || 0}</span>
        <span>Limit: ${metadata.requested_limit || 0}</span>
    `;
    
    tableBody.innerHTML = '';
    
    if (events.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem;">No events found</td></tr>';
    } else {
        events.forEach((event, index) => {
            const confidencePercent = Math.round((event.confidence_score || 0.5) * 100);
            const confidenceClass = getConfidenceClass(confidencePercent);
            const hypePercent = Math.round((event.hype_score || 0) * 100);
            const hypeClass = getHypeClass(hypePercent);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${event.event_name || 'Unknown'}</strong></td>
                <td>${event.exact_date || 'Date not specified'}</td>
                <td>${event.exact_venue || event.location || 'Venue not specified'}</td>
                <td><span class="engagement-badge">${event.category || 'other'}</span></td>
                <td><span class="${confidenceClass}">${confidencePercent}%</span></td>
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
    
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_attendees || 0}</span>
        <span>Limit: ${metadata.requested_limit || 0}</span>
    `;
    
    tableBody.innerHTML = '';
    selectedUsers.clear();
    updateSelectionUI();
    
    if (attendees.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem;">No attendees found</td></tr>';
    } else {
        attendees.forEach(attendee => {
            const confidencePercent = Math.round((attendee.confidence_score || 0) * 100);
            const confidenceClass = getConfidenceClass(confidencePercent);
            const engagementClass = getEngagementClass(attendee.engagement_type);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox" class="user-checkbox" value="${attendee.username}" onchange="toggleUserSelection('${attendee.username}')">
                </td>
                <td>
                    <strong>${attendee.username || '@unknown'}</strong>
                    ${attendee.verified ? ' <i class="fas fa-badge-check" style="color: #1d9bf0;"></i>' : ''}
                </td>
                <td><span class="engagement-badge ${engagementClass}">${attendee.engagement_type || 'mention'}</span></td>
                <td title="${attendee.post_content || 'No content'}">
                    ${(attendee.post_content || 'No content').length > 60 ? 
                      (attendee.post_content || 'No content').substring(0, 60) + '...' : 
                      (attendee.post_content || 'No content')}
                </td>
                <td>${attendee.post_date || 'Unknown date'}</td>
                <td>${(attendee.followers_count || 0).toLocaleString()}</td>
                <td><span class="${confidenceClass}">${confidencePercent}%</span></td>
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
                <td colspan="5" style="text-align: center; padding: 2rem; color: #666;">
                    No users selected yet. Go to Attendees phase and select users to notify.
                </td>
            </tr>
        `;
    } else {
        tableBody.innerHTML = '';
        notificationUsers.forEach(user => {
            const engagementClass = getEngagementClass(user.engagement_type);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <strong>${user.username}</strong>
                    ${user.verified ? ' <i class="fas fa-badge-check" style="color: #1d9bf0;"></i>' : ''}
                </td>
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
    
    showLoading(`Performing ${action} on ${notificationUsers.length} posts...`);
    
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
            default:
                throw new Error('Invalid action');
        }
        
        const requestBody = {
            attendees: notificationUsers
        };
        
        if ((action === 'comment' || action === 'quote') && message) {
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
            
            let successMessage = `✅ Successfully ${action}ed ${result[successKey]} posts!`;
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
            `Choose Twitter action for ${notificationUsers.length} posts:\n\n` +
            `• retweet - Retweet the original posts\n` +
            `• like - Like the original posts\n` +
            `• comment - Comment on the original posts\n` +
            `• quote - Create quote tweets\n\n` +
            `Enter your choice:`,
            'retweet'
        );
        
        if (action && ['retweet', 'like', 'comment', 'quote'].includes(action.toLowerCase())) {
            resolve(action.toLowerCase());
        } else if (action === null) {
            resolve(null);
        } else {
            alert('Please enter: retweet, like, comment, or quote');
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
            const statusCell = row.cells[3];
            
            if (resultItem.status === 'retweeted' || resultItem.status === 'liked' || 
                resultItem.status === 'commented' || resultItem.status === 'quoted') {
                statusCell.innerHTML = `<span class="status-sent">${action}ed</span>`;
            } else {
                statusCell.innerHTML = `<span class="status-pending">Failed</span>`;
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