<?php
/**
 * Plugin Name: Antigravity Tracker
 * Description: Injects the conversion tracking script into the frontend.
 * Version: 1.0.0
 * Author: Antigravity AI
 * Must-Use: Yes
 */

if (!defined('ABSPATH')) {
    exit;
}

function antigravity_enqueue_tracking_script() {
    // URL to the static JS file - adjust based on your deployment
    // Assuming backend is running on localhost:8000 for development
    $script_url = 'http://localhost:8000/static/js/tracking.js';
    
    // In production, this might be a local file path or CDN URL
    
    wp_enqueue_script(
        'antigravity-tracking', 
        $script_url, 
        array(), 
        '1.0.0', 
        true // Load in footer
    );
    
    // Inject configuration variables
    $config_data = array(
        'apiUrl' => 'http://localhost:8000', // Backend API URL
        'siteId' => get_bloginfo('url')
    );
    
    wp_localize_script(
        'antigravity-tracking',
        'AntigravityConfig',
        $config_data
    );
}

add_action('wp_enqueue_scripts', 'antigravity_enqueue_tracking_script');
