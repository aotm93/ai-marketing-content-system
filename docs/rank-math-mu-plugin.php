<?php
/**
 * Plugin Name: Rank Math REST API Enabler
 * Description: Enable Rank Math meta fields in WordPress REST API for SEO Autopilot integration
 * Version: 1.0.0
 * Author: SEO Autopilot
 * License: MIT
 * 
 * Installation:
 * 1. Copy this file to wp-content/mu-plugins/ directory
 * 2. If mu-plugins directory doesn't exist, create it
 * 3. No activation needed - MU plugins auto-load
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Register Rank Math meta fields for REST API access
 * 
 * This allows external applications to read and write Rank Math SEO metadata
 * via the WordPress REST API
 */
add_action('init', function() {
    // List of Rank Math meta fields to expose
    $meta_fields = [
        // Primary SEO fields
        'rank_math_title',              // SEO Title
        'rank_math_description',        // Meta Description
        'rank_math_focus_keyword',      // Focus Keyword
        
        // Additional SEO fields (optional)
        'rank_math_robots',             // Robots meta tag
        'rank_math_canonical_url',      // Canonical URL
        'rank_math_primary_category',   // Primary Category
        
        // Advanced fields
        'rank_math_facebook_title',     // Facebook Title
        'rank_math_facebook_description', // Facebook Description
        'rank_math_facebook_image',     // Facebook Image
        'rank_math_twitter_title',      // Twitter Title
        'rank_math_twitter_description', // Twitter Description
        'rank_math_twitter_image',      // Twitter Image
        
        // Schema
        'rank_math_schema',             // Schema markup
    ];
    
    // Register each meta field for REST API
    foreach ($meta_fields as $field) {
        register_meta('post', $field, [
            'show_in_rest' => true,
            'single' => true,
            'type' => 'string',
            'auth_callback' => function() {
                // Only allow users with edit_posts capability
                return current_user_can('edit_posts');
            },
            'sanitize_callback' => function($value) {
                // Sanitize the value
                return sanitize_text_field($value);
            }
        ]);
    }
    
    // Log successful registration (for debugging)
    if (defined('WP_DEBUG') && WP_DEBUG) {
        error_log('Rank Math REST API Enabler: Registered ' . count($meta_fields) . ' meta fields');
    }
}, 10);

/**
 * Add CORS headers for REST API (optional, only if needed)
 * 
 * Uncomment this section if you need to allow cross-origin requests
 */
/*
add_action('rest_api_init', function() {
    remove_filter('rest_pre_serve_request', 'rest_send_cors_headers');
    add_filter('rest_pre_serve_request', function($value) {
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
        header('Access-Control-Allow-Credentials: true');
        header('Access-Control-Allow-Headers: Authorization, Content-Type');
        return $value;
    });
}, 15);
*/

/**
 * Verify installation endpoint
 * 
 * Access: GET /wp-json/seo-autopilot/v1/verify
 * Returns: Installation status and registered fields
 */
add_action('rest_api_init', function() {
    register_rest_route('seo-autopilot/v1', '/verify', [
        'methods' => 'GET',
        'callback' => function() {
            return [
                'success' => true,
                'message' => 'Rank Math REST API Enabler is active',
                'version' => '1.0.0',
                'registered_fields' => [
                    'rank_math_title',
                    'rank_math_description',
                    'rank_math_focus_keyword',
                    'rank_math_robots',
                    'rank_math_canonical_url'
                ],
                'timestamp' => current_time('mysql')
            ];
        },
        'permission_callback' => '__return_true'
    ]);
});
