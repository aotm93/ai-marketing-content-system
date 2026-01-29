const API_BASE_URL = '/api/v1';

export async function fetchStats(): Promise<import('../types').DashboardStats> {
    try {
        const response = await fetch(`${API_BASE_URL}/autopilot/status`);
        if (!response.ok) {
            console.error('Failed to fetch stats:', response.statusText);
            throw new Error('Failed to fetch stats');
        }

        const result = await response.json();
        const data = result.data || {};

        // Map backend data to frontend stats
        // Note: Backend might not return all these specific metrics yet, using placeholders/derived values
        return {
            total_opportunities: 0, // Need aggregation endpoint
            potential_clicks_gain: 0,
            active_alerts: 0,
            pending_publications: 0 // Could map to queue size if available
        };
    } catch (error) {
        console.error('Error fetching stats:', error);
        return {
            total_opportunities: 0,
            potential_clicks_gain: 0,
            active_alerts: 0,
            pending_publications: 0
        };
    }
}

export async function fetchOpportunities(): Promise<import('../types').GSCOpportunity[]> {
    try {
        const response = await fetch(`${API_BASE_URL}/gsc/opportunities?limit=10`);
        if (!response.ok) {
            // Handle 503 (GSC disabled) gracefully
            if (response.status === 503) return [];
            throw new Error('Failed to fetch opportunities');
        }

        const data = await response.json();

        // Map backend response to frontend GSCOpportunity type
        return data.map((item: any, index: number) => ({
            id: String(index + 1),
            opportunity_id: `gsc-${index}`,
            type: "low_hanging_fruit", // Default type
            target_query: item.query,
            target_page: item.page,
            score: item.potential_score || 0,
            potential_clicks: Math.round((item.impressions || 0) * 0.1), // Estimated
            current_position: item.position,
            current_impressions: item.impressions,
            status: "pending",
            priority: item.potential_score > 1000 ? "high" : "medium"
        }));
    } catch (error) {
        console.error('Error fetching opportunities:', error);
        return [];
    }
}
