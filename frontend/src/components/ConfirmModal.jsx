// src/components/ConfirmModal.jsx

import React from "react";
import { Modal, Button } from "antd";
import { ExclamationCircleOutlined } from "@ant-design/icons";

/**
 * Reusable Confirmation Modal Component with Ant Design styling and Jura font
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
            closable={true}
            centered
            width={416}
            footer={[
                <Button
                    key="cancel"
                    onClick={onCancel}
                    disabled={loading}
                    style={{ fontFamily: 'Jura, sans-serif' }}
                >
                    {cancelText}
                </Button>,
                <Button
                    key="confirm"
                    type={confirmType}
                    danger={danger}
                    onClick={onConfirm}
                    loading={loading}
                    style={{ fontFamily: 'Jura, sans-serif' }}
                >
                    {confirmText}
                </Button>
            ]}
            styles={{
                header: { fontFamily: 'Jura, sans-serif' },
                body: { fontFamily: 'Jura, sans-serif' }
            }}
        >
            <div style={{ display: 'flex', gap: '12px', fontFamily: 'Jura, sans-serif' }}>
                <ExclamationCircleOutlined
                    style={{
                        fontSize: '22px',
                        color: danger ? '#ff4d4f' : '#faad14',
                        marginTop: '4px'
                    }}
                />
                <div style={{ flex: 1 }}>
                    <div style={{
                        fontSize: '16px',
                        fontWeight: 500,
                        marginBottom: '8px',
                        color: 'rgba(0, 0, 0, 0.88)'
                    }}>
                        {title}
                    </div>
                    <div style={{
                        fontSize: '14px',
                        color: 'rgba(0, 0, 0, 0.65)',
                        lineHeight: '1.5715'
                    }}>
                        {message}
                    </div>
                </div>
            </div>
        </Modal>
    );
};

export default ConfirmModal;
