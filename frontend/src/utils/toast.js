import { toast } from 'react-toastify';

/**
 * Toast notification utility
 * Provides consistent toast notifications across the application
 */

const toastConfig = {
    position: "top-right",
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
};

export const showToast = {
    success: (message, options = {}) => {
        toast.success(message, { ...toastConfig, ...options });
    },

    error: (message, options = {}) => {
        toast.error(message, { ...toastConfig, ...options });
    },

    info: (message, options = {}) => {
        toast.info(message, { ...toastConfig, ...options });
    },

    warning: (message, options = {}) => {
        toast.warning(message, { ...toastConfig, ...options });
    },

    promise: (promise, messages, options = {}) => {
        return toast.promise(
            promise,
            {
                pending: messages.pending || 'Processing...',
                success: messages.success || 'Success!',
                error: messages.error || 'Something went wrong',
            },
            { ...toastConfig, ...options }
        );
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
