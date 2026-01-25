// Admin Panel JavaScript
const API_BASE = '/api/v1/admin';

// State management
let isAuthenticated = false;

// DOM Elements
const loginScreen = document.getElementById('loginScreen');
const dashboardScreen = document.getElementById('dashboardScreen');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const logoutBtn = document.getElementById('logoutBtn');
const saveAllBtn = document.getElementById('saveAllBtn');
const refreshBtn = document.getElementById('refreshBtn');
const messageBox = document.getElementById('messageBox');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Check authentication status
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/verify`, {
            credentials: 'include'
        });

        if (response.ok) {
            isAuthenticated = true;
            showDashboard();
            loadConfiguration();
        } else {
            showLogin();
        }
    } catch (error) {
        showLogin();
    }
}

// Setup event listeners
function setupEventListeners() {
    loginForm.addEventListener('submit', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    saveAllBtn.addEventListener('click', handleSaveAll);
    refreshBtn.addEventListener('click', loadConfiguration);
}

// Handle login
async function handleLogin(e) {
    e.preventDefault();
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ password })
        });

        if (response.ok) {
            isAuthenticated = true;
            showDashboard();
            loadConfiguration();
        } else {
            const data = await response.json();
            showError(loginError, data.detail || 'Login failed');
        }
    } catch (error) {
        showError(loginError, 'Connection error. Please try again.');
    }
}

// Handle logout
async function handleLogout() {
    try {
        await fetch(`${API_BASE}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }

    isAuthenticated = false;
    showLogin();
}

// Load configuration
async function loadConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/config`, {
            credentials: 'include'
        });

        if (response.ok) {
            const result = await response.json();
            populateConfigFields(result.data);
            showMessage('Configuration loaded successfully', 'success');
        } else {
            showMessage('Failed to load configuration', 'error');
        }
    } catch (error) {
        showMessage('Connection error while loading configuration', 'error');
    }
}

// Populate configuration fields
function populateConfigFields(config) {
    const mapping = {
        'primary_ai_provider': 'PRIMARY_AI_PROVIDER',
        'primary_ai_base_url': 'PRIMARY_AI_BASE_URL',
        'primary_ai_text_model': 'PRIMARY_AI_TEXT_MODEL',
        'primary_ai_image_model': 'PRIMARY_AI_IMAGE_MODEL',
        'fallback_ai_provider': 'FALLBACK_AI_PROVIDER',
        'fallback_ai_base_url': 'FALLBACK_AI_BASE_URL',
        'fallback_ai_text_model': 'FALLBACK_AI_TEXT_MODEL',
        'wordpress_url': 'WORDPRESS_URL',
        'wordpress_username': 'WORDPRESS_USERNAME',
        'seo_plugin': 'SEO_PLUGIN',
        'keyword_api_provider': 'KEYWORD_API_PROVIDER',
        'log_level': 'LOG_LEVEL',
        'max_concurrent_agents': 'MAX_CONCURRENT_AGENTS',
        'content_generation_timeout': 'CONTENT_GENERATION_TIMEOUT'
    };

    for (const [key, elementId] of Object.entries(mapping)) {
        const element = document.getElementById(elementId);
        if (element && config[key] !== null && config[key] !== undefined) {
            element.value = config[key];
        }
    }
}

// Handle save all configuration
async function handleSaveAll() {
    const configKeys = [
        'PRIMARY_AI_PROVIDER', 'PRIMARY_AI_BASE_URL', 'PRIMARY_AI_API_KEY',
        'PRIMARY_AI_TEXT_MODEL', 'PRIMARY_AI_IMAGE_MODEL',
        'FALLBACK_AI_PROVIDER', 'FALLBACK_AI_BASE_URL', 'FALLBACK_AI_API_KEY',
        'FALLBACK_AI_TEXT_MODEL',
        'WORDPRESS_URL', 'WORDPRESS_USERNAME', 'WORDPRESS_PASSWORD',
        'SEO_PLUGIN', 'SEO_API_KEY',
        'KEYWORD_API_PROVIDER', 'KEYWORD_API_KEY', 'KEYWORD_API_BASE_URL',
        'LOG_LEVEL', 'MAX_CONCURRENT_AGENTS', 'CONTENT_GENERATION_TIMEOUT'
    ];

    let successCount = 0;
    let failCount = 0;

    saveAllBtn.disabled = true;
    saveAllBtn.textContent = 'Saving...';

    for (const key of configKeys) {
        const element = document.getElementById(key);
        if (element && element.value) {
            try {
                const response = await fetch(`${API_BASE}/config`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        config_key: key,
                        config_value: element.value
                    })
                });

                if (response.ok) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (error) {
                failCount++;
            }
        }
    }

    saveAllBtn.disabled = false;
    saveAllBtn.textContent = '💾 Save All Changes';

    if (failCount === 0) {
        showMessage(`Successfully saved ${successCount} configuration items`, 'success');
    } else {
        showMessage(`Saved ${successCount} items, ${failCount} failed`, 'error');
    }
}

// UI Helper Functions
function showLogin() {
    loginScreen.classList.add('active');
    dashboardScreen.classList.remove('active');
    document.getElementById('password').value = '';
    loginError.classList.remove('show');
}

function showDashboard() {
    loginScreen.classList.remove('active');
    dashboardScreen.classList.add('active');
}

function showError(element, message) {
    element.textContent = message;
    element.classList.add('show');
}

function showMessage(message, type) {
    messageBox.textContent = message;
    messageBox.className = `message-box show ${type}`;

    setTimeout(() => {
        messageBox.classList.remove('show');
    }, 5000);
}
