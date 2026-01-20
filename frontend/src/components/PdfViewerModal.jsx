import React, { useState, useEffect } from 'react';
import { Modal, Button, Tabs, Spin } from 'antd';
import { CloseOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import { showToast } from "../utils/toast";
import { API_BASE_URL } from "../services/api";

const PdfViewerModal = ({ visible, onClose, sessionId, title = "PDF Viewer", initialPage = null, initialFileIndex = 0 }) => {
    const [loading, setLoading] = useState(true);
    const [pdfFiles, setPdfFiles] = useState([]);
    const [loadedPdfs, setLoadedPdfs] = useState({}); // Cache loaded PDFs by file_index
    const [activeTab, setActiveTab] = useState("0");
    const [error, setError] = useState(null);
    const [targetPage, setTargetPage] = useState(initialPage);
    const [currentPage, setCurrentPage] = useState(0); // Pagination: which set of 4 tabs to show
    const TABS_PER_PAGE = 4;

    useEffect(() => {
        if (visible && sessionId) {
            setTargetPage(initialPage);
            setActiveTab(String(initialFileIndex));
            // Calculate which page the initial file index is on
            setCurrentPage(Math.floor(initialFileIndex / TABS_PER_PAGE));
            fetchPdfList();
        }

        // Cleanup blob URLs when modal closes
        return () => {
            Object.values(loadedPdfs).forEach(blobUrl => {
                if (blobUrl) {
                    URL.revokeObjectURL(blobUrl);
                }
            });
        };
    }, [visible, sessionId, initialPage, initialFileIndex]);

    const fetchPdfList = async () => {
        setLoading(true);
        setError(null);

        try {
            // Check sessionStorage first, then localStorage (matching AuthContext pattern)
            let token = sessionStorage.getItem('access_token');
            if (!token) {
                token = localStorage.getItem('access_token');
            }

            if (!token) {
                throw new Error('No authentication token found. Please login again.');
            }

            const response = await fetch(`${API_BASE_URL}/history/ingest/${sessionId}/pdfs`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to load PDF list: ${response.statusText}`);
            }

            const data = await response.json();
            setPdfFiles(data.pdf_files || []);

            // Load the first PDF (or the one specified by initialFileIndex)
            if (data.pdf_files && data.pdf_files.length > 0) {
                await fetchPdfByIndex(initialFileIndex, token);
            }

            setLoading(false);
        } catch (err) {
            console.error('Error loading PDF list:', err);
            setError(err.message);
            setLoading(false);
            showToast.error('Failed to load PDF list');
        }
    };

    const fetchPdfByIndex = async (fileIndex, token = null) => {
        // Check if already loaded
        if (loadedPdfs[fileIndex]) {
            return;
        }

        setLoading(true);
        setError(null);

        try {
            // Get token if not provided
            if (!token) {
                token = sessionStorage.getItem('access_token');
                if (!token) {
                    token = localStorage.getItem('access_token');
                }
            }

            if (!token) {
                throw new Error('No authentication token found. Please login again.');
            }

            const response = await fetch(
                `${API_BASE_URL}/history/ingest/${sessionId}/pdf?file_index=${fileIndex}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`Failed to load PDF: ${response.statusText}`);
            }

            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);

            setLoadedPdfs(prev => ({
                ...prev,
                [fileIndex]: blobUrl
            }));

            setLoading(false);
        } catch (err) {
            console.error('Error loading PDF:', err);
            setError(err.message);
            setLoading(false);
            showToast.error('Failed to load PDF');
        }
    };

    const handleTabChange = (key) => {
        setActiveTab(key);
        const fileIndex = parseInt(key);

        // Load PDF if not already loaded
        if (!loadedPdfs[fileIndex]) {
            fetchPdfByIndex(fileIndex);
        }
    };

    const handleModalClose = () => {
        // Revoke all blob URLs to free memory
        Object.values(loadedPdfs).forEach(blobUrl => {
            if (blobUrl) {
                URL.revokeObjectURL(blobUrl);
            }
        });
        setLoadedPdfs({});
        setPdfFiles([]);
        setLoading(true);
        setError(null);
        setCurrentPage(0);
        onClose();
    };

    // Calculate pagination
    const totalPages = Math.ceil(pdfFiles.length / TABS_PER_PAGE);
    const startIndex = currentPage * TABS_PER_PAGE;
    const endIndex = Math.min(startIndex + TABS_PER_PAGE, pdfFiles.length);
    const visiblePdfFiles = pdfFiles.slice(startIndex, endIndex);

    const handlePrevPage = () => {
        if (currentPage > 0) {
            setCurrentPage(currentPage - 1);
            // Switch to first tab of previous page
            const newActiveIndex = (currentPage - 1) * TABS_PER_PAGE;
            setActiveTab(String(newActiveIndex));
            if (!loadedPdfs[newActiveIndex]) {
                fetchPdfByIndex(newActiveIndex);
            }
        }
    };

    const handleNextPage = () => {
        if (currentPage < totalPages - 1) {
            setCurrentPage(currentPage + 1);
            // Switch to first tab of next page
            const newActiveIndex = (currentPage + 1) * TABS_PER_PAGE;
            setActiveTab(String(newActiveIndex));
            if (!loadedPdfs[newActiveIndex]) {
                fetchPdfByIndex(newActiveIndex);
            }
        }
    };

    // Create tabs from visible PDF files
    const tabItems = visiblePdfFiles.map((pdfFile, relativeIndex) => {
        const absoluteIndex = startIndex + relativeIndex;
        return {
            key: String(absoluteIndex),
            label: (
                <div style={{ textAlign: 'center', padding: '4px 8px' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>PDF {absoluteIndex + 1}</div>
                    <div style={{
                        fontSize: '11px',
                        color: '#666',
                        wordWrap: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '1.3'
                    }}>
                        {pdfFile.filename}
                    </div>
                </div>
            ),
            children: (
                <div style={{
                    position: 'relative',
                    width: '100%',
                    height: '100%',
                    backgroundColor: '#525659',
                    overflow: 'hidden'
                }}>
                    {loading && !loadedPdfs[absoluteIndex] && (
                        <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                            <Spin size="large" tip="Loading PDF..." />
                        </div>
                    )}
                    {error && (
                        <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                            <div className="text-center">
                                <p className="text-red-500 text-lg mb-2">Failed to load PDF</p>
                                <p className="text-gray-600">{error}</p>
                                <Button type="primary" onClick={() => fetchPdfByIndex(absoluteIndex)} className="mt-4">
                                    Retry
                                </Button>
                            </div>
                        </div>
                    )}
                    {loadedPdfs[absoluteIndex] && !loading && !error && (
                        <iframe
                            id={`pdf-iframe-${absoluteIndex}`}
                            src={targetPage && activeTab === String(absoluteIndex) ? `${loadedPdfs[absoluteIndex]}#page=${targetPage}` : loadedPdfs[absoluteIndex]}
                            style={{
                                width: '100%',
                                height: '100%',
                                border: 'none',
                                display: 'block'
                            }}
                            title={`PDF Viewer ${absoluteIndex + 1}`}
                        />
                    )}
                </div>
            )
        };
    });

    return (
        <Modal
            open={visible}
            onCancel={handleModalClose}
            footer={null}
            width="90vw"
            height="90vh"
            style={{ top: 20 }}
            closable={false}
            bodyStyle={{ padding: 0, height: 'calc(95vh - 100px)', display: 'flex', flexDirection: 'column' }}
            zIndex={9999}
            maskStyle={{ backgroundColor: 'rgba(0, 0, 0, 0.65)' }}
            destroyOnClose={true}
        >
            {/* Header */}
            <div className="flex justify-between items-center px-4 py-3 border-b bg-gray-50 flex-shrink-0">
                <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-lg m-0">{title}</h3>
                    {pdfFiles.length > 0 && (
                        <span className="text-sm text-gray-500">
                            ({pdfFiles.length} {pdfFiles.length === 1 ? 'file' : 'files'})
                        </span>
                    )}
                </div>
                <Button
                    icon={<CloseOutlined />}
                    onClick={handleModalClose}
                >
                    Close
                </Button>
            </div>

            {/* Tabs with Pagination Controls */}
            {pdfFiles.length > 0 ? (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {/* Pagination Controls - Only show if more than TABS_PER_PAGE */}
                    {pdfFiles.length > TABS_PER_PAGE && (
                        <div className="flex justify-between items-center px-4 py-2 bg-gray-100 border-b">
                            <Button
                                icon={<LeftOutlined />}
                                onClick={handlePrevPage}
                                disabled={currentPage === 0}
                                size="small"
                            >
                                Previous
                            </Button>
                            <span className="text-sm text-gray-600">
                                Showing {startIndex + 1}-{endIndex} of {pdfFiles.length} PDFs
                            </span>
                            <Button
                                icon={<RightOutlined />}
                                onClick={handleNextPage}
                                disabled={currentPage === totalPages - 1}
                                size="small"
                                iconPosition="end"
                            >
                                Next
                            </Button>
                        </div>
                    )}

                    {/* Tabs */}
                    <Tabs
                        activeKey={activeTab}
                        onChange={handleTabChange}
                        items={tabItems}
                        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
                        className="pdf-viewer-tabs"
                    />
                </div>
            ) : (
                <div className="relative flex-1 bg-gray-100 overflow-hidden">
                    {loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                            <Spin size="large" tip="Loading PDFs..." />
                        </div>
                    )}
                    {error && !loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                            <div className="text-center">
                                <p className="text-red-500 text-lg mb-2">Failed to load PDFs</p>
                                <p className="text-gray-600">{error}</p>
                                <Button type="primary" onClick={fetchPdfList} className="mt-4">
                                    Retry
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </Modal>
    );
};

export default PdfViewerModal;
