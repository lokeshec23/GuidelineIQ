import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, Space, Spin, message } from 'antd';
import { CloseOutlined, SearchOutlined, UpOutlined, DownOutlined } from '@ant-design/icons';

const PdfViewerModal = ({ visible, onClose, pdfUrl, title = "PDF Viewer" }) => {
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(true);
    const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
    const [error, setError] = useState(null);
    const [searchActive, setSearchActive] = useState(false);

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
            message.error('Failed to load PDF');
        }
    };

    const handleSearch = () => {
        if (!searchText.trim()) {
            message.warning('Please enter text to search');
            return;
        }

        const iframe = document.getElementById('pdf-iframe');
        if (iframe && iframe.contentWindow) {
            try {
                // Use the browser's built-in find functionality
                iframe.contentWindow.focus();
                const found = iframe.contentWindow.find(searchText, false, false, true, false, true, false);

                if (found) {
                    setSearchActive(true);
                } else {
                    message.info('No matches found');
                    setSearchActive(false);
                }
            } catch (e) {
                console.error('Search error:', e);
                // Fallback: Try using execCommand
                try {
                    iframe.contentDocument.execCommand('find', false, searchText);
                    setSearchActive(true);
                } catch (err) {
                    message.warning('Search functionality may be limited in this browser');
                }
            }
        }
    };

    const handleFindNext = () => {
        if (!searchText.trim()) return;

        const iframe = document.getElementById('pdf-iframe');
        if (iframe && iframe.contentWindow) {
            try {
                iframe.contentWindow.focus();
                iframe.contentWindow.find(searchText, false, false, true, false, true, false);
            } catch (e) {
                console.error('Find next error:', e);
            }
        }
    };

    const handleFindPrevious = () => {
        if (!searchText.trim()) return;

        const iframe = document.getElementById('pdf-iframe');
        if (iframe && iframe.contentWindow) {
            try {
                iframe.contentWindow.focus();
                // Third parameter = true means search backwards
                iframe.contentWindow.find(searchText, false, true, true, false, true, false);
            } catch (e) {
                console.error('Find previous error:', e);
            }
        }
    };

    const handleSearchKeyPress = (e) => {
        if (e.key === 'Enter') {
            if (e.shiftKey) {
                handleFindPrevious();
            } else {
                if (searchActive) {
                    handleFindNext();
                } else {
                    handleSearch();
                }
            }
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
        setSearchText('');
        setSearchActive(false);
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
                <Space>
                    <Input
                        placeholder="Search in PDF..."
                        prefix={<SearchOutlined />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        onKeyDown={handleSearchKeyPress}
                        style={{ width: 250 }}
                        allowClear
                    />
                    <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        onClick={handleSearch}
                        disabled={!searchText.trim()}
                    >
                        Find
                    </Button>
                    <Button.Group>
                        <Button
                            icon={<UpOutlined />}
                            onClick={handleFindPrevious}
                            disabled={!searchActive || !searchText.trim()}
                            title="Previous match (Shift+Enter)"
                        />
                        <Button
                            icon={<DownOutlined />}
                            onClick={handleFindNext}
                            disabled={!searchActive || !searchText.trim()}
                            title="Next match (Enter)"
                        />
                    </Button.Group>
                    <Button
                        icon={<CloseOutlined />}
                        onClick={handleModalClose}
                    >
                        Close
                    </Button>
                </Space>
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
        </Modal>
    );
};

export default PdfViewerModal;
