import React, { useState, useEffect } from 'react';
import { Modal, Button, Spin, Select } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { showToast } from "../utils/toast";
import api, { API_BASE_URL } from "../services/api";
const PdfViewerModal = ({ visible, onClose, sessionId, title = "PDF Viewer", initialPage = null, initialFileIndex = 0 }) => {
    const [loading, setLoading] = useState(true);
    const [pdfFiles, setPdfFiles] = useState([]);
    const [loadedPdfs, setLoadedPdfs] = useState({}); // Cache loaded PDFs by file_index
    const [activeTab, setActiveTab] = useState(String(initialFileIndex));
    const [error, setError] = useState(null);
    const [targetPage, setTargetPage] = useState(initialPage);

    useEffect(() => {
        if (visible && sessionId) {
            setTargetPage(initialPage);
            setActiveTab(String(initialFileIndex));
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
            const response = await api.get(`/history/ingest/${sessionId}/pdfs`);
            const data = response.data;
            setPdfFiles(data.pdf_files || []);

            // Load the first PDF (or the one specified by initialFileIndex)
            if (data.pdf_files && data.pdf_files.length > 0) {
                await fetchPdfByIndex(initialFileIndex);
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
            const response = await api.get(`/history/ingest/${sessionId}/pdf?file_index=${fileIndex}`, {
                responseType: 'blob'
            });

            const blobUrl = URL.createObjectURL(response.data);

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
        onClose();
    };

    const activeFileIndex = parseInt(activeTab);
    const activePdfFile = pdfFiles[activeFileIndex];

    return (
        <Modal
            open={visible}
            onCancel={handleModalClose}
            footer={null}
            width="98vw"
            centered
            style={{ maxWidth: '100vw', margin: 0, padding: 0, top: 10 }}
            closable={false}
            bodyStyle={{ padding: 0, height: '96vh', display: 'flex', flexDirection: 'column' }}
            zIndex={9999}
            maskStyle={{ backgroundColor: 'rgba(0, 0, 0, 0.65)' }}
            destroyOnClose={true}
        >
            {/* Header */}
            <div 
                className="flex justify-between items-center px-5 py-3 border-b bg-surface text-text-primary flex-shrink-0" 
                style={{ minHeight: '56px', borderColor: 'var(--color-border)' }}
            >
                {/* Left: Title & Count */}
                <div className="flex items-center gap-3 w-1/3">
                    <h3 className="font-semibold text-lg m-0 text-text-primary">{title}</h3>
                    {pdfFiles.length > 0 && (
                        <span className="text-sm text-text-secondary whitespace-nowrap">
                            ({pdfFiles.length} {pdfFiles.length === 1 ? 'file' : 'files'})
                        </span>
                    )}
                </div>

                {/* Center: Dropdown */}
                <div className="flex justify-center w-1/3">
                    {pdfFiles.length > 1 && (
                        <div className="flex items-center gap-2 w-full max-w-md">
                            <span className="font-medium text-text-secondary whitespace-nowrap">Select PDF:</span>
                            <Select
                                value={activeTab}
                                onChange={handleTabChange}
                                style={{ width: '100%' }}
                                options={pdfFiles.map((file, i) => ({
                                    value: String(i),
                                    label: `PDF ${i + 1} - ${file.filename}`
                                }))}
                                showSearch
                                optionFilterProp="label"
                            />
                        </div>
                    )}
                </div>

                {/* Right: Close Button */}
                <div className="flex justify-end w-1/3">
                    <Button
                        icon={<CloseOutlined />}
                        onClick={handleModalClose}
                    >
                        Close
                    </Button>
                </div>
            </div>

            {/* Content Area */}
            {pdfFiles.length > 0 ? (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <div style={{ flex: 1, position: 'relative', backgroundColor: '#525659' }}>
                        {pdfFiles.map((pdfFile, idx) => {
                            const isSelected = activeFileIndex === idx;
                            const hasLoadedData = !!loadedPdfs[idx];

                            if (!isSelected && !hasLoadedData) {
                                return null;
                            }

                            return (
                                <div
                                    key={`pdf-container-${idx}`}
                                    style={{
                                        position: 'absolute',
                                        inset: 0,
                                        display: isSelected ? 'block' : 'none',
                                    }}
                                >
                                    {loading && !hasLoadedData && isSelected && (
                                        <div className="absolute inset-0 flex items-center justify-center bg-base z-10">
                                            <Spin size="large" tip="Loading PDF..." />
                                        </div>
                                    )}
                                    {error && isSelected && (
                                        <div className="absolute inset-0 flex items-center justify-center bg-base z-10">
                                            <div className="text-center">
                                                <p className="text-red-500 text-lg mb-2">Failed to load PDF</p>
                                                <p className="text-text-secondary">{error}</p>
                                                <Button type="primary" onClick={() => fetchPdfByIndex(idx)} className="mt-4">
                                                    Retry
                                                </Button>
                                            </div>
                                        </div>
                                    )}
                                    {hasLoadedData && (
                                        <iframe
                                            id={`pdf-iframe-${idx}`}
                                            src={targetPage && isSelected ? `${loadedPdfs[idx]}#page=${targetPage}` : loadedPdfs[idx]}
                                            style={{
                                                width: '100%',
                                                height: '100%',
                                                border: 'none',
                                                display: 'block'
                                            }}
                                            title={`PDF Viewer ${idx + 1}`}
                                        />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            ) : (
                <div className="relative flex-1 bg-base overflow-hidden">
                    {loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-base z-10">
                            <Spin size="large" tip="Loading PDFs..." />
                        </div>
                    )}
                    {error && !loading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-base z-10">
                            <div className="text-center">
                                <p className="text-red-500 text-lg mb-2">Failed to load PDFs</p>
                                <p className="text-text-secondary">{error}</p>
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
