/**
 * API barrel export.
 *
 * Re-exports all domain-specific modules so that existing imports
 * like `import { ... } from '@/lib/api'` continue to work unchanged.
 */

// Base client utilities and error types
export {
  ApiError,
  getApiUrl,
  getUserEmail,
  buildAuthHeaders,
  buildHeaders,
  buildMultipartHeaders,
  safeFetch,
  handleResponse,
} from './client';
export type { ApiErrorCategory } from './client';

// Settings: notifications, model catalog, model preferences, per-task model preferences
export {
  getNotificationSettings,
  updateNotificationSettings,
  sendNotificationPreview,
  unsubscribeByToken,
  getModelsCatalog,
  testModelRuntime,
  getModelPreferences,
  updateModelPreferences,
  getTaskModelPreferences,
  getTaskModelPreference,
  createTaskModelPreference,
  updateTaskModelPreference,
  deleteTaskModelPreference,
  getSystemModelDefaults,
  getModelCostEstimate,
} from './settings';

// Tools: calculators, analysis, commute, listing generation
export {
  calculateMortgage,
  calculateTCO,
  compareTCO,
  getTCOLocationDefaults,
  getTCOAvailableLocations,
  calculateInvestment,
  neighborhoodQualityApi,
  getNeighborhoodBadge,
  comparePropertiesApi,
  priceAnalysisApi,
  locationAnalysisApi,
  valuationApi,
  legalCheckApi,
  enrichAddressApi,
  calculateAdvancedInvestment,
  analyzePortfolio,
  calculateRentVsBuy,
  generateListing,
  calculateCommuteTime,
  rankPropertiesByCommute,
  // v5.1: AI price forecast and neighborhood one-liner
  priceForecastApi,
  neighborhoodSummaryApi,
} from './tools';

// Chat: message and streaming
export { chatMessage, streamChatMessage } from './chat';

// Search: property search, export, feedback
export {
  searchProperties,
  exportPropertiesBySearch,
  exportPropertiesByIds,
  submitFeedback,
} from './search';

// Admin: data ingestion, Excel, portals
export {
  ingestData,
  getExcelSheets,
  ingestFileUpload,
  getExcelSheetsUpload,
  listPortals,
  fetchFromPortal,
} from './admin';

// Favorites, Collections, Saved Searches, Filter Presets
export {
  getSavedSearches,
  createSavedSearch,
  getSavedSearch,
  updateSavedSearch,
  deleteSavedSearch,
  toggleSavedSearchAlert,
  markSavedSearchUsed,
  getFavorites,
  addFavorite,
  removeFavorite,
  removeFavoriteByProperty,
  checkFavorite,
  getFavoriteIds,
  updateFavorite,
  moveFavoriteToCollection,
  getCollections,
  createCollection,
  getDefaultCollection,
  getCollection,
  updateCollection,
  deleteCollection,
  getFilterPresets,
  getFilterPreset,
  getDefaultFilterPreset,
  createFilterPreset,
  updateFilterPreset,
  deleteFilterPreset,
  markFilterPresetUsed,
  setFilterPresetDefault,
} from './favorites';

// Market: price history, trends, indicators, area comparison, anomalies
export {
  getPriceHistory,
  getMarketTrends,
  getMarketIndicators,
  compareAreas,
  getAreaInsights,
  getAnomalies,
  getAnomaly,
  dismissAnomaly,
  getAnomalyStats,
  subscribeToAnomalies,
} from './market';

// Lead Scoring
export {
  getLeads,
  getHighValueLeads,
  getLead,
  getLeadScoreBreakdown,
  updateLead,
  updateLeadStatus,
  assignAgentToLead,
  bulkAssignLeads,
  bulkUpdateLeadStatus,
  recalculateScores,
  getScoringStatistics,
  exportLeads,
  deleteLead,
} from './leads';

// Agent/Broker and Agent Performance Analytics
export {
  getAgentMetrics,
  getTeamComparison,
  getPerformanceTrends,
  getCoachingInsights,
  getGoalProgress,
  getTopPerformers,
  getAgentsNeedingSupport,
  createDeal,
  getMyDeals,
  getDeal,
  updateDeal,
  getAgents,
  getAgent,
  getAgentListings,
  contactAgent,
  scheduleViewing,
  getOwnAgentProfile,
  createAgentProfile,
  updateOwnAgentProfile,
  getOwnInquiries,
  updateInquiry,
  getOwnAppointments,
  updateAppointment,
} from './agents';

// Document Management, E-Signature, Document Templates
export {
  uploadDocument,
  getDocuments,
  getExpiringDocuments,
  getDocumentDownloadUrl,
  updateDocument,
  deleteDocument,
  createSignatureRequest,
  getSignatureRequests,
  getSignatureRequest,
  cancelSignatureRequest,
  sendSignatureReminder,
  getSignedDocumentDownloadUrl,
  getDocumentTemplates,
  getDocumentTemplate,
  createDocumentTemplate,
  updateDocumentTemplate,
  deleteDocumentTemplate,
} from './documents';

// Data Sources, Bulk Jobs, MCP Connectors
export {
  listDataSources,
  createDataSource,
  getDataSource,
  updateDataSource,
  deleteDataSource,
  syncDataSource,
  testDataSource,
  getDataSourceSyncHistory,
  listMCPConnectors,
  getMCPConnector,
  healthCheckMCPConnector,
  healthCheckAllMCPConnectors,
  createBulkImportJob,
  createBulkExportJob,
  listBulkJobs,
  getBulkJob,
  cancelBulkJob,
  deleteBulkJob,
} from './data-sources';

// User Profile, Activity Analytics, RAG, Prompt Templates, CRM
export {
  uploadRagDocuments,
  resetRagKnowledge,
  ragQa,
  crmSyncContactApi,
  listPromptTemplates,
  applyPromptTemplate,
  getUserActivitySummary,
  getUserActivityTrends,
  exportUserActivityCSV,
  getProfile,
  updateProfile,
  uploadAvatar,
  deleteAvatar,
  updatePrivacySettings,
  requestDataExport,
  getExportStatus,
} from './user';

// CMA (Comparative Market Analysis)
export {
  findComparables,
  generateCMAReport,
  getCMAReport,
  downloadCMAPdf,
  listCMAReports,
  deleteCMAReport,
} from './cma';
