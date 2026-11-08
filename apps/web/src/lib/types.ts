export interface Property {
  id?: string;
  title?: string;
  description?: string;
  country?: string;
  region?: string;
  city: string;
  district?: string;
  neighborhood?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  property_type: 'apartment' | 'house' | 'studio' | 'loft' | 'townhouse' | 'other';
  listing_type: 'rent' | 'sale' | 'room' | 'sublease';
  rooms?: number;
  bathrooms?: number;
  area_sqm?: number;
  floor?: number;
  total_floors?: number;
  year_built?: number;
  energy_rating?: string;
  price?: number;
  currency?: string;
  price_media?: number;
  price_delta?: number;
  deposit?: number;
  negotiation_rate?: 'high' | 'middle' | 'low';
  has_parking: boolean;
  has_garden: boolean;
  has_pool: boolean;
  has_garage: boolean;
  has_bike_room: boolean;
  amenities?: string[];
  images?: string[];
}

export interface SearchResultItem {
  property: Property;
  score: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  count: number;
}

export interface SearchRequest {
  query: string;
  limit?: number;
  filters?: Record<string, unknown>;
  alpha?: number;
  lat?: number;
  lon?: number;
  radius_km?: number;
  polygon?: [number, number][];
  sort_by?: 'relevance' | 'price' | 'price_per_sqm' | 'area_sqm' | 'year_built';
  sort_order?: 'asc' | 'desc';
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  stream?: boolean;
  include_intermediate_steps?: boolean;
}

export interface ChatResponse {
  response: string;
  sources: Array<{
    content: string;
    metadata: Record<string, unknown>;
  }>;
  sources_truncated?: boolean;
  session_id?: string;
  intermediate_steps?: Array<Record<string, unknown>>;
}

export interface RagUploadResponse {
  message: string;
  chunks_indexed: number;
  errors: string[];
}

export interface RagResetResponse {
  message: string;
  documents_removed: number;
  documents_remaining: number;
}

export interface RagQaRequest {
  question: string;
  top_k?: number;
  provider?: string;
  model?: string;
}

export interface RagQaCitation {
  source: string;
  chunk_index: number;
}

// ============================================================================
// TASK-065: Enhanced Citation Types
// ============================================================================

export type SourceType = 'pdf' | 'docx' | 'web' | 'database' | 'api' | 'unknown';

export type CitationConfidence = 'high' | 'medium' | 'low';

export interface EnhancedCitation {
  source?: string | null;
  chunk_index?: number | null;
  page_number?: number | null;
  paragraph_number?: number | null;
  source_type: SourceType;
  confidence: CitationConfidence;
  confidence_score: number;
  content_snippet?: string | null;
  source_url?: string | null;
  source_title?: string | null;
  citation_hash?: string | null;
  is_duplicate: boolean;
  validated: boolean;
}

export interface CitationStats {
  total: number;
  unique: number;
  duplicates: number;
  by_type: Record<string, number>;
  avg_confidence: number;
}

export interface RagQaResponse {
  answer: string;
  citations: EnhancedCitation[];
  citation_format?: string;
  citation_stats?: CitationStats | null;
  llm_used: boolean;
  provider: string | null;
  model: string | null;
}

export interface MortgageInput {
  property_price: number;
  down_payment_percent?: number;
  interest_rate?: number;
  loan_years?: number;
}

export interface MortgageResult {
  monthly_payment: number;
  total_interest: number;
  total_cost: number;
  down_payment: number;
  loan_amount: number;
  breakdown: Record<string, number>;
}

export interface TCOInput {
  property_price: number;
  down_payment_percent?: number;
  interest_rate?: number;
  loan_years?: number;
  monthly_hoa?: number;
  annual_property_tax?: number;
  annual_insurance?: number;
  monthly_utilities?: number;
  monthly_internet?: number;
  monthly_parking?: number;
  maintenance_percent?: number;
}

export interface TCOResult {
  // Mortgage components
  monthly_payment: number;
  total_interest: number;
  down_payment: number;
  loan_amount: number;
  // TCO components (monthly)
  monthly_mortgage: number;
  monthly_property_tax: number;
  monthly_insurance: number;
  monthly_hoa: number;
  monthly_utilities: number;
  monthly_internet: number;
  monthly_parking: number;
  monthly_maintenance: number;
  monthly_tco: number;
  // TCO components (annual)
  annual_mortgage: number;
  annual_property_tax: number;
  annual_insurance: number;
  annual_hoa: number;
  annual_utilities: number;
  annual_internet: number;
  annual_parking: number;
  annual_maintenance: number;
  annual_tco: number;
  // Total over loan term
  total_ownership_cost: number;
  total_all_costs: number;
  breakdown: Record<string, number>;
}

// Task #52: Enhanced TCO types
export interface TCOProjection {
  year: number;
  cumulative_cost: number;
  cumulative_principal_paid: number;
  cumulative_interest_paid: number;
  cumulative_equity: number;
  property_value_estimate: number;
  loan_balance: number;
  annual_cost: number;
}

export interface EnhancedTCOResult extends TCOResult {
  projections: TCOProjection[];
  percentage_breakdown: Record<string, number>;
  fixed_costs_monthly: number;
  variable_costs_monthly: number;
  discretionary_costs_monthly: number;
}

export interface TCOLocationDefaults {
  country: string;
  region: string;
  property_tax_rate: number;
  avg_insurance_rate: number;
  avg_utilities_per_sqm: number;
  avg_internet: number;
  avg_parking: number;
  currency: string;
}

export interface TCOComparisonInput {
  scenario_a: TCOInput;
  scenario_b: TCOInput;
  scenario_a_name?: string;
  scenario_b_name?: string;
  comparison_years?: number;
  appreciation_rate?: number;
  priority_monthly_cashflow?: number;
  priority_long_term_equity?: number;
  priority_total_cost?: number;
}

export interface TCOComparisonResult {
  scenario_a: EnhancedTCOResult;
  scenario_b: EnhancedTCOResult;
  scenario_a_name: string;
  scenario_b_name: string;
  monthly_cost_difference: number;
  total_cost_difference: number;
  equity_difference: number;
  break_even_years: number | null;
  a_advantages: string[];
  b_advantages: string[];
  recommendation: string;
  recommendation_reason: string;
  priority_score_a: number;
  priority_score_b: number;
}

export interface AvailableLocationsResponse {
  locations: Record<string, string[]>;
}

export interface NotificationSettings {
  // Notification type toggles
  price_alerts_enabled: boolean;
  new_listings_enabled: boolean;
  saved_search_enabled: boolean;
  market_updates_enabled: boolean;

  // Frequency settings
  alert_frequency: 'instant' | 'daily' | 'weekly';

  // Channel selection
  email_enabled: boolean;
  push_enabled: boolean;
  in_app_enabled: boolean;

  // Advanced settings
  quiet_hours_start: string | null; // HH:MM format
  quiet_hours_end: string | null; // HH:MM format
  price_drop_threshold: number; // percentage

  // Digest settings
  daily_digest_time: string; // HH:MM format
  weekly_digest_day: string; // day name

  // Expert/Marketing preferences
  expert_mode: boolean;
  marketing_emails: boolean;

  // Unsubscribe info (read-only)
  unsubscribe_token: string | null;
  unsubscribed_at: string | null;
  unsubscribed_types: string[] | null;
}

export interface NotificationSettingsUpdate {
  // Notification type toggles (all optional for partial updates)
  price_alerts_enabled?: boolean;
  new_listings_enabled?: boolean;
  saved_search_enabled?: boolean;
  market_updates_enabled?: boolean;

  // Frequency settings
  alert_frequency?: 'instant' | 'daily' | 'weekly';

  // Channel selection
  email_enabled?: boolean;
  push_enabled?: boolean;
  in_app_enabled?: boolean;

  // Advanced settings
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  price_drop_threshold?: number;

  // Digest settings
  daily_digest_time?: string;
  weekly_digest_day?: string;

  // Expert/Marketing preferences
  expert_mode?: boolean;
  marketing_emails?: boolean;
}

export interface NotificationPreviewRequest {
  channel: 'email' | 'push' | 'in_app';
  notification_type: 'price_alert' | 'new_listing' | 'saved_search' | 'market_update';
}

export interface NotificationPreviewResponse {
  success: boolean;
  message: string;
  channel: string;
  notification_type: string;
}

export interface ModelPricing {
  input_price_per_1m: number;
  output_price_per_1m: number;
  currency: string;
}

export interface ModelCatalogItem {
  id: string;
  display_name: string;
  provider_name: string;
  context_window: number;
  pricing: ModelPricing | null;
  capabilities: string[];
  description: string | null;
  recommended_for: string[];
}

export interface ModelProviderCatalog {
  name: string;
  display_name: string;
  is_local: boolean;
  requires_api_key: boolean;
  models: ModelCatalogItem[];
  runtime_available?: boolean | null;
  available_models?: string[] | null;
  runtime_error?: string | null;
}

export interface ModelRuntimeTestResponse {
  provider: string;
  is_local: boolean;
  runtime_available?: boolean | null;
  available_models?: string[] | null;
  runtime_error?: string | null;
}

export interface ModelPreferences {
  preferred_provider: string | null;
  preferred_model: string | null;
}

export type ExportFormat = 'csv' | 'xlsx' | 'json' | 'md' | 'pdf';

export interface ExportPropertiesRequest {
  format: ExportFormat;
  property_ids?: string[];
  search?: SearchRequest;
  columns?: string[];
  include_header?: boolean;
  csv_delimiter?: string;
  csv_decimal?: string;
  include_summary?: boolean;
  include_statistics?: boolean;
  include_metadata?: boolean;
  pretty?: boolean;
  max_properties?: number | null;
}

export interface ExportSearchRequest {
  format: ExportFormat;
  search: SearchRequest;
}

export interface PromptTemplateVariableInfo {
  name: string;
  description: string;
  required: boolean;
  example?: string | null;
}

export interface PromptTemplateInfo {
  id: string;
  title: string;
  category: string;
  description: string;
  template_text: string;
  variables: PromptTemplateVariableInfo[];
}

export interface PromptTemplateApplyResponse {
  template_id: string;
  rendered_text: string;
}

// Admin API types for data ingestion
export interface IngestRequest {
  file_urls?: string[];
  force?: boolean;
  sheet_name?: string;
  header_row?: number;
  source_name?: string;
}

export interface IngestResponse {
  message: string;
  properties_processed: number;
  errors: string[];
  source_type?: string;
  source_name?: string;
}

export interface ExcelSheetsRequest {
  file_url: string;
}

export interface ExcelSheetsResponse {
  file_url: string;
  sheet_names: string[];
  default_sheet?: string;
  row_count: Record<string, number>;
}

// Portal/API Integration types for TASK-006
export interface PortalAdapterInfo {
  name: string;
  display_name: string;
  configured: boolean;
  has_api_key: boolean;
  rate_limit?: { requests: number; window_seconds: number } | null;
}

export interface PortalAdaptersResponse {
  adapters: PortalAdapterInfo[];
  count: number;
}

export interface PortalFiltersRequest {
  portal: string;
  city?: string;
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  property_type?: string;
  listing_type?: string;
  limit?: number;
  source_name?: string;
}

export interface PortalIngestResponse {
  success: boolean;
  message: string;
  portal: string;
  properties_processed: number;
  source_type: string;
  source_name?: string;
  errors: string[];
  filters_applied?: Record<string, unknown>;
}

// Investment Analysis types for TASK-019
export interface InvestmentAnalysisInput {
  property_price: number;
  monthly_rent: number;
  down_payment_percent?: number;
  closing_costs?: number;
  renovation_costs?: number;
  interest_rate?: number;
  loan_years?: number;
  property_tax_monthly?: number;
  insurance_monthly?: number;
  hoa_monthly?: number;
  maintenance_percent?: number;
  vacancy_rate?: number;
  management_percent?: number;
}

export interface InvestmentAnalysisResult {
  monthly_cash_flow: number;
  annual_cash_flow: number;
  cash_on_cash_roi: number;
  cap_rate: number;
  gross_yield: number;
  net_yield: number;
  total_investment: number;
  monthly_income: number;
  monthly_expenses: number;
  annual_income: number;
  annual_expenses: number;
  monthly_mortgage: number;
  investment_score: number;
  score_breakdown: Record<string, number>;
}

export interface CompareInvestmentsRequest {
  property_ids: string[];
}

export interface ComparedInvestmentProperty {
  property_id?: string;
  price?: number;
  monthly_rent?: number;
  monthly_cash_flow?: number;
  cash_on_cash_roi?: number;
  cap_rate?: number;
  investment_score?: number;
}

export interface CompareInvestmentsResponse {
  properties: ComparedInvestmentProperty[];
  summary: Record<string, unknown>;
}

// Neighborhood Quality Index types for TASK-020 and Task #40

/**
 * Detailed information about a single scoring factor
 */
export interface FactorDetail {
  raw_value: number;
  unit: string;
  confidence: number; // 0-1
  data_source: string;
}

/**
 * Comparison of neighborhood to city average
 */
export interface CityComparison {
  percentile: number; // 0-100
  city_average: number;
  better_than: string[]; // Factor names where this neighborhood is better
  worse_than: string[]; // Factor names where this neighborhood is worse
}

/**
 * A single Point of Interest near the property
 */
export interface NearbyPOI {
  name: string;
  category: string;
  distance_meters: number;
  latitude?: number;
  longitude?: number;
}

/**
 * Grouped POIs by category
 */
export interface NearbyPOIs {
  schools: NearbyPOI[];
  amenities: NearbyPOI[];
  green_spaces: NearbyPOI[];
  transport_stops: NearbyPOI[];
  police_stations: NearbyPOI[];
}

/**
 * Data freshness information for each source
 */
export interface DataFreshness {
  [key: string]: string; // ISO timestamp strings
}

export interface NeighborhoodQualityInput {
  property_id: string;
  latitude?: number;
  longitude?: number;
  city?: string;
  neighborhood?: string;
}

/**
 * Enhanced Neighborhood Quality Result with all 8 scoring factors
 * Core factors (60%): Safety, Schools, Amenities, Walkability, Green Space
 * New factors (40%): Air Quality, Noise Level, Public Transport
 */
export interface NeighborhoodQualityResult {
  property_id: string;
  overall_score: number;
  // Core scores (60% total)
  safety_score: number;
  schools_score: number;
  amenities_score: number;
  walkability_score: number;
  green_space_score: number;
  // New scores (40% total)
  air_quality_score: number;
  noise_level_score: number;
  public_transport_score: number;
  // Detailed breakdown for each factor
  factor_details?: {
    safety?: FactorDetail;
    schools?: FactorDetail;
    amenities?: FactorDetail;
    walkability?: FactorDetail;
    green_space?: FactorDetail;
    air_quality?: FactorDetail;
    noise_level?: FactorDetail;
    public_transport?: FactorDetail;
  };
  score_breakdown: Record<string, number>;
  data_sources: string[];
  // New fields for Task #40
  city_comparison?: CityComparison;
  nearby_pois?: NearbyPOIs;
  data_freshness?: DataFreshness;
  latitude?: number;
  longitude?: number;
  city?: string;
  neighborhood?: string;
}

// Saved Search types for Task #36
export type AlertFrequency = 'instant' | 'daily' | 'weekly' | 'none';

export interface SavedSearch {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  alert_frequency: AlertFrequency;
  is_active: boolean;
  notify_on_new: boolean;
  notify_on_price_drop: boolean;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  use_count: number;
}

export interface SavedSearchCreate {
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  alert_frequency?: AlertFrequency;
  notify_on_new?: boolean;
  notify_on_price_drop?: boolean;
}

export interface SavedSearchUpdate {
  name?: string;
  description?: string;
  filters?: Record<string, unknown>;
  alert_frequency?: AlertFrequency;
  is_active?: boolean;
  notify_on_new?: boolean;
  notify_on_price_drop?: boolean;
}

export interface SavedSearchListResponse {
  items: SavedSearch[];
  total: number;
}

// Filter Preset types for Task #75
export interface FilterPreset {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  is_default: boolean;
  last_used_at?: string;
  use_count: number;
  created_at: string;
  updated_at: string;
}

export interface FilterPresetCreate {
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  is_default?: boolean;
}

export interface FilterPresetUpdate {
  name?: string;
  description?: string;
  filters?: Record<string, unknown>;
  is_default?: boolean;
}

export interface FilterPresetListResponse {
  items: FilterPreset[];
  total: number;
}

// Collection types for Task #37
export interface Collection {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  favorite_count: number;
}

export interface CollectionCreate {
  name: string;
  description?: string;
}

export interface CollectionUpdate {
  name?: string;
  description?: string;
}

export interface CollectionListResponse {
  items: Collection[];
  total: number;
}

// Favorite types for Task #37
export interface Favorite {
  id: string;
  user_id: string;
  property_id: string;
  collection_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface FavoriteWithProperty extends Favorite {
  property?: Property;
  is_available: boolean;
}

export interface FavoriteCreate {
  property_id: string;
  collection_id?: string;
  notes?: string;
}

export interface FavoriteUpdate {
  collection_id?: string;
  notes?: string;
}

export interface FavoriteListResponse {
  items: FavoriteWithProperty[];
  total: number;
  unavailable_count: number;
}

export interface FavoriteCheckResponse {
  is_favorited: boolean;
  favorite_id?: string;
  collection_id?: string;
  notes?: string;
}

// Price History types for Task #38
export interface PriceSnapshot {
  id: string;
  property_id: string;
  price: number;
  price_per_sqm?: number;
  currency?: string;
  source?: string;
  recorded_at: string;
}

export interface PriceHistory {
  property_id: string;
  snapshots: PriceSnapshot[];
  total: number;
  current_price?: number;
  first_recorded?: string;
  last_recorded?: string;
  price_change_percent?: number;
  trend: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
}

export interface MarketTrendPoint {
  period: string;
  start_date: string;
  end_date: string;
  average_price: number;
  median_price: number;
  volume: number;
  avg_price_per_sqm?: number;
}

export interface MarketTrends {
  city?: string;
  district?: string;
  interval: 'month' | 'quarter' | 'year';
  data_points: MarketTrendPoint[];
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  change_percent?: number;
  confidence: 'high' | 'medium' | 'low';
}

export interface MarketIndicators {
  city?: string;
  overall_trend: 'rising' | 'falling' | 'stable';
  avg_price_change_1m?: number;
  avg_price_change_3m?: number;
  avg_price_change_6m?: number;
  avg_price_change_1y?: number;
  total_listings: number;
  new_listings_7d: number;
  price_drops_7d: number;
  hottest_districts: Array<{ name: string; avg_price: number; count: number }>;
  coldest_districts: Array<{ name: string; avg_price: number; count: number }>;
}

// Area Comparison types for Task #84
export interface AreaInsights {
  city: string;
  property_count: number;
  avg_price: number;
  median_price: number;
  avg_price_per_sqm?: number;
  most_common_room_count?: number;
  amenity_availability: Record<string, number>;
  price_comparison?: 'above_average' | 'below_average' | 'average';
}

export interface AreaComparison {
  area1: AreaInsights;
  area2: AreaInsights;
  price_difference: number;
  price_difference_percent: number;
  cheaper_area: string;
  more_properties_area: string;
  comparison_timestamp: string;
}

// Advanced Investment Analytics types for Task #39
export interface YearlyCashFlow {
  year: number;
  gross_income: number;
  operating_expenses: number;
  mortgage_payment: number;
  noi: number;
  cash_flow: number;
  cumulative_cash_flow: number;
  property_value: number;
  equity: number;
  loan_balance: number;
}

export interface AdvancedInvestmentInput extends InvestmentAnalysisInput {
  projection_years?: number;
  appreciation_rate?: number;
  rent_growth_rate?: number;
  marginal_tax_rate?: number;
  land_value_ratio?: number;
  market_volatility?: number;
}

export interface AppreciationScenario {
  name: string;
  annual_rate: number;
  projected_values: Record<number, number>;
  total_appreciation_percent: number;
  total_appreciation_amount: number;
}

export interface AdvancedInvestmentResult extends InvestmentAnalysisResult {
  cash_flow_projection: YearlyCashFlow[];
  total_projected_cash_flow: number;
  final_equity: number;
  irr: number | null;
  annual_depreciation: number;
  total_tax_deductions: number;
  tax_benefit: number;
  appreciation_scenarios: AppreciationScenario[];
  risk_score: number;
  risk_factors: string[];
  recommendations: string[];
}

// Portfolio Analytics types for Task #39
export interface PropertyHolding {
  property_id: string;
  property_price: number;
  monthly_rent: number;
  property_type: string;
  city: string;
  monthly_cash_flow: number;
  cap_rate: number;
}

export interface PortfolioMetrics {
  total_properties: number;
  total_value: number;
  total_monthly_cash_flow: number;
  total_annual_cash_flow: number;
  weighted_avg_cap_rate: number;
  weighted_avg_yield: number;
}

export interface PortfolioDiversification {
  geographic_score: number;
  property_type_score: number;
  city_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  concentration_risk: number;
  largest_holding_percent: number;
}

export interface PortfolioRiskAssessment {
  overall_risk_score: number;
  geographic_diversification: number;
  property_type_diversification: number;
  concentration_risk: number;
  cash_flow_risk: number;
  recommendations: string[];
}

export interface PortfolioPerformance {
  total_return: number;
  annualized_return: number;
  cash_on_cash_return: number;
  appreciation: number;
}

export interface PortfolioAnalysisInput {
  properties: PropertyHolding[];
  market_volatility_by_city?: Record<string, number>;
}

export interface PortfolioAnalysisResult {
  metrics: PortfolioMetrics;
  diversification: PortfolioDiversification;
  risk_assessment: PortfolioRiskAssessment;
  performance: PortfolioPerformance;
}

// Task #42: Rent vs Buy Calculator
export interface RentVsBuyInput {
  property_price: number;
  monthly_rent: number;
  down_payment_percent?: number;
  interest_rate?: number;
  loan_years?: number;
  annual_property_tax?: number;
  annual_insurance?: number;
  monthly_hoa?: number;
  maintenance_percent?: number;
  appreciation_rate?: number;
  rent_increase_rate?: number;
  investment_return_rate?: number;
  marginal_tax_rate?: number;
  projection_years?: number;
}

export interface YearlyBreakdown {
  year: number;
  annual_rent: number;
  cumulative_rent: number;
  invested_savings_value: number;
  annual_mortgage: number;
  annual_property_tax: number;
  annual_insurance: number;
  annual_maintenance: number;
  annual_hoa: number;
  annual_total_ownership_cost: number;
  cumulative_ownership_cost: number;
  property_value: number;
  loan_balance: number;
  equity: number;
  tax_savings: number;
  net_ownership_cost: number;
  net_benefit: number;
}

export interface RentVsBuyResult {
  monthly_mortgage: number;
  monthly_rent_initial: number;
  break_even_years: number | null;
  recommendation: string;
  total_rent_paid: number;
  total_ownership_cost: number;
  total_equity_built: number;
  final_property_value: number;
  opportunity_cost_of_buying: number;
  net_buying_advantage: number;
  yearly_breakdown: YearlyBreakdown[];
}

// Task #54: Listing Generation
export type ListingTone = 'professional' | 'friendly' | 'luxury' | 'engaging';
export type ListingLanguage = 'en' | 'pl' | 'es' | 'de' | 'fr' | 'it' | 'pt' | 'ru';
export type HeadlineStyle = 'catchy' | 'professional' | 'seo';
export type SocialPlatform = 'facebook' | 'instagram' | 'linkedin' | 'twitter';

export interface ListingGenerationRequest {
  property_id: string;
  tone?: ListingTone;
  language?: ListingLanguage;
  generate_description?: boolean;
  generate_headlines?: boolean;
  headline_count?: number;
  headline_style?: HeadlineStyle;
  generate_social?: boolean;
  social_platform?: SocialPlatform;
}

export interface ListingGenerationResult {
  description: string | null;
  headlines: string[] | null;
  social_content: string | null;
  char_counts: Record<string, number>;
  error?: string;
}

// Task #51: Commute Time Analysis
export type CommuteMode = 'driving' | 'walking' | 'bicycling' | 'transit';

export interface CommuteTimeRequest {
  property_id: string;
  destination_lat: number;
  destination_lon: number;
  mode?: CommuteMode;
  destination_name?: string;
  departure_time?: string; // ISO format
}

export interface CommuteTimeResult {
  property_id: string;
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  destination_name?: string;
  duration_seconds: number;
  duration_text: string; // e.g., "45m"
  distance_meters: number;
  distance_text: string; // e.g., "12.5 km"
  mode: string;
  polyline?: string; // Encoded route for map visualization
  arrival_time?: string;
  departure_time?: string;
}

export interface CommuteTimeResponse {
  result: CommuteTimeResult;
}

export interface CommuteRankingRequest {
  property_ids: string; // Comma-separated property IDs
  destination_lat: number;
  destination_lon: number;
  mode?: CommuteMode;
  destination_name?: string;
  departure_time?: string; // ISO format
}

export interface CommuteRankingResponse {
  destination_name?: string;
  destination_lat: number;
  destination_lon: number;
  mode: string;
  rankings: CommuteTimeResult[];
  count: number;
  fastest_duration_seconds?: number | null;
  slowest_duration_seconds?: number | null;
}

// Saved destination for frequent commute calculations
export interface SavedDestination {
  id: string;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  is_default?: boolean;
}

// Task #53: Market Anomaly Detection
export type AnomalyType =
  | 'price_spike'
  | 'price_drop'
  | 'volume_spike'
  | 'volume_drop'
  | 'unusual_pattern';

export type AnomalySeverity = 'low' | 'medium' | 'high' | 'critical';

export type AnomalyScope = 'property' | 'city' | 'district' | 'market' | 'region';

export interface MarketAnomaly {
  id: string;
  anomaly_type: AnomalyType;
  severity: AnomalySeverity;
  scope_type: AnomalyScope;
  scope_id: string;
  detected_at: string;
  algorithm: string;
  threshold_used: number;
  metric_name: string;
  expected_value: number;
  actual_value: number;
  deviation_percent: number;
  z_score?: number;
  alert_sent: boolean;
  alert_sent_at?: string;
  dismissed_by?: string;
  dismissed_at?: string;
  context: Record<string, unknown>;
}

export interface AnomalyListResponse {
  anomalies: MarketAnomaly[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnomalyStatsResponse {
  total: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  undismissed: number;
}

export interface AnomalyDismissRequest {
  dismissed_by?: string;
  reason?: string;
}

export interface AnomalyFilterParams {
  limit?: number;
  offset?: number;
  severity?: AnomalySeverity;
  anomaly_type?: AnomalyType;
  scope_type?: AnomalyScope;
  scope_id?: string;
}

// ============================================
// Lead Scoring Types (Task #55)
// ============================================

export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';

export interface Lead {
  id: string;
  visitor_id: string;
  user_id?: string;
  email?: string;
  phone?: string;
  name?: string;
  budget_min?: number;
  budget_max?: number;
  preferred_locations?: string[];
  status: LeadStatus;
  source?: string;
  current_score: number;
  first_seen_at: string;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
  consent_given: boolean;
  consent_at?: string;
}

export interface LeadWithScore extends Lead {
  assigned_agent_id?: string;
  assigned_agent_name?: string;
  latest_score?: LeadScore;
  interaction_count: number;
  // Flattened score properties for convenience
  total_score: number;
  search_activity_score: number;
  engagement_score: number;
  intent_score: number;
}

export interface LeadScore {
  id: string;
  lead_id: string;
  total_score: number;
  search_activity_score: number;
  engagement_score: number;
  intent_score: number;
  score_factors: Record<string, unknown>;
  recommendations?: string[];
  model_version: string;
  calculated_at: string;
}

export interface LeadScoreBreakdown {
  total_score: number;
  components: {
    search_activity: number;
    engagement: number;
    intent: number;
  };
  factors: Record<string, unknown>;
  weights: {
    search_activity: number;
    engagement: number;
    intent: number;
  };
  recommendations: string[];
  percentile?: number;
}

export interface LeadInteraction {
  id: string;
  lead_id: string;
  interaction_type: string;
  property_id?: string;
  search_query?: string;
  metadata?: Record<string, unknown>;
  session_id?: string;
  page_url?: string;
  time_spent_seconds?: number;
  created_at: string;
}

export interface AgentAssignment {
  id: string;
  lead_id: string;
  agent_id: string;
  assigned_by?: string;
  notes?: string;
  is_primary: boolean;
  is_active: boolean;
  assigned_at: string;
}

export interface LeadListResponse {
  items: LeadWithScore[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LeadDetailResponse extends LeadWithScore {
  recent_interactions: LeadInteraction[];
  score_history: LeadScore[];
}

export interface LeadFilters {
  status?: LeadStatus;
  score_min?: number;
  score_max?: number;
  source?: string;
  has_email?: boolean;
  agent_id?: string;
  sort_by?: 'score' | 'created_at' | 'last_activity';
  sort_order?: 'asc' | 'desc';
  search?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}

export interface BulkAssignRequest {
  lead_ids: string[];
  agent_id: string;
  notes?: string;
}

export interface BulkStatusUpdateRequest {
  lead_ids: string[];
  status: LeadStatus;
  notes?: string;
}

export interface BulkOperationResponse {
  success_count: number;
  failed_count: number;
  failed_ids?: string[];
  message: string;
}

export interface RecalculateScoresRequest {
  lead_ids?: string[];
  force?: boolean;
}

export interface RecalculateScoresResponse {
  recalculated_count: number;
  failed_count: number;
  duration_seconds: number;
  message: string;
}

export interface ScoringStatistics {
  total_leads: number;
  high_value_leads: number;
  avg_score: number;
  conversion_rate: number;
  converted_leads: number;
  new_leads_24h: number;
  score_distribution: {
    high_80_100: number;
    medium_50_79: number;
    low_0_49: number;
  };
  scores_calculated_today: number;
  model_version: string;
  weights: {
    search_activity: number;
    engagement: number;
    intent: number;
  };
}

// =============================================================================
// Agent Performance Analytics Types (Task #56)
// =============================================================================

export type DealStatus =
  | 'offer_submitted'
  | 'offer_accepted'
  | 'contract_signed'
  | 'closed'
  | 'fell_through';
export type DealType = 'sale' | 'rent';
export type CommissionStatus = 'pending' | 'approved' | 'paid' | 'clawed_back';
export type CommissionType = 'primary' | 'split' | 'referral';
export type GoalType = 'leads' | 'deals' | 'revenue' | 'gci';
export type PeriodType = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export interface Deal {
  id: string;
  lead_id: string;
  agent_id: string;
  property_id?: string;
  deal_type: DealType;
  deal_value: number;
  currency: string;
  status: DealStatus;
  property_type?: string;
  property_city?: string;
  property_district?: string;
  offer_submitted_at: string;
  offer_accepted_at?: string;
  contract_signed_at?: string;
  closed_at?: string;
  days_to_close?: number;
  created_at: string;
}

export interface DealCreate {
  lead_id: string;
  property_id?: string;
  deal_type: DealType;
  deal_value: number;
  property_type?: string;
  property_city?: string;
  property_district?: string;
  notes?: string;
}

export interface DealListResponse {
  items: Deal[];
  total: number;
  page: number;
  page_size: number;
}

export interface Commission {
  id: string;
  deal_id: string;
  agent_id: string;
  commission_type: CommissionType;
  commission_rate: number;
  commission_amount: number;
  status: CommissionStatus;
  paid_at?: string;
  payment_reference?: string;
  created_at: string;
}

export interface AgentMetrics {
  // Lead metrics
  total_leads: number;
  active_leads: number;
  new_leads_week: number;
  high_value_leads: number;
  // Deal metrics
  total_deals: number;
  active_deals: number;
  closed_deals: number;
  fell_through_deals: number;
  // Conversion metrics
  lead_to_qualified_rate: number;
  qualified_to_deal_rate: number;
  overall_conversion_rate: number;
  // Time metrics
  avg_time_to_first_contact_hours: number | null;
  avg_time_to_qualify_days: number | null;
  avg_time_to_close_days: number | null;
  // Financial metrics
  total_deal_value: number;
  avg_deal_value: number;
  total_commission: number;
  pending_commission: number;
  // Strengths
  top_property_types: Array<{ type: string; count: number; percentage: number }>;
  top_locations: Array<{ location: string; count: number; percentage: number }>;
  avg_lead_score: number;
  // Period comparison
  deals_change_percent: number | null;
  revenue_change_percent: number | null;
}

export interface TeamComparison {
  agent_id: string;
  agent_name: string;
  rank_by_deals: number;
  rank_by_revenue: number;
  rank_by_conversion: number;
  total_agents: number;
  deals_vs_avg_percent: number;
  revenue_vs_avg_percent: number;
  conversion_vs_avg_percent: number;
  time_to_close_vs_avg_percent: number;
  team_avg_deals: number;
  team_avg_revenue: number;
  team_avg_conversion: number;
  team_avg_time_to_close_days: number;
}

export interface PerformanceTrendPoint {
  period: string;
  period_start: string;
  period_end: string;
  leads: number;
  deals_closed: number;
  revenue: number;
  conversion_rate: number;
  avg_deal_value: number;
}

export interface PerformanceTrendsResponse {
  trends: PerformanceTrendPoint[];
  interval: string;
}

export interface CoachingInsight {
  category: 'strength' | 'improvement' | 'opportunity';
  title: string;
  description: string;
  actionable_recommendation: string;
  priority: number;
}

export interface CoachingInsightsResponse {
  insights: CoachingInsight[];
}

export interface GoalProgress {
  id: string;
  goal_type: GoalType;
  target_value: number;
  current_value: number;
  progress_percent: number;
  period_type: PeriodType;
  period_start: string;
  period_end: string;
  is_achieved: boolean;
  days_remaining: number;
}

export interface GoalProgressListResponse {
  goals: GoalProgress[];
}

export interface TopPerformerEntry {
  agent_id: string;
  agent_name: string;
  agent_email?: string;
  metric_value: number;
  rank: number;
}

export interface TopPerformersResponse {
  performers: TopPerformerEntry[];
  metric: string;
  period_days: number;
}

export interface AgentNeedingSupport {
  agent_id: string;
  agent_name: string;
  agent_email?: string;
  days_without_deal: number;
  total_leads: number;
  conversion_rate: number;
  last_deal_at?: string;
  suggested_actions: string[];
}

export interface AgentsNeedingSupportResponse {
  agents: AgentNeedingSupport[];
  threshold_days: number;
}

// =============================================================================
// Agent/Broker Types (Task #45)
// =============================================================================

export type InquiryStatus = 'new' | 'read' | 'responded' | 'closed';
export type InquiryType = 'general' | 'property' | 'financing' | 'viewing';
export type AppointmentStatus = 'requested' | 'confirmed' | 'cancelled' | 'completed';
export type ListingType = 'sale' | 'rent';

// Agent Profile
export interface AgentProfile {
  id: string;
  user_id: string;
  name?: string;
  email?: string;
  agency_name?: string;
  license_number?: string;
  license_state?: string;
  professional_email?: string;
  professional_phone?: string;
  office_address?: string;
  specialties?: string[];
  service_areas?: string[];
  property_types?: string[];
  languages?: string[];
  average_rating: number;
  total_reviews: number;
  total_sales: number;
  total_rentals: number;
  is_verified: boolean;
  is_active: boolean;
  profile_image_url?: string;
  bio?: string;
  created_at: string;
  updated_at: string;
}

export interface AgentProfileCreate {
  agency_name?: string;
  license_number?: string;
  license_state?: string;
  professional_email?: string;
  professional_phone?: string;
  office_address?: string;
  specialties?: string[];
  service_areas?: string[];
  property_types?: string[];
  languages?: string[];
  bio?: string;
  profile_image_url?: string;
}

export interface AgentProfileUpdate extends Partial<AgentProfileCreate> {
  is_active?: boolean;
}

export interface AgentProfileListResponse {
  items: AgentProfile[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Agent Listing (property-agent relationship)
export interface AgentListing {
  id: string;
  agent_id: string;
  property_id: string;
  listing_type: ListingType;
  is_primary: boolean;
  is_active: boolean;
  commission_rate?: number;
  created_at: string;
  property?: Property;
}

export interface AgentListingListResponse {
  items: AgentListing[];
  total: number;
}

// Agent Inquiry (contact form)
export interface AgentInquiry {
  id: string;
  agent_id: string;
  user_id?: string;
  visitor_id?: string;
  name: string;
  email: string;
  phone?: string;
  property_id?: string;
  inquiry_type: InquiryType;
  message: string;
  status: InquiryStatus;
  created_at: string;
  read_at?: string;
  responded_at?: string;
}

export interface AgentInquiryCreate {
  name: string;
  email: string;
  phone?: string;
  property_id?: string;
  inquiry_type: InquiryType;
  message: string;
}

export interface AgentInquiryUpdate {
  status?: InquiryStatus;
}

export interface AgentInquiryListResponse {
  items: AgentInquiry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Viewing Appointment
export interface ViewingAppointment {
  id: string;
  agent_id: string;
  user_id?: string;
  visitor_id?: string;
  client_name: string;
  client_email: string;
  client_phone?: string;
  property_id?: string;
  proposed_datetime: string;
  confirmed_datetime?: string;
  duration_minutes: number;
  status: AppointmentStatus;
  notes?: string;
  cancellation_reason?: string;
  created_at: string;
  updated_at: string;
  agent_name?: string;
}

export interface ViewingAppointmentCreate {
  property_id?: string;
  proposed_datetime: string;
  duration_minutes?: number;
  client_name: string;
  client_email: string;
  client_phone?: string;
  notes?: string;
}

export interface ViewingAppointmentUpdate {
  proposed_datetime?: string;
  confirmed_datetime?: string;
  duration_minutes?: number;
  status?: AppointmentStatus;
  notes?: string;
  cancellation_reason?: string;
}

export interface ViewingAppointmentListResponse {
  items: ViewingAppointment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Agent Filters for search
export interface AgentFilters {
  city?: string;
  specialty?: string;
  property_type?: string;
  min_rating?: number;
  agency_id?: string;
  is_verified?: boolean;
  is_active?: boolean;
  language?: string;
  sort_by?: 'rating' | 'listings' | 'reviews' | 'created';
  sort_order?: 'asc' | 'desc';
}

// =============================================================================
// Document Management Types (Task #43)
// =============================================================================

export type DocumentCategory = 'contract' | 'inspection' | 'photo' | 'financial' | 'other';

export type OCRStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: string;
  user_id: string;
  property_id?: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  category?: DocumentCategory;
  tags?: string[];
  description?: string;
  expiry_date?: string;
  ocr_status: OCRStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  message: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentUpdateRequest {
  property_id?: string;
  category?: DocumentCategory;
  tags?: string[];
  description?: string;
  expiry_date?: string;
}

export interface DocumentFilters {
  property_id?: string;
  category?: DocumentCategory;
  ocr_status?: OCRStatus;
  search_query?: string;
  sort_by?: 'created_at' | 'updated_at' | 'filename' | 'file_size' | 'expiry_date';
  sort_order?: 'asc' | 'desc';
}

export interface ExpiringDocumentsResponse {
  items: Document[];
  total: number;
  days_ahead: number;
}

// =============================================================================
// E-Signature Types (Task #57)
// =============================================================================

export type TemplateType = 'rental_agreement' | 'purchase_offer' | 'lease_renewal' | 'custom';
export type TemplateCategory =
  | 'rental'
  | 'purchase'
  | 'lease'
  | 'custom'
  | 'default'
  | 'user_created'
  | 'system'
  | 'builtin';
export type ESignatureProvider = 'hellosign' | 'docusign';
export type SignatureRequestStatus =
  | 'draft'
  | 'sent'
  | 'viewed'
  | 'partially_signed'
  | 'completed'
  | 'expired'
  | 'cancelled'
  | 'declined';
export type SignerStatus = 'pending' | 'viewed' | 'signed' | 'declined';
export type SignerRole = 'landlord' | 'tenant' | 'buyer' | 'seller' | 'agent' | 'witness' | 'other';

// Signer
export interface Signer {
  email: string;
  name: string;
  role: SignerRole;
  order: number;
  status: SignerStatus;
  signed_at?: string;
  signature_url?: string;
}

// Signature Request
export interface SignatureRequest {
  id: string;
  user_id: string;
  title: string;
  subject?: string;
  message?: string;
  document_id?: string;
  template_id?: string;
  property_id?: string;
  provider: ESignatureProvider;
  provider_envelope_id?: string;
  signers: Signer[];
  status: SignatureRequestStatus;
  variables?: Record<string, unknown>;
  created_at: string;
  sent_at?: string;
  viewed_at?: string;
  completed_at?: string;
  expires_at?: string;
  cancelled_at?: string;
  reminder_count?: number;
  error_message?: string;
}

// Signature Request Create
export interface SignatureRequestCreate {
  title: string;
  template_id?: string;
  document_id?: string;
  subject?: string;
  message?: string;
  signers: Array<{
    email: string;
    name: string;
    role: SignerRole;
    order: number;
  }>;
  variables?: Record<string, unknown>;
  property_id?: string;
  expires_in_days?: number;
  provider?: ESignatureProvider;
}

// Signature Request List Response
export interface SignatureRequestListResponse {
  items: SignatureRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Signature Request Filters
export interface SignatureRequestFilters {
  status?: SignatureRequestStatus;
  property_id?: string;
  page?: number;
  page_size?: number;
  sort_by?: 'created_at' | 'updated_at' | 'title' | 'status';
  sort_order?: 'asc' | 'desc';
}

// Document Template
export interface DocumentTemplate {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  template_type: TemplateType;
  content: string;
  variables?: Record<string, unknown>;
  is_default: boolean;
  category?: TemplateCategory;
  tags?: string[];
  expiry_date?: string;
  created_at: string;
  updated_at: string;
}

// Document Template Create
export interface DocumentTemplateCreate {
  name: string;
  template_type: TemplateType;
  content: string;
  description?: string;
  variables?: Record<string, unknown>;
  is_default?: boolean;
  category?: TemplateCategory;
  tags?: string[];
  expiry_date?: string;
}

// Document Template Update
export interface DocumentTemplateUpdate {
  name?: string;
  description?: string;
  content?: string;
  variables?: Record<string, unknown>;
  is_default?: boolean;
  category?: TemplateCategory;
  tags?: string[];
  expiry_date?: string;
}

// Document Template List Response
export interface DocumentTemplateListResponse {
  items: DocumentTemplate[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Signed Document
export interface SignedDocument {
  id: string;
  signature_request_id: string;
  document_id?: string;
  storage_path: string;
  file_size: number;
  provider_document_id?: string;
  certificate_url?: string;
  created_at: string;
}

// =============================================================================
// Data Sources Types (Task #79)
// =============================================================================

export type DataSourceType = 'file_upload' | 'url' | 'portal_api' | 'json';
export type DataSourceStatus = 'pending' | 'active' | 'syncing' | 'error' | 'disabled';
export type SyncStatus = 'pending' | 'running' | 'success' | 'failed' | 'partial';

export interface DataSource {
  id: string;
  name: string;
  source_type: DataSourceType;
  config: Record<string, unknown>;
  status: DataSourceStatus;
  last_sync_at?: string;
  last_sync_status?: SyncStatus;
  last_error?: string;
  total_records: number;
  health_score: number;
  consecutive_failures: number;
  auto_sync_enabled: boolean;
  sync_schedule?: string;
  created_at: string;
  updated_at: string;
}

export interface DataSourceCreate {
  name: string;
  source_type: DataSourceType;
  config: Record<string, unknown>;
  auto_sync_enabled?: boolean;
  sync_schedule?: string;
}

export interface DataSourceUpdate {
  name?: string;
  config?: Record<string, unknown>;
  auto_sync_enabled?: boolean;
  sync_schedule?: string;
  status?: DataSourceStatus;
}

export interface DataSourceListResponse {
  sources: DataSource[];
  total: number;
  page: number;
  page_size: number;
}

export interface DataSourceSyncResponse {
  source_id: string;
  status: string;
  message: string;
  records_processed: number;
  started_at: string;
}

export interface DataSourceTestRequest {
  source_type: DataSourceType;
  config: Record<string, unknown>;
}

export interface DataSourceTestResponse {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
}

// =============================================================================
// Task #71: MCP Connector Registry Types
// ============================================================================

export interface MCPConnectorInfo {
  name: string;
  display_name: string;
  description: string;
  enabled: boolean;
  edition: string;
  status: 'active' | 'disabled' | 'error' | 'not_instantiated' | 'unknown';
  accessible_in_ce: boolean;
  registered: boolean;
  has_instance: boolean;
  requires_api_key: boolean;
  supports_streaming: boolean;
  min_edition: string;
  last_health_check?: string;
  error_message?: string;
}

export interface MCPConnectorsListResponse {
  connectors: MCPConnectorInfo[];
  edition: string;
  total: number;
}

export interface MCPConnectorDetailResponse extends MCPConnectorInfo {
  rate_limit?: {
    connector_name: string;
    requests_per_minute: number;
    burst_size: number;
    enabled: boolean;
    current_requests: number;
    remaining: number;
    reset_at: number;
  };
  config?: Record<string, unknown>;
  instance_status?: Record<string, unknown>;
}

export interface MCPConnectorHealthResponse {
  name: string;
  status: 'healthy' | 'unhealthy' | 'error';
  success: boolean;
  errors: string[];
  warnings: string[];
  response_time_ms?: number;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface MCPHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  edition: string;
  connectors_checked: number;
  results: Record<string, { success: boolean; errors: string[] }>;
  timestamp: string;
}

export interface SyncHistoryItem {
  id: string;
  started_at: string;
  completed_at?: string;
  status: SyncStatus;
  records_processed: number;
  records_added: number;
  records_updated: number;
  records_failed: number;
  error_message?: string;
}

export interface SyncHistoryResponse {
  source_id: string;
  history: SyncHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Bulk Jobs Types (Task #80: Import/Export Data API)
// =============================================================================

export type BulkJobType = 'import' | 'export';
export type BulkJobSourceType = 'url' | 'file_upload' | 'portal_api' | 'search';
export type BulkJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface BulkImportRequest {
  source_type: BulkJobSourceType;
  config: Record<string, unknown>;
  source_name?: string;
}

export interface BulkExportRequest {
  format: string;
  source_type?: BulkJobSourceType;
  config: Record<string, unknown>;
  columns?: string[];
  include_header?: boolean;
}

export interface BulkJobResponse {
  id: string;
  job_type: BulkJobType;
  source_type: BulkJobSourceType;
  status: BulkJobStatus;
  records_total: number;
  records_processed: number;
  records_failed: number;
  progress_percent: number;
  result_url?: string;
  result_data?: Record<string, unknown>;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  expires_at?: string;
}

export interface BulkJobListResponse {
  jobs: BulkJobResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface BulkJobCreateResponse {
  id: string;
  job_type: BulkJobType;
  status: BulkJobStatus;
  message: string;
  created_at: string;
}

// =============================================================================
// User Activity Analytics Types (Task #82)
// =============================================================================

export interface UserActivitySummary {
  period_start: string;
  period_end: string;
  total_searches: number;
  total_property_views: number;
  total_property_clicks: number;
  total_tool_uses: number;
  total_exports: number;
  total_favorites: number;
  unique_sessions: number;
  avg_processing_time_ms?: number;
  top_tools: Array<{ tool_name: string; count: number }>;
  top_search_cities: Array<{ city: string; count: number }>;
  event_counts_by_day: Array<{ date: string; count: number }>;
}

export interface UserActivityTrendPoint {
  date: string;
  searches: number;
  property_views: number;
  tool_uses: number;
  exports: number;
}

export interface UserActivityTrendsResponse {
  trends: UserActivityTrendPoint[];
  interval: string;
}

// =============================================================================
// Task #87: Per-Task Model Preferences Types
// =============================================================================

export type TaskType = 'chat' | 'search' | 'tools' | 'analysis' | 'embedding';

export interface FallbackChainItem {
  provider: string;
  model_name: string;
}

export interface TaskModelPreference {
  id: string;
  user_id: string;
  task_type: TaskType;
  provider: string;
  model_name: string;
  fallback_chain: FallbackChainItem[] | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskModelPreferenceCreate {
  task_type: TaskType;
  provider: string;
  model_name: string;
  fallback_chain?: FallbackChainItem[];
  is_active?: boolean;
}

export interface TaskModelPreferenceUpdate {
  provider?: string;
  model_name?: string;
  fallback_chain?: FallbackChainItem[];
  is_active?: boolean;
}

export interface TaskModelPreferenceListResponse {
  items: TaskModelPreference[];
  total: number;
}

export interface SystemDefaultModelPreference {
  task_type: TaskType;
  provider: string;
  model_name: string;
  description?: string;
  cost_per_1m_input_tokens?: number;
  cost_per_1m_output_tokens?: number;
}

export interface SystemDefaultsResponse {
  defaults: SystemDefaultModelPreference[];
  available_providers: string[];
  available_models: Record<string, string[]>;
}

export interface ModelCostEstimate {
  provider: string;
  model_name: string;
  input_cost_per_1m: number | null;
  output_cost_per_1m: number | null;
  estimated_tokens_per_request: number;
  estimated_cost_per_request: number | null;
}

// =============================================================================
// Task #88: User Profile Management Types
// =============================================================================

export interface ProfileUpdate {
  full_name?: string;
  phone?: string;
  bio?: string;
  timezone?: string;
  language?: string;
}

export interface ProfileResponse {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  avatar_url: string | null;
  timezone: string;
  language: string;
  bio: string | null;
  privacy_settings: PrivacySettings;
  is_active: boolean;
  is_verified: boolean;
  role: string;
  created_at: string;
  last_login_at: string | null;
  gdpr_consent_at: string | null;
}

export interface PrivacySettings {
  profile_visible: boolean;
  activity_visible: boolean;
  show_email: boolean;
  show_phone: boolean;
  allow_contact: boolean;
}

export interface AvatarUploadResponse {
  avatar_url: string;
  message: string;
}

export interface DataExportRequest {
  format: 'json' | 'csv';
  include_favorites: boolean;
  include_search_history: boolean;
  include_documents: boolean;
}

export interface DataExportResponse {
  export_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  format: string;
  includes: string[];
  created_at: string;
}

export interface DataExportStatusResponse {
  export_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_percent: number;
  download_url: string | null;
  expires_at: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

// ============================================================================
// CMA (Comparative Market Analysis) Types - Task #85
// ============================================================================

export type CMAStatus = 'draft' | 'completed' | 'expired';

export interface CMAAdjustment {
  category: string;
  description: string;
  subject_value: string | null;
  comp_value: string | null;
  adjustment_percent: number;
  adjustment_amount: number;
  confidence: number;
}

export interface CMAComparable {
  property_id: string;
  similarity_score: number;
  adjustments: CMAAdjustment[];
  adjusted_price: number;
  currency?: string;
}

export interface CMAValuation {
  estimated_value: number;
  value_range_low: number;
  value_range_high: number;
  confidence_score: number;
  price_per_sqm: number;
}

export interface CMAReportCreate {
  subject_property_id: string;
  comparable_ids?: string[];
  max_distance_km?: number;
  min_comparables?: number;
  max_comparables?: number;
}

export interface CMAReport {
  id: string;
  user_id: string;
  status: CMAStatus;
  subject_property: Record<string, unknown>;
  comparables: CMAComparable[];
  valuation: CMAValuation;
  market_context?: Record<string, unknown> | null;
  created_at: string;
  expires_at: string | null;
}

export interface CMAReportListResponse {
  reports: CMAReport[];
  total: number;
  page: number;
  page_size: number;
}
