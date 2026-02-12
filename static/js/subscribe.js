/**
 * SEO Autopilot Subscribe Form
 * Vanilla JS - No dependencies
 * 
 * Usage:
 * <div id="seo-subscribe-form" data-api-url="https://your-api.com"></div>
 * <script src="/static/js/subscribe.js"></script>
 */

(function() {
    'use strict';

    // Configuration
    const DEFAULT_API_URL = '';
    const CONTAINER_ID = 'seo-subscribe-form';

    /**
     * Initialize subscribe form
     */
    function initSubscribeForm() {
        const container = document.getElementById(CONTAINER_ID);
        
        if (!container) {
            console.warn('SEO Subscribe: Container #' + CONTAINER_ID + ' not found');
            return;
        }

        // Get API URL from data attribute or use default
        const apiUrl = container.dataset.apiUrl || DEFAULT_API_URL;
        
        if (!apiUrl) {
            console.error('SEO Subscribe: API URL not configured. Add data-api-url attribute.');
            container.innerHTML = '<p style="color: red;">Error: API URL not configured</p>';
            return;
        }

        // Create form HTML
        container.innerHTML = `
            <div class="seo-subscribe-wrapper" style="max-width: 400px; font-family: system-ui, -apple-system, sans-serif;">
                <form class="seo-subscribe-form" style="display: flex; flex-direction: column; gap: 10px;">
                    <div class="seo-subscribe-field">
                        <input 
                            type="email" 
                            name="email" 
                            placeholder="Enter your email" 
                            required
                            style="padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box;"
                        >
                    </div>
                    <div class="seo-subscribe-field">
                        <input 
                            type="text" 
                            name="first_name" 
                            placeholder="Your name (optional)"
                            style="padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 100%; box-sizing: border-box;"
                        >
                    </div>
                    <button 
                        type="submit" 
                        class="seo-subscribe-submit"
                        style="padding: 10px 20px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;"
                    >
                        Subscribe
                    </button>
                </form>
                <div class="seo-subscribe-message" style="margin-top: 10px; font-size: 14px; display: none;"></div>
            </div>
        `;

        // Bind form submit
        const form = container.querySelector('.seo-subscribe-form');
        const messageDiv = container.querySelector('.seo-subscribe-message');

        form.addEventListener('submit', function(e) {
            e.preventDefault();
            handleSubmit(form, messageDiv, apiUrl);
        });
    }

    /**
     * Handle form submission
     */
    function handleSubmit(form, messageDiv, apiUrl) {
        const submitBtn = form.querySelector('.seo-subscribe-submit');
        const email = form.querySelector('input[name="email"]').value.trim();
        const firstName = form.querySelector('input[name="first_name"]').value.trim();

        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Subscribing...';
        submitBtn.style.opacity = '0.7';

        // Hide previous messages
        messageDiv.style.display = 'none';
        messageDiv.className = 'seo-subscribe-message';

        // Build request
        const data = {
            email: email,
            first_name: firstName || null,
            source: 'website_subscribe_form'
        };

        // Send request
        fetch(apiUrl + '/api/v1/email/subscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(function(response) {
            return response.json().then(function(data) {
                return { ok: response.ok, status: response.status, data: data };
            });
        })
        .then(function(result) {
            if (result.ok) {
                // Success
                showMessage(messageDiv, 'Thank you for subscribing!', 'success');
                form.reset();
            } else {
                // Error
                const errorMsg = result.data.detail || result.data.message || 'Subscription failed. Please try again.';
                showMessage(messageDiv, errorMsg, 'error');
            }
        })
        .catch(function(error) {
            console.error('SEO Subscribe Error:', error);
            showMessage(messageDiv, 'Network error. Please try again later.', 'error');
        })
        .finally(function() {
            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Subscribe';
            submitBtn.style.opacity = '1';
        });
    }

    /**
     * Show message
     */
    function showMessage(element, message, type) {
        element.textContent = message;
        element.style.display = 'block';
        
        if (type === 'success') {
            element.style.color = '#28a745';
            element.style.background = '#d4edda';
            element.style.padding = '10px';
            element.style.borderRadius = '4px';
        } else {
            element.style.color = '#dc3545';
            element.style.background = '#f8d7da';
            element.style.padding = '10px';
            element.style.borderRadius = '4px';
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSubscribeForm);
    } else {
        initSubscribeForm();
    }

})();
