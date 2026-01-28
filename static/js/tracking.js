
/**
 * pSEO Conversion Tracker
 * Handles session tracking, pageviews, and CTA interactions.
 */
(function(window, document) {
    'use strict';

    const CONFIG = {
        apiEndpoint: '/api/v1/conversion',  // Adjust if API is on different domain
        sessionKey: 'pseo_session_id',
        userKey: 'pseo_user_id'
    };

    // Helper: Generate UUID
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Helper: Get or Create Session
    function getSessionId() {
        let sid = localStorage.getItem(CONFIG.sessionKey);
        if (!sid) {
            sid = generateUUID();
            localStorage.setItem(CONFIG.sessionKey, sid);
        }
        return sid;
    }

    // API Client
    const api = {
        post: async function(path, data) {
            try {
                const response = await fetch(`${CONFIG.apiEndpoint}${path}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ...data,
                        session_id: getSessionId(),
                        user_id: localStorage.getItem(CONFIG.userKey),
                        page_url: window.location.href,
                        referrer: document.referrer
                    })
                });
                return await response.json();
            } catch (err) {
                console.error('[pSEO Tracking Error]', err);
            }
        }
    };

    // 1. Track Page View
    function trackPageView() {
        api.post('/track', {
            event_type: 'pageview'
        });
    }

    // 2. Track Clicks (Delegation)
    function initClickTracking() {
        document.addEventListener('click', function(e) {
            const target = e.target.closest('[data-cta-variant]');
            if (target) {
                const variantId = target.getAttribute('data-cta-variant');
                api.post('/track', {
                    event_type: 'click',
                    variant_id: variantId
                });
            }
        });
    }

    // 3. Dynamic CTA Injection (Optional)
    async function loadDynamicCTA() {
        const containers = document.querySelectorAll('[data-pseo-cta]');
        if (containers.length === 0) return;

        // Infer intent from meta tag or default
        const intentMeta = document.querySelector('meta[name="pseo-intent"]');
        const intent = intentMeta ? intentMeta.content : 'informational';

        // Fetch recommendation
        try {
            const response = await fetch(`${CONFIG.apiEndpoint}/cta/recommend`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    page_url: window.location.href,
                    intent: intent
                })
            });
            const data = await response.json();
            
            if (data.primary) {
                // Apply to all containers
                containers.forEach(el => {
                    const btn = document.createElement('a');
                    btn.href = data.primary.button_url;
                    btn.className = `btn btn-${data.primary.button_color} pseo-cta`;
                    btn.textContent = data.primary.button_text;
                    btn.setAttribute('data-cta-variant', data.primary.variant_id);
                    el.innerHTML = '';
                    el.appendChild(btn);
                    
                    // Track Impression
                    api.post('/track', {
                        event_type: 'impression',
                        variant_id: data.primary.variant_id
                    });
                });
            }
        } catch (e) {
            console.warn('Failed to load dynamic CTA', e);
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            trackPageView();
            initClickTracking();
            loadDynamicCTA();
        });
    } else {
        trackPageView();
        initClickTracking();
        loadDynamicCTA();
    }

})(window, document);
