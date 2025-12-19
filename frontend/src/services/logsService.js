// frontend/src/services/logsService.js

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003';

// Get access token from localStorage
const getToken = () => {
    return localStorage.getItem('access_token');
};

// Get logs with filtering and pagination
export const getLogs = async (params = {}) => {
    const token = getToken();
    const response = await axios.get(`${API_BASE_URL}/logs`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
        params,
    });
    return response.data;
};

// Get log statistics
export const getLogStats = async () => {
    const token = getToken();
    const response = await axios.get(`${API_BASE_URL}/logs/stats`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });
    return response.data;
};

// Export logs as CSV
export const exportLogs = async (params = {}) => {
    const token = getToken();
    const response = await axios.get(`${API_BASE_URL}/logs/export`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
        params,
        responseType: 'blob',
    });

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `activity_logs_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
};

// Connect to WebSocket for real-time log streaming
export const connectWebSocket = (onMessage, onError, onClose) => {
    const token = getToken();
    const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/logs/stream?token=${token}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (onMessage) {
                onMessage(data);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (onError) {
            onError(error);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (onClose) {
            onClose();
        }
    };

    return ws;
};
