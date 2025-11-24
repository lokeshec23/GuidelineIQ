// src/components/ConfirmModal.jsx

import React from "react";
import { Modal, Button } from "antd";
import { ExclamationCircleOutlined } from "@ant-design/icons";

/**
 * Reusable Confirmation Modal Component
 * 
 * @param {boolean} visible - Controls modal visibility
 * @param {function} onConfirm - Callback when user confirms
 * @param {function} onCancel - Callback when user cancels
 * @param {string} title - Modal title
 * @param {string} message - Confirmation message
 * @param {string} confirmText - Confirm button text (default: "Confirm")
 * @param {string} cancelText - Cancel button text (default: "Cancel")
 * @param {string} confirmType - Confirm button type (default: "primary")
 * @param {boolean} danger - Whether confirm button is danger type (default: false)
 * @param {boolean} loading - Whether confirm button shows loading state
 */
const ConfirmModal = ({
    visible,
    onConfirm,
    onCancel,
    title = "Confirm Action",
    message = "Are you sure you want to proceed?",
    confirmText = "Confirm",
    cancelText = "Cancel",
    confirmType = "primary",
    danger = false,
    loading = false,
}) => {
    return (
        <Modal
            open={visible}
            onCancel={onCancel}
            footer={null}
            closable={false}
            centered
            width={400}
        >
            <div className="py-4">
                {/* Icon and Title */}
                <div className="flex items-start gap-4 mb-4">
                    <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${danger ? "bg-red-100" : "bg-yellow-100"
                        }`}>
                        <ExclamationCircleOutlined
                            className={`text-xl ${danger ? "text-red-600" : "text-yellow-600"}`}
                        />
                    </div>
                    <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            {title}
                        </h3>
                        <p className="text-sm text-gray-600">
                            {message}
                        </p>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end gap-3 mt-6">
                    <Button
                        onClick={onCancel}
                        disabled={loading}
                    >
                        {cancelText}
                    </Button>
                    <Button
                        type={confirmType}
                        danger={danger}
                        onClick={onConfirm}
                        loading={loading}
                    >
                        {confirmText}
                    </Button>
                </div>
            </div>
        </Modal>
    );
};

export default ConfirmModal;
