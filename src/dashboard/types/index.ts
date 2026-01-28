export interface GSCOpportunity {
    id: string;
    opportunity_id: string;
    type: 'low_hanging_fruit' | 'ctr_optimization' | 'content_refresh' | 'cannibalization';
    target_query: string;
    target_page: string;
    score: number;
    potential_clicks: number;
    current_position: number;
    current_impressions: number;
    status: 'pending' | 'in_progress' | 'completed' | 'dismissed';
    priority: 'low' | 'medium' | 'high' | 'critical';
}

export interface SystemStatus {
    status: 'online' | 'offline' | 'degraded';
    active_jobs: number;
    last_sync: string | null;
    uptime_seconds: number;
}

export interface DashboardStats {
    total_opportunities: number;
    potential_clicks_gain: number;
    active_alerts: number;
    pending_publications: number;
}
