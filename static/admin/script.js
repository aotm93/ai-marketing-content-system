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

    // Website Analysis Cache event listeners
    const saveWebsiteAnalysisBtn = document.getElementById('saveWebsiteAnalysisBtn');
    const refreshWebsiteAnalysisBtn = document.getElementById('refreshWebsiteAnalysisBtn');

    if (saveWebsiteAnalysisBtn) {
        saveWebsiteAnalysisBtn.addEventListener('click', saveWebsiteAnalysisConfig);
    }

    if (refreshWebsiteAnalysisBtn) {
        refreshWebsiteAnalysisBtn.addEventListener('click', refreshWebsiteAnalysis);
    }
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

            // Also load website analysis config
            await loadWebsiteAnalysisConfig();
        } else {
            showMessage('Failed to load configuration', 'error');
        }
    } catch (error) {
        showMessage('Connection error while loading configuration', 'error');
    }
}

// Populate configuration fields
function populateConfigFields(config) {
    // Regular fields mapping
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
        'keyword_api_username': 'KEYWORD_API_USERNAME',
        'log_level': 'LOG_LEVEL',
        'max_concurrent_agents': 'MAX_CONCURRENT_AGENTS',
        'content_generation_timeout': 'CONTENT_GENERATION_TIMEOUT',
        // Autopilot Fields
        'autopilot_enabled': 'AUTOPILOT_ENABLED',
        'autopilot_mode': 'AUTOPILOT_MODE',
        'publish_interval_minutes': 'PUBLISH_INTERVAL_MINUTES',
        'max_posts_per_day': 'MAX_POSTS_PER_DAY',
        'max_concurrent_jobs': 'MAX_CONCURRENT_JOBS',
        'gsc_enabled': 'GSC_ENABLED',
        'gsc_site_url': 'GSC_SITE_URL',
        'gsc_auth_method': 'GSC_AUTH_METHOD',
        'gsc_credentials_path': 'GSC_CREDENTIALS_PATH',
        'gsc_opportunity_sync_enabled': 'GSC_OPPORTUNITY_SYNC_ENABLED',
        'gsc_runtime_status': 'GSC_RUNTIME_STATUS',
        'gsc_credential_source': 'GSC_CREDENTIAL_SOURCE',
        'gsc_schema_status': 'GSC_SCHEMA_STATUS',
        'gsc_last_raw_query_sync_at': 'GSC_LAST_RAW_QUERY_SYNC_AT',
        'gsc_last_opportunity_sync_at': 'GSC_LAST_OPPORTUNITY_SYNC_AT',
        'gsc_last_opportunity_sync_status': 'GSC_LAST_OPPORTUNITY_SYNC_STATUS',
        'gsc_persisted_opportunity_count': 'GSC_PERSISTED_OPPORTUNITY_COUNT',
        'cluster_engine_shadow_enabled': 'CLUSTER_ENGINE_SHADOW_ENABLED',
        'cluster_engine_authoritative_enabled': 'CLUSTER_ENGINE_AUTHORITATIVE_ENABLED',
        'cluster_engine_kill_switch_enabled': 'CLUSTER_ENGINE_KILL_SWITCH_ENABLED',
        'action_ctr_authoritative_enabled': 'ACTION_CTR_AUTHORITATIVE_ENABLED',
        'action_refresh_authoritative_enabled': 'ACTION_REFRESH_AUTHORITATIVE_ENABLED',
        'action_internal_link_authoritative_enabled': 'ACTION_INTERNAL_LINK_AUTHORITATIVE_ENABLED',
        'action_new_content_authoritative_enabled': 'ACTION_NEW_CONTENT_AUTHORITATIVE_ENABLED',
        'action_backlink_authoritative_enabled': 'ACTION_BACKLINK_AUTHORITATIVE_ENABLED',
        'reference_keywords': 'REFERENCE_KEYWORDS',
        'negative_keywords': 'NEGATIVE_KEYWORDS',
        'commercial_priority_terms': 'COMMERCIAL_PRIORITY_TERMS',
        'priority_target_pages': 'PRIORITY_TARGET_PAGES'
    };

    // Sensitive fields (API Keys, Passwords) - these return masked values from backend
    const sensitiveMapping = {
        'primary_ai_api_key': 'PRIMARY_AI_API_KEY',
        'fallback_ai_api_key': 'FALLBACK_AI_API_KEY',
        'wordpress_password': 'WORDPRESS_PASSWORD',
        'seo_api_key': 'SEO_API_KEY',
        'keyword_api_key': 'KEYWORD_API_KEY',
        'gsc_credentials_json': 'GSC_CREDENTIALS_JSON'
    };

    // Populate regular fields
    for (const [key, elementId] of Object.entries(mapping)) {
        const element = document.getElementById(elementId);
        if (element && config[key] !== null && config[key] !== undefined) {
            element.value = config[key];
        }
    }

    // Populate sensitive fields with special handling
    // If the backend returns a masked value (••••••••), we set a placeholder instead of the value
    // This tells the user the value is saved, but doesn't expose it
    for (const [key, elementId] of Object.entries(sensitiveMapping)) {
        const element = document.getElementById(elementId);
        if (element && config[key] !== null && config[key] !== undefined) {
            const value = config[key];
            if (value === '••••••••') {
                // Value is saved but masked - show placeholder
                element.value = '';
                element.placeholder = '✓ 已配置 (留空保留现有值)';
                element.dataset.hasExistingValue = 'true';
            } else if (value === '') {
                // No value set
                element.value = '';
                element.placeholder = '未配置';
                element.dataset.hasExistingValue = 'false';
            } else {
                // For textarea (GSC_CREDENTIALS_JSON), handle differently
                element.value = value;
            }
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
        'KEYWORD_API_PROVIDER', 'KEYWORD_API_KEY', 'KEYWORD_API_USERNAME', 'KEYWORD_API_BASE_URL',
        'LOG_LEVEL', 'MAX_CONCURRENT_AGENTS', 'CONTENT_GENERATION_TIMEOUT',
        // Autopilot Keys
        'AUTOPILOT_ENABLED', 'AUTOPILOT_MODE', 'PUBLISH_INTERVAL_MINUTES',
        'MAX_POSTS_PER_DAY', 'MAX_CONCURRENT_JOBS',
        'GSC_ENABLED', 'GSC_SITE_URL', 'GSC_AUTH_METHOD', 'GSC_CREDENTIALS_PATH', 'GSC_CREDENTIALS_JSON',
        'GSC_OPPORTUNITY_SYNC_ENABLED',
        'CLUSTER_ENGINE_SHADOW_ENABLED', 'CLUSTER_ENGINE_AUTHORITATIVE_ENABLED',
        'CLUSTER_ENGINE_KILL_SWITCH_ENABLED', 'ACTION_CTR_AUTHORITATIVE_ENABLED',
        'ACTION_REFRESH_AUTHORITATIVE_ENABLED', 'ACTION_INTERNAL_LINK_AUTHORITATIVE_ENABLED',
        'ACTION_NEW_CONTENT_AUTHORITATIVE_ENABLED', 'ACTION_BACKLINK_AUTHORITATIVE_ENABLED',
        'REFERENCE_KEYWORDS', 'NEGATIVE_KEYWORDS', 'COMMERCIAL_PRIORITY_TERMS', 'PRIORITY_TARGET_PAGES'
    ];

    // Sensitive fields that should not be overwritten with empty values if they already exist
    const sensitiveKeys = [
        'PRIMARY_AI_API_KEY', 'FALLBACK_AI_API_KEY',
        'WORDPRESS_PASSWORD', 'SEO_API_KEY',
        'KEYWORD_API_KEY', 'GSC_CREDENTIALS_JSON'
    ];

    let successCount = 0;
    let failCount = 0;
    let skippedCount = 0;

    saveAllBtn.disabled = true;
    saveAllBtn.textContent = '保存中...';

    for (const key of configKeys) {
        const element = document.getElementById(key);
        if (element) {
            let valueToSend = element.value;

            // Skip saving sensitive fields if:
            // 1. The field is empty AND
            // 2. There was an existing value (marked by dataset.hasExistingValue)
            if (sensitiveKeys.includes(key) && valueToSend === '' && element.dataset.hasExistingValue === 'true') {
                skippedCount++;
                console.log(`Skipped ${key} - keeping existing value`);
                continue;
            }

            // Special handling for JSON fields: Minify to single line
            if (key === 'GSC_CREDENTIALS_JSON' && valueToSend.trim().startsWith('{')) {
                try {
                    const parsed = JSON.parse(valueToSend);
                    valueToSend = JSON.stringify(parsed);
                } catch (e) {
                    console.error('Invalid JSON provided for credentials');
                    // Continue with raw value, backend/env might handle or break
                }
            }

            try {
                const response = await fetch(`${API_BASE}/config`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        config_key: key,
                        config_value: valueToSend
                    })
                });

                if (response.ok) {
                    successCount++;
                } else {
                    failCount++;
                    console.error(`Failed to save ${key}:`, await response.text());
                }
            } catch (error) {
                failCount++;
                console.error(`Error saving ${key}:`, error);
            }
        }
    }

    saveAllBtn.disabled = false;
    saveAllBtn.textContent = '💾 Save All Changes';

    if (failCount === 0) {
        let message = `✅ 成功保存 ${successCount} 项配置`;
        if (skippedCount > 0) {
            message += ` (${skippedCount} 个敏感字段保留现有值)`;
        }
        showMessage(message, 'success');
        // Reload configuration to show updated masked values
        await loadConfiguration();
    } else {
        showMessage(`保存 ${successCount} 项，${failCount} 项失败`, 'error');
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

// ========================================
// Website Analysis Cache Configuration
// ========================================

// Load website analysis cache configuration
async function loadWebsiteAnalysisConfig() {
    try {
        const response = await fetch(`${API_BASE}/website-analysis/config`, {
            credentials: 'include'
        });

        if (response.ok) {
            const result = await response.json();

            // Update cache duration input
            const cacheDaysInput = document.getElementById('WEBSITE_ANALYSIS_CACHE_DAYS');
            if (cacheDaysInput && result.cache_days) {
                cacheDaysInput.value = result.cache_days;
            }

            // Update cache status display
            updateCacheStatusDisplay(result);
        } else {
            console.error('Failed to load website analysis config');
        }
    } catch (error) {
        console.error('Error loading website analysis config:', error);
    }
}

// Update cache status display
function updateCacheStatusDisplay(result) {
    const cacheAgeEl = document.getElementById('cacheAge');
    const nextAnalysisEl = document.getElementById('nextAnalysis');

    if (cacheAgeEl && nextAnalysisEl) {
        if (result.cache_age_days !== null && result.cache_age_days !== undefined) {
            cacheAgeEl.textContent = `Cache Age: ${result.cache_age_days.toFixed(1)} days`;

            if (result.next_analysis_days !== null && result.next_analysis_days > 0) {
                nextAnalysisEl.textContent = `Next Analysis: in ${result.next_analysis_days.toFixed(1)} days`;
            } else {
                nextAnalysisEl.textContent = `Next Analysis: Will run on next job`;
            }
        } else {
            cacheAgeEl.textContent = 'Cache Age: No cache yet';
            nextAnalysisEl.textContent = 'Next Analysis: Will run on first job';
        }
    }
}

// Save website analysis cache duration
async function saveWebsiteAnalysisConfig() {
    const cacheDaysInput = document.getElementById('WEBSITE_ANALYSIS_CACHE_DAYS');
    const saveBtn = document.getElementById('saveWebsiteAnalysisBtn');

    if (!cacheDaysInput || !cacheDaysInput.value) {
        showMessage('Please enter cache duration (1-30 days)', 'error');
        return;
    }

    const cacheDays = parseInt(cacheDaysInput.value);
    if (cacheDays < 1 || cacheDays > 30) {
        showMessage('Cache duration must be between 1 and 30 days', 'error');
        return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
        const response = await fetch(`${API_BASE}/website-analysis/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ cache_days: cacheDays })
        });

        if (response.ok) {
            showMessage(`✅ Cache duration updated to ${cacheDays} days`, 'success');
            await loadWebsiteAnalysisConfig();
        } else {
            const result = await response.json();
            showMessage(`Failed to save: ${result.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showMessage('Connection error while saving configuration', 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Cache Duration';
    }
}

// Force refresh website analysis (clear cache)
async function refreshWebsiteAnalysis() {
    const refreshBtn = document.getElementById('refreshWebsiteAnalysisBtn');

    if (!confirm('This will immediately analyze your website content (may take 10-30 seconds). Continue?')) {
        return;
    }

    refreshBtn.disabled = true;
    refreshBtn.textContent = '🔄 Analyzing...';

    try {
        const response = await fetch(`${API_BASE}/website-analysis/refresh`, {
            method: 'POST',
            credentials: 'include'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showMessage(result.message || '✅ Website analysis completed successfully!', 'success');
            await loadWebsiteAnalysisConfig();
        } else {
            const errorMsg = result.message || result.detail || 'Analysis failed';
            showMessage(errorMsg, result.success === false ? 'warning' : 'error');
            await loadWebsiteAnalysisConfig();
        }
    } catch (error) {
        showMessage('Connection error while analyzing website', 'error');
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = '🔄 Force Re-Analysis Now';
    }
}
