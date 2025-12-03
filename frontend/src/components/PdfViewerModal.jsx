import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, Space, Spin } from 'antd';
import { CloseOutlined, SearchOutlined, UpOutlined, DownOutlined } from '@ant-design/icons';
import { showToast } from "../utils/toast";

const PdfViewerModal = ({ visible, onClose, pdfUrl, title = "PDF Viewer" }) => {
    const [loading, setLoading] = useState(true);
    const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (visible && pdfUrl) {
            fetchPdfWithAuth();
        }

        // Cleanup blob URL when modal closes
        return () => {
            if (pdfBlobUrl) {
                URL.revokeObjectURL(pdfBlobUrl);
            }
        };
    }, [visible, pdfUrl]);

    const fetchPdfWithAuth = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = sessionStorage.getItem('access_token');

            const response = await fetch(pdfUrl, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to load PDF: ${response.statusText}`);
            }

            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            setPdfBlobUrl(blobUrl);
            setLoading(false);
        } catch (err) {
            console.error('Error loading PDF:', err);
            setError(err.message);
            setLoading(false);
            showToast.error('Failed to load PDF');
        }
    };



    const handleModalClose = () => {
        // Revoke blob URL to free memory
        if (pdfBlobUrl) {
            URL.revokeObjectURL(pdfBlobUrl);
            setPdfBlobUrl(null);
        }
        setLoading(true);
        setError(null);
        onClose();
    };

    return (
        <Modal
            open={visible}
            onCancel={handleModalClose}
            footer={null}
            width="90vw"
            height="90vh"
            style={{ top: 20 }}
            closable={false}
            bodyStyle={{ padding: 0, height: 'calc(90vh - 100px)', display: 'flex', flexDirection: 'column' }}
            zIndex={3000}
        >
            {/* Header */}
            <div className="flex justify-between items-center px-4 py-3 border-b bg-gray-50 flex-shrink-0">
                <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-lg m-0">{title}</h3>
                </div>
                <Button
                    icon={<CloseOutlined />}
                    onClick={handleModalClose}
                >
                    Close
                </Button>
            </div>

            {/* PDF Viewer */}
            <div className="relative flex-1 bg-gray-100 overflow-hidden">
                {loading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                        <Spin size="large" tip="Loading PDF..." />
                    </div>
                )}
                {error && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                        <div className="text-center">
                            <p className="text-red-500 text-lg mb-2">Failed to load PDF</p>
                            <p className="text-gray-600">{error}</p>
                            <Button type="primary" onClick={fetchPdfWithAuth} className="mt-4">
                                Retry
                            </Button>
                        </div>
                    </div>
                )}
                {pdfBlobUrl && !loading && !error && (
                    <iframe
                        id="pdf-iframe"
                        src={pdfBlobUrl}
                        className="w-full h-full border-0"
                        title="PDF Viewer"
                    />
                )}
            </div>

            {/* Search Instructions */}
            {/* <div className="px-4 py-2 bg-blue-50 border-t flex-shrink-0">
                <p className="m-0 text-sm text-blue-800">
                    <strong>💡 To search in PDF:</strong> Use <kbd className="px-2 py-1 bg-white border border-blue-200 rounded text-xs font-mono">Ctrl+F</kbd> (or <kbd className="px-2 py-1 bg-white border border-blue-200 rounded text-xs font-mono">Cmd+F</kbd> on Mac) to open your browser's search tool
                </p>
            </div> */}
        </Modal>
    );
};

export default PdfViewerModal;
