import toast from 'react-hot-toast';

/**
 * Toast notification utility
 * Provides consistent toast notifications across the application
 * Uses react-hot-toast for better UX and smaller bundle size
 */

// Default toast configuration
const toastConfig = {
    duration: 3000,
    position: 'bottom-right',

    // Custom styling for modern look
    style: {
        borderRadius: '8px',
        background: '#333',
        color: '#fff',
        padding: '12px 16px',
        fontSize: '14px',
        maxWidth: '500px',
    },
};

// Variant-specific styles
const variantStyles = {
    success: {
        iconTheme: {
            primary: '#10b981',
            secondary: '#fff',
        },
    },
    error: {
        iconTheme: {
            primary: '#ef4444',
            secondary: '#fff',
        },
    },
    info: {
        icon: 'ℹ️',
        iconTheme: {
            primary: '#3b82f6',
            secondary: '#fff',
        },
    },
    warning: {
        icon: '⚠️',
        iconTheme: {
            primary: '#f59e0b',
            secondary: '#fff',
        },
    },
};

/**
 * Generic toast notification utility
 * Maintains backward compatibility with previous API
 */
export const showToast = {
    /**
     * Show success toast
     * @param {string} message - Message to display
     * @param {object} options - Additional options to override defaults
     */
    success: (message, options = {}) => {
        return toast.success(message, {
            ...toastConfig,
            ...variantStyles.success,
            ...options,
        });
    },

    /**
     * Show error toast
     * @param {string} message - Message to display
     * @param {object} options - Additional options to override defaults
     */
    error: (message, options = {}) => {
        return toast.error(message, {
            ...toastConfig,
            ...variantStyles.error,
            ...options,
        });
    },

    /**
     * Show info toast
     * @param {string} message - Message to display
     * @param {object} options - Additional options to override defaults
     */
    info: (message, options = {}) => {
        return toast(message, {
            ...toastConfig,
            ...variantStyles.info,
            ...options,
        });
    },

    /**
     * Show warning toast
     * @param {string} message - Message to display
     * @param {object} options - Additional options to override defaults
     */
    warning: (message, options = {}) => {
        return toast(message, {
            ...toastConfig,
            ...variantStyles.warning,
            ...options,
        });
    },

    /**
     * Show promise-based toast
     * @param {Promise} promise - Promise to track
     * @param {object} messages - Messages for different states
     * @param {object} options - Additional options to override defaults
     */
    promise: (promise, messages, options = {}) => {
        return toast.promise(
            promise,
            {
                loading: messages.pending || 'Processing...',
                success: messages.success || 'Success!',
                error: messages.error || 'Something went wrong',
            },
            {
                ...toastConfig,
                ...options,
            }
        );
    },

    /**
     * Custom toast with full control
     * @param {string} message - Message to display
     * @param {object} options - Toast options
     */
    custom: (message, options = {}) => {
        return toast(message, {
            ...toastConfig,
            ...options,
        });
    },

    /**
     * Dismiss a specific toast or all toasts
     * @param {string} toastId - Optional toast ID to dismiss
     */
    dismiss: (toastId) => {
        if (toastId) {
            toast.dismiss(toastId);
        } else {
            toast.dismiss();
        }
    },
};

/**
 * Helper to extract error message from various error formats
 */
export const getErrorMessage = (error) => {
    if (typeof error === 'string') return error;

    if (error?.response?.data?.detail) {
        // FastAPI error format
        if (typeof error.response.data.detail === 'string') {
            return error.response.data.detail;
        }
        if (Array.isArray(error.response.data.detail)) {
            return error.response.data.detail.map(e => e.msg).join(', ');
        }
    }

    if (error?.response?.data?.message) {
        return error.response.data.message;
    }

    if (error?.message) {
        return error.message;
    }

    return 'An unexpected error occurred';
};

export default showToast;
