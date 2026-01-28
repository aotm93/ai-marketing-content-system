<?php
/**
 * Plugin Name: SEO Autopilot - Rank Math REST API Extension
 * Description: Enables Rank Math SEO meta fields in WordPress REST API for external automation
 * Version: 1.0.0
 * Author: AI Marketing Content System
 * 
 * Installation:
 * 1. Copy this file to wp-content/mu-plugins/
 * 2. MU (Must-Use) plugins are automatically activated
 * 
 * This plugin implements P0-6: MU-plugin for register_meta(..., show_in_rest=True)
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Register Rank Math meta fields for REST API access
 */
function seo_autopilot_register_rank_math_meta() {
    // List of Rank Math meta keys that should be accessible via REST API
    $rank_math_meta_keys = array(
        // Core SEO meta
        'rank_math_title' => array(
            'type' => 'string',
            'description' => 'SEO Title override',
            'single' => true,
        ),
        'rank_math_description' => array(
            'type' => 'string',
            'description' => 'Meta description',
            'single' => true,
        ),
        'rank_math_focus_keyword' => array(
            'type' => 'string',
            'description' => 'Primary focus keyword (comma-separated for multiple)',
            'single' => true,
        ),
        
        // Robots meta
        'rank_math_robots' => array(
            'type' => 'array',
            'description' => 'Robots meta directives (noindex, nofollow, etc.)',
            'single' => true,
            'items' => array('type' => 'string'),
        ),
        
        // Canonical URL
        'rank_math_canonical_url' => array(
            'type' => 'string',
            'description' => 'Canonical URL override',
            'single' => true,
        ),
        
        // Primary category
        'rank_math_primary_category' => array(
            'type' => 'integer',
            'description' => 'Primary category ID',
            'single' => true,
        ),
        
        // Social meta - Facebook/Open Graph
        'rank_math_facebook_title' => array(
            'type' => 'string',
            'description' => 'Facebook/OG title',
            'single' => true,
        ),
        'rank_math_facebook_description' => array(
            'type' => 'string',
            'description' => 'Facebook/OG description',
            'single' => true,
        ),
        'rank_math_facebook_image' => array(
            'type' => 'string',
            'description' => 'Facebook/OG image URL',
            'single' => true,
        ),
        'rank_math_facebook_image_id' => array(
            'type' => 'integer',
            'description' => 'Facebook/OG image attachment ID',
            'single' => true,
        ),
        
        // Social meta - Twitter
        'rank_math_twitter_title' => array(
            'type' => 'string',
            'description' => 'Twitter card title',
            'single' => true,
        ),
        'rank_math_twitter_description' => array(
            'type' => 'string',
            'description' => 'Twitter card description',
            'single' => true,
        ),
        'rank_math_twitter_card_type' => array(
            'type' => 'string',
            'description' => 'Twitter card type (summary, summary_large_image)',
            'single' => true,
        ),
        
        // Schema/Structured Data
        'rank_math_schema_type' => array(
            'type' => 'string',
            'description' => 'Schema.org type (Article, Product, etc.)',
            'single' => true,
        ),
        'rank_math_schema_json_ld' => array(
            'type' => 'string',
            'description' => 'Custom JSON-LD schema',
            'single' => true,
        ),
        
        // Advanced
        'rank_math_breadcrumb_title' => array(
            'type' => 'string',
            'description' => 'Custom breadcrumb title',
            'single' => true,
        ),
        'rank_math_pillar_content' => array(
            'type' => 'boolean',
            'description' => 'Is pillar/cornerstone content',
            'single' => true,
        ),
    );
    
    // Post types to register meta for
    $post_types = array('post', 'page', 'product');
    
    // Allow filtering post types
    $post_types = apply_filters('seo_autopilot_meta_post_types', $post_types);
    
    foreach ($rank_math_meta_keys as $meta_key => $config) {
        $args = array(
            'object_subtype' => '', // Will be set per post type
            'type' => $config['type'],
            'description' => $config['description'],
            'single' => $config['single'],
            'show_in_rest' => true,
            'auth_callback' => function() {
                return current_user_can('edit_posts');
            },
        );
        
        // Handle array types
        if ($config['type'] === 'array' && isset($config['items'])) {
            $args['show_in_rest'] = array(
                'schema' => array(
                    'type' => 'array',
                    'items' => $config['items'],
                ),
            );
        }
        
        // Register for each post type
        foreach ($post_types as $post_type) {
            $args['object_subtype'] = $post_type;
            register_post_meta($post_type, $meta_key, $args);
        }
    }
}
add_action('init', 'seo_autopilot_register_rank_math_meta', 99);


/**
 * Add custom REST API endpoint for SEO diagnostics
 */
function seo_autopilot_register_rest_routes() {
    register_rest_route('seo-autopilot/v1', '/check', array(
        'methods' => 'GET',
        'callback' => 'seo_autopilot_check_callback',
        'permission_callback' => function() {
            return current_user_can('edit_posts');
        },
    ));
    
    register_rest_route('seo-autopilot/v1', '/test-meta/(?P<post_id>\d+)', array(
        'methods' => 'POST',
        'callback' => 'seo_autopilot_test_meta_callback',
        'permission_callback' => function() {
            return current_user_can('edit_posts');
        },
        'args' => array(
            'post_id' => array(
                'required' => true,
                'type' => 'integer',
            ),
        ),
    ));
}
add_action('rest_api_init', 'seo_autopilot_register_rest_routes');


/**
 * SEO integration check endpoint
 */
function seo_autopilot_check_callback($request) {
    $checks = array();
    
    // Check 1: Rank Math installed
    $rank_math_active = class_exists('RankMath');
    $checks['rank_math_installed'] = array(
        'status' => $rank_math_active ? 'pass' : 'fail',
        'message' => $rank_math_active ? 'Rank Math is active' : 'Rank Math not found',
    );
    
    // Check 2: REST API enabled
    $checks['rest_api'] = array(
        'status' => 'pass',
        'message' => 'REST API is accessible',
    );
    
    // Check 3: Current user capabilities
    $can_edit = current_user_can('edit_posts');
    $can_publish = current_user_can('publish_posts');
    $checks['permissions'] = array(
        'status' => ($can_edit && $can_publish) ? 'pass' : 'warning',
        'message' => sprintf('edit_posts: %s, publish_posts: %s', 
            $can_edit ? 'yes' : 'no',
            $can_publish ? 'yes' : 'no'
        ),
    );
    
    // Check 4: Test meta registration
    $test_key = 'rank_math_title';
    $registered = registered_meta_key_exists('post', $test_key);
    $checks['meta_registration'] = array(
        'status' => $registered ? 'pass' : 'warning',
        'message' => $registered 
            ? "Meta key '$test_key' is registered for REST API" 
            : "Meta key '$test_key' may not be fully accessible",
    );
    
    // Overall status
    $has_failures = false;
    foreach ($checks as $check) {
        if ($check['status'] === 'fail') {
            $has_failures = true;
            break;
        }
    }
    
    return array(
        'status' => $has_failures ? 'error' : 'success',
        'checks' => $checks,
        'plugin_version' => '1.0.0',
        'wordpress_version' => get_bloginfo('version'),
        'rank_math_version' => $rank_math_active && defined('RANK_MATH_VERSION') ? RANK_MATH_VERSION : null,
    );
}


/**
 * Test meta writing/reading on a specific post
 */
function seo_autopilot_test_meta_callback($request) {
    $post_id = $request['post_id'];
    
    // Verify post exists
    $post = get_post($post_id);
    if (!$post) {
        return new WP_Error('not_found', 'Post not found', array('status' => 404));
    }
    
    // Test values
    $test_title = '[SEO Autopilot Test] - ' . time();
    $test_description = 'Test meta description from SEO Autopilot at ' . date('Y-m-d H:i:s');
    $test_keyword = 'test-keyword-' . time();
    
    $results = array(
        'post_id' => $post_id,
        'tests' => array(),
    );
    
    // Test 1: Write title
    $write_result = update_post_meta($post_id, 'rank_math_title', $test_title);
    $results['tests']['write_title'] = array(
        'status' => $write_result !== false ? 'pass' : 'fail',
        'value' => $test_title,
    );
    
    // Test 2: Read title back
    $read_title = get_post_meta($post_id, 'rank_math_title', true);
    $results['tests']['read_title'] = array(
        'status' => $read_title === $test_title ? 'pass' : 'fail',
        'value' => $read_title,
        'expected' => $test_title,
    );
    
    // Test 3: Write description
    update_post_meta($post_id, 'rank_math_description', $test_description);
    $read_desc = get_post_meta($post_id, 'rank_math_description', true);
    $results['tests']['description'] = array(
        'status' => $read_desc === $test_description ? 'pass' : 'fail',
        'value' => $read_desc,
    );
    
    // Test 4: Write focus keyword
    update_post_meta($post_id, 'rank_math_focus_keyword', $test_keyword);
    $read_keyword = get_post_meta($post_id, 'rank_math_focus_keyword', true);
    $results['tests']['focus_keyword'] = array(
        'status' => $read_keyword === $test_keyword ? 'pass' : 'fail',
        'value' => $read_keyword,
    );
    
    // Cleanup - restore original values or delete test values
    delete_post_meta($post_id, 'rank_math_title');
    delete_post_meta($post_id, 'rank_math_description');
    delete_post_meta($post_id, 'rank_math_focus_keyword');
    
    // Overall status
    $all_passed = true;
    foreach ($results['tests'] as $test) {
        if ($test['status'] !== 'pass') {
            $all_passed = false;
            break;
        }
    }
    
    $results['status'] = $all_passed ? 'success' : 'partial';
    $results['message'] = $all_passed 
        ? 'All SEO meta tests passed' 
        : 'Some tests failed - check individual results';
    
    return $results;
}


/**
 * Log actions for debugging (optional)
 */
function seo_autopilot_log($message) {
    if (defined('WP_DEBUG') && WP_DEBUG && defined('WP_DEBUG_LOG') && WP_DEBUG_LOG) {
        error_log('[SEO Autopilot] ' . $message);
    }
}

// Log plugin load
seo_autopilot_log('MU-Plugin loaded');
