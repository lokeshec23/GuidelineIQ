import axios from "axios";
import { showToast, getErrorMessage } from "../utils/toast";


// Use environment variable with fallback for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8003";


// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Check sessionStorage first, then localStorage
    const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        let refreshToken = sessionStorage.getItem("refresh_token");
        let storage = sessionStorage;

        if (!refreshToken) {
          refreshToken = localStorage.getItem("refresh_token");
          storage = localStorage;
        }

        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          storage.setItem("access_token", access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("refresh_token");
        sessionStorage.removeItem("user");

        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");

        showToast.error("Session expired. Please login again.");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    // Show error toast for all errors except:
    // - 401 (handled above for token refresh)
    // - Auth endpoints (login/register - handled in AuthContext)
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/login') ||
      originalRequest?.url?.includes('/auth/register');

    if (error.response?.status !== 401 && !isAuthEndpoint) {
      const errorMessage = getErrorMessage(error);
      showToast.error(errorMessage);
    }

    return Promise.reject(error);
  }
);


// ==================== AUTH APIs ====================
export const authAPI = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
  getCurrentUser: () => api.get("/auth/me"),
};

// ==================== SETTINGS APIs ====================
export const settingsAPI = {
  getSettings: () => api.get("/settings"),
  updateSettings: (data) => api.post("/settings", data),
  getSupportedModels: () => api.get("/settings/models"),
  deleteSettings: () => api.delete("/settings"),
};

// ==================== INGEST APIs ====================
// Add to ingestAPI object
// ==================== INGEST APIs ====================
export const ingestAPI = {
  ingestGuideline: (formData) =>
    api.post("/ingest/guideline", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  getStatus: (sessionId) => api.get(`/ingest/status/${sessionId}`),

  // Get preview data (JSON)
  getPreview: (sessionId) => api.get(`/ingest/preview/${sessionId}`),

  // ✅ NEW: Get Excel as base64
  getExcelBase64: (sessionId) => api.get(`/ingest/excel/${sessionId}`),


  // ✅ Download Excel file
  downloadExcel: (sessionId) => {
    const link = document.createElement("a");
    link.href = `${API_BASE_URL}/ingest/download/${sessionId}`;
    link.download = "extraction.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  // Cleanup session
  cleanupSession: (sessionId) => api.delete(`/ingest/cleanup/${sessionId}`),
};

// ==================== COMPARE APIs ====================
export const compareAPI = {
  compareGuidelines: (formData) =>
    api.post("/compare/guidelines", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  getStatus: (sessionId) => api.get(`/compare/status/${sessionId}`),

  createProgressStream: (sessionId) => {
    return new EventSource(`${API_BASE_URL}/compare/progress/${sessionId}`);
  },

  getPreview: (sessionId) => api.get(`/compare/preview/${sessionId}`),


  downloadExcel: (sessionId) => {
    const link = document.createElement("a");
    link.href = `${API_BASE_URL}/compare/download/${sessionId}`;
    link.download = "comparison.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  compareFromDB: (data) => api.post("/compare/from-db", data),
};

// ==================== HISTORY APIs ====================
export const historyAPI = {
  getIngestHistory: () => api.get("/history/ingest"),
  deleteIngestHistory: (id) => api.delete(`/history/ingest/${id}`),
  deleteAllIngestHistory: () => api.delete("/history/ingest"),
  getCompareHistory: () => api.get("/history/compare"),
  deleteCompareHistory: (id) => api.delete(`/history/compare/${id}`),
  deleteAllCompareHistory: () => api.delete("/history/compare"),
};

// ==================== CHAT APIs ====================
export const chatAPI = {
  sendMessage: ({ session_id, conversation_id, message, mode = "excel", instructions = null }) =>
    api.post(`/chat/session/${session_id}/message`, { conversation_id, message, mode, instructions }),

  getChatHistory: (session_id) =>
    api.get(`/chat/session/${session_id}/history`),

  clearChatHistory: (session_id) =>
    api.delete(`/chat/session/${session_id}/history`),

  // Conversation management
  createConversation: (session_id, title = null) =>
    api.post(`/chat/session/${session_id}/conversations`, { title }),

  getConversations: (session_id) =>
    api.get(`/chat/session/${session_id}/conversations`),

  deleteConversation: (conversation_id) =>
    api.delete(`/chat/conversation/${conversation_id}`),

  getConversationMessages: (conversation_id, limit = 100) =>
    api.get(`/chat/conversation/${conversation_id}/messages`, { params: { limit } }),
};

// Prompts API
export const promptsAPI = {
  getUserPrompts: () => api.get("/prompts"),
  saveUserPrompts: (prompts) => api.put("/prompts", prompts),
  resetUserPrompts: () => api.post("/prompts/reset"),
};

// Export API_BASE_URL for use in components
export { API_BASE_URL };

export default api;
