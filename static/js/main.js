// MELTSA-TaTU Main JavaScript with Modern Features

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializePopovers();
    initializeAutoHideAlerts();
    initializeFormValidation();
    initializeSearch();
    initializeNotificationBadge();
    initializeThemeToggle();
    initializeDataTables();
});

// Tooltips initialization
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Popovers initialization
function initializePopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Auto-hide alerts after 5 seconds
function initializeAutoHideAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// Global search functionality
function initializeSearch() {
    const searchInput = document.getElementById('global-search');
    if (!searchInput) return;

    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 3) {
            document.getElementById('search-results')?.classList.add('d-none');
            return;
        }
        
        searchTimeout = setTimeout(() => performSearch(query), 300);
    });
}

async function performSearch(query) {
    const resultsDiv = document.getElementById('search-results');
    if (!resultsDiv) return;
    
    // Show loading
    resultsDiv.innerHTML = '<div class="text-center p-3"><div class="spinner"></div></div>';
    resultsDiv.classList.remove('d-none');
    
    try {
        const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        displaySearchResults(data);
    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = '<div class="alert alert-danger">Error performing search</div>';
    }
}

function displaySearchResults(data) {
    const resultsDiv = document.getElementById('search-results');
    if (!resultsDiv) return;
    
    let html = '<div class="list-group">';
    
    if (data.students?.length) {
        html += '<div class="list-group-item bg-light"><strong>Students</strong></div>';
        data.students.forEach(student => {
            html += `<a href="/directory/student/${student.id}/" class="list-group-item list-group-item-action">
                <i class="fas fa-user-graduate me-2"></i>${student.full_name} (${student.student_id})
            </a>`;
        });
    }
    
    if (data.courses?.length) {
        html += '<div class="list-group-item bg-light"><strong>Courses</strong></div>';
        data.courses.forEach(course => {
            html += `<a href="/courses/${course.id}/" class="list-group-item list-group-item-action">
                <i class="fas fa-book me-2"></i>${course.code} - ${course.title}
            </a>`;
        });
    }
    
    if (data.announcements?.length) {
        html += '<div class="list-group-item bg-light"><strong>Announcements</strong></div>';
        data.announcements.forEach(announcement => {
            html += `<a href="/announcements/${announcement.id}/" class="list-group-item list-group-item-action">
                <i class="fas fa-bullhorn me-2"></i>${announcement.title}
            </a>`;
        });
    }
    
    if (html === '<div class="list-group">') {
        html += '<div class="list-group-item text-muted">No results found</div>';
    }
    
    html += '</div>';
    resultsDiv.innerHTML = html;
}

// Notification badge update
function initializeNotificationBadge() {
    updateNotificationBadge();
    setInterval(updateNotificationBadge, 30000); // Update every 30 seconds
}

async function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (!badge) return;
    
    try {
        const response = await fetch('/api/notifications/unread-count/');
        const data = await response.json();
        
        if (data.count > 0) {
            badge.textContent = data.count;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    } catch (error) {
        console.error('Error updating notification badge:', error);
    }
}

// Theme toggle (light/dark mode)
function initializeThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    themeToggle.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Update icon
        const icon = this.querySelector('i');
        icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    });
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-bs-theme', savedTheme);
        const icon = themeToggle.querySelector('i');
        icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// DataTables initialization
function initializeDataTables() {
    if (typeof $.fn.DataTable !== 'undefined') {
        $('.datatable').DataTable({
            responsive: true,
            pageLength: 25,
            language: {
                search: "_INPUT_",
                searchPlaceholder: "Search..."
            }
        });
    }
}

// Payment processing with Paystack
function initializePayment(dueId, amount, email) {
    if (typeof PaystackPop === 'undefined') {
        console.error('Paystack library not loaded');
        return;
    }
    
    const handler = PaystackPop.setup({
        key: PAYSTACK_PUBLIC_KEY,
        email: email,
        amount: amount * 100, // Convert to pesewas
        currency: 'GHS',
        ref: 'MELTSA-' + Date.now() + '-' + Math.floor(Math.random() * 1000000),
        callback: function(response) {
            verifyPayment(response.reference, dueId);
        },
        onClose: function() {
            showToast('Payment window closed', 'warning');
        }
    });
    
    handler.openIframe();
}

async function verifyPayment(reference, dueId) {
    try {
        const response = await fetch('/api/payments/verify/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                reference: reference,
                due_id: dueId
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showToast('Payment successful!', 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast('Payment verification failed', 'danger');
        }
    } catch (error) {
        console.error('Payment verification error:', error);
        showToast('Error verifying payment', 'danger');
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Utility function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// QR Code scanner for attendance
function initializeQRScanner() {
    const video = document.getElementById('qr-video');
    if (!video) return;
    
    if (typeof QrScanner !== 'undefined') {
        const scanner = new QrScanner(video, result => {
            markAttendanceWithQR(result);
        });
        
        scanner.start();
    }
}

async function markAttendanceWithQR(qrData) {
    try {
        const response = await fetch('/api/attendance/mark-qr/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ qr_data: qrData })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Attendance marked successfully!', 'success');
        } else {
            showToast('Error: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Error marking attendance:', error);
        showToast('Error marking attendance', 'danger');
    }
}

// Export to Excel
function exportToExcel(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const wb = XLSX.utils.table_to_book(table, {sheet: "Sheet1"});
    XLSX.writeFile(wb, filename + '.xlsx');
}

// Export to CSV
function exportToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = Array.from(cols).map(col => col.innerText);
        csv.push(rowData.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename + '.csv';
    a.click();
}

// Print ID card
function printIDCard() {
    window.print();
}

// Download ID card as PDF
function downloadIDCardPDF() {
    const element = document.getElementById('student-id-card');
    if (!element) return;
    
    if (typeof html2pdf !== 'undefined') {
        html2pdf().from(element).save('student-id-card.pdf');
    }
}

// Initialize WebSocket connection for real-time notifications
let notificationSocket = null;

function connectNotificationWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
    
    notificationSocket = new WebSocket(wsUrl);
    
    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        showNotification(data.title, data.message);
        updateNotificationBadge();
    };
    
    notificationSocket.onclose = function() {
        // Reconnect after 5 seconds
        setTimeout(connectNotificationWebSocket, 5000);
    };
}

// Browser notifications
function showNotification(title, message) {
    if (Notification.permission === 'granted') {
        new Notification(title, { body: message });
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                new Notification(title, { body: message });
            }
        });
    }
}

// Request notification permission on login
if (Notification && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Connect WebSocket if user is authenticated
if (document.querySelector('.user-authenticated')) {
    connectNotificationWebSocket();
}
