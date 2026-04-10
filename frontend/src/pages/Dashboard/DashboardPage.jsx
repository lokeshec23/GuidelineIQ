import React, { useState, useEffect } from "react";
import { Table, Button, Space, Tabs, Modal, Spin, Tag, Input, Tooltip, Empty, Typography } from "antd";
import { EyeOutlined, DeleteOutlined, SearchOutlined, HistoryOutlined, FileTextOutlined } from "@ant-design/icons";
import "./DashboardPage.css";
import { useAuth } from "../../context/AuthContext";
const ExcelPreviewModal = React.lazy(() => import("../../components/ExcelPreviewModal"));
import ConfirmModal from "../../components/ConfirmModal";
import { historyAPI, ingestAPI, compareAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import { DashboardSkeleton } from "../../components/common/SkeletonLoader";

const { Title, Text } = Typography;

const renderFileNames = (text) => {
    if (!text) return "-";
    const files = typeof text === 'string' ? text.split(',').map(f => f.trim()).filter(Boolean) : [text];
    return (
        <Space size={[0, 4]} wrapStyle={{ flexWrap: 'wrap' }} style={{ display: 'flex', paddingBottom: '4px' }}>
            {files.map((file, idx) => (
                <Tag
                    key={idx}
                    className="file-tag"
                    color="blue"
                >
                    <FileTextOutlined style={{ marginRight: '4px' }} />
                    {file}
                </Tag>
            ))}
        </Space>
    );
};

const DashboardPage = () => {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState("ingest");
    const [ingestHistory, setIngestHistory] = useState([]);
    const [compareHistory, setCompareHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchText, setSearchText] = useState("");

    // Preview modal state
    const [previewVisible, setPreviewVisible] = useState(false);
    const [previewData, setPreviewData] = useState([]);
    const [previewTitle, setPreviewTitle] = useState("");
    const [previewRecord, setPreviewRecord] = useState(null);

    // Delete confirmation modal state
    const [deleteModalVisible, setDeleteModalVisible] = useState(false);
    const [deleteAllModalVisible, setDeleteAllModalVisible] = useState(false);
    const [recordToDelete, setRecordToDelete] = useState(null);
    const [deleteLoading, setDeleteLoading] = useState(false);



    const fetchIngestHistory = React.useCallback(async () => {
        try {
            setLoading(true);
            const response = await historyAPI.getIngestHistory();
            setIngestHistory(response.data);
        } catch (error) {
            console.error("Failed to fetch ingest history:", error);
            // Toast is handled by API interceptor
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchCompareHistory = React.useCallback(async () => {
        try {
            setLoading(true);
            const response = await historyAPI.getCompareHistory();
            setCompareHistory(response.data);
        } catch (error) {
            console.error("Failed to fetch compare history:", error);
            // Toast is handled by API interceptor
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (activeTab === "ingest") {
            fetchIngestHistory();
        } else {
            fetchCompareHistory();
        }
    }, [activeTab, fetchIngestHistory, fetchCompareHistory]);

    const handleView = React.useCallback((record) => {
        if (!record.preview_data || record.preview_data.length === 0) {
            showToast.warning("No preview data available for this record");
            return;
        }

        // Set title based on record type
        // Note: We use the *current* activeTab state here. 
        // If this handler closes over stale state, it might be an issue, but since activeTab is in dependency 
        // array (or we can derive from record structure), it should be fine.
        // Actually, safer to derive from record properties if possible, but simplicity first with correct deps.
        const isIngest = record.investor !== undefined; // Simple heuristic or rely on activeTab

        if (isIngest) {
            const investor = record.investor || " - ";
            const version = record.version || " - ";
            setPreviewTitle(`${investor} - ${version}`);
        } else {
            const file1 = record.uploadedFile1 || " - ";
            const file2 = record.uploadedFile2 || " - ";
            setPreviewTitle(`${file1} vs ${file2}`);
        }

        setPreviewData(record.preview_data);
        setPreviewRecord(record);
        setPreviewVisible(true);
    }, []);

    const handleDownload = React.useCallback(() => {
        if (!previewRecord) return;

        try {
            if (activeTab === "ingest") {
                ingestAPI.downloadExcel(previewRecord.id);
            } else {
                compareAPI.downloadExcel(previewRecord.id);
            }
            showToast.success("Download started");
        } catch (error) {
            console.error("Download failed:", error);
            // Toast is handled by API interceptor
        }
    }, [activeTab, previewRecord]);

    const handleDelete = React.useCallback((record) => {
        setRecordToDelete(record);
        setDeleteModalVisible(true);
    }, []);

    const handleConfirmDelete = React.useCallback(async () => {
        if (!recordToDelete) return;

        const isIngest = activeTab === "ingest";

        try {
            setDeleteLoading(true);

            if (isIngest) {
                await historyAPI.deleteIngestHistory(recordToDelete.id);
            } else {
                await historyAPI.deleteCompareHistory(recordToDelete.id);
            }

            showToast.success("Record deleted successfully");

            // Refresh appropriate list
            if (isIngest) {
                fetchIngestHistory();
            } else {
                fetchCompareHistory();
            }

            // Close modal
            setDeleteModalVisible(false);
            setRecordToDelete(null);
        } catch (error) {
            console.error("Failed to delete record:", error);
            // Toast is handled by API interceptor
        } finally {
            setDeleteLoading(false);
        }
    }, [recordToDelete, activeTab, fetchIngestHistory, fetchCompareHistory]);

    const handleCancelDelete = React.useCallback(() => {
        setDeleteModalVisible(false);
        setRecordToDelete(null);
    }, []);

    const handleDeleteAll = React.useCallback(() => {
        if ((activeTab === "ingest" && ingestHistory.length === 0) ||
            (activeTab === "compare" && compareHistory.length === 0)) {
            showToast.info("No records to delete");
            return;
        }
        setDeleteAllModalVisible(true);
    }, [activeTab, ingestHistory.length, compareHistory.length]);

    const handleConfirmDeleteAll = React.useCallback(async () => {
        const isIngest = activeTab === "ingest";

        try {
            setDeleteLoading(true);

            if (isIngest) {
                await historyAPI.deleteAllIngestHistory();
            } else {
                await historyAPI.deleteAllCompareHistory();
            }

            showToast.success(`All ${isIngest ? "ingest" : "compare"} history deleted successfully`);

            // Refresh appropriate list
            if (isIngest) {
                fetchIngestHistory();
            } else {
                fetchCompareHistory();
            }

            // Close modal
            setDeleteAllModalVisible(false);
        } catch (error) {
            console.error("Failed to delete all records:", error);
            // Toast is handled by API interceptor
        } finally {
            setDeleteLoading(false);
        }
    }, [activeTab, fetchIngestHistory, fetchCompareHistory]);

    const ingestColumns = React.useMemo(() => [
        {
            title: "S.no",
            key: "index",
            width: 80,
            render: (text, record, index) => index + 1,
        },
        {
            title: "Investor",
            dataIndex: "investor",
            key: "investor",
            width: 150,
            render: (text) => text || " - ",
        },
        {
            title: "Version",
            dataIndex: "version",
            key: "version",
            width: 100,
            render: (text) => text || " - ",
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 120,
            render: renderFileNames,
        },
        {
            title: "Effective Date",
            dataIndex: "effective_date",
            key: "effective_date",
            width: 130,
            render: (date) => {
                if (!date) return "-";
                try {
                    return new Date(date).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric'
                    });
                } catch {
                    return "-";
                }
            },
        },
        {
            title: "Expiry Date",
            dataIndex: "expiry_date",
            key: "expiry_date",
            width: 130,
            render: (date) => {
                if (!date) return "-";
                try {
                    return new Date(date).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric'
                    });
                } catch {
                    return "-";
                }
            },
        },
        {
            title: "Program Type",
            dataIndex: "program_type",
            key: "program_type",
            width: 120,
            render: (text) => text || "-",
        },
        {
            title: "Page Range",
            dataIndex: "page_range",
            key: "page_range",
            width: 100,
            render: (text) => text || "All",
        },
        {
            title: "Uploaded File Name",
            dataIndex: "uploadedFile",
            key: "uploadedFile",
            render: renderFileNames,
        },
        {
            title: "Extracted File Name",
            dataIndex: "extractedFile",
            key: "extractedFile",
            render: renderFileNames,
        },
        {
            title: "Action",
            key: "action",
            width: 120,
            fixed: "right",
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="View Preview">
                        <Button
                            type="text"
                            icon={<EyeOutlined />}
                            onClick={() => handleView(record)}
                            className="action-btn"
                        />
                    </Tooltip>
                    <Tooltip title="Delete Record">
                        <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDelete(record)}
                            className="action-btn delete"
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ], [handleView, handleDelete]);

    const compareColumns = React.useMemo(() => [
        {
            title: "S.no",
            key: "index",
            width: 80,
            render: (text, record, index) => index + 1,
        },
        {
            title: "Investor",
            dataIndex: "investor",
            key: "investor",
            width: 150,
            render: (text) => text || " - ",
        },
        {
            title: "Version",
            dataIndex: "version",
            key: "version",
            width: 100,
            render: (text) => text || " - ",
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 120,
            render: (text) => text ? renderFileNames(text) : " - ",
        },
        {
            title: "Effective Date",
            dataIndex: "effective_date",
            key: "effective_date",
            width: 130,
            render: (date) => {
                if (!date) return "-";
                try {
                    return new Date(date).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric'
                    });
                } catch {
                    return "-";
                }
            },
        },
        {
            title: "Expiry Date",
            dataIndex: "expiry_date",
            key: "expiry_date",
            width: 130,
            render: (date) => {
                if (!date) return "-";
                try {
                    return new Date(date).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric'
                    });
                } catch {
                    return "-";
                }
            },
        },
        {
            title: "Extracted File Name",
            dataIndex: "extractedFile",
            key: "extractedFile",
            render: renderFileNames,
        },
        {
            title: "Uploaded File Name 1",
            dataIndex: "uploadedFile1",
            key: "uploadedFile1",
            render: renderFileNames,
        },
        {
            title: "Uploaded File Name 2",
            dataIndex: "uploadedFile2",
            key: "uploadedFile2",
            render: renderFileNames,
        },
        {
            title: "Action",
            key: "action",
            width: 120,
            fixed: "right",
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="View Preview">
                        <Button
                            type="text"
                            icon={<EyeOutlined />}
                            onClick={() => handleView(record)}
                            className="action-btn"
                        />
                    </Tooltip>
                    <Tooltip title="Delete Record">
                        <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDelete(record)}
                            className="action-btn delete"
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ], [handleView, handleDelete]);

    // Preview modal columns - dynamic based on data type
    const previewColumns = React.useMemo(() => {
        // For Ingest tab, ensure we filter out internal fields
        if (activeTab === "ingest") {
            if (!previewData) return null;

            // Handle both array and object/multi-tab formats
            const isArray = Array.isArray(previewData);
            const firstTabKey = !isArray ? Object.keys(previewData)[0] : null;
            const dataForKeys = isArray ? previewData[0] : (firstTabKey ? previewData[firstTabKey][0] : null);

            if (!dataForKeys) return null;

            const allKeys = Object.keys(dataForKeys);
            const hiddenColumns = ['Classification', 'Notes', '_verification', 'key', 'PPE_Field_Type'];
            const visibleKeys = allKeys.filter(key => !hiddenColumns.includes(key));

            return visibleKeys.map(key => {
                // Rename Hard_Soft_Classification to PPE FIELD TYPE
                if (key.toLowerCase() === 'hard_soft_classification') {
                    return {
                        title: "PPE FIELD TYPE",
                        dataIndex: key,
                        key: key
                    };
                }
                return {
                    dataIndex: key,
                    key: key
                };
            });
        }

        // For Compare tab, we keep the specific columns
        return [
            {
                title: "PARAMETERS",
                dataIndex: "rule_id",
                key: "rule_id",
                width: "10%",
            },
            {
                title: "Category",
                dataIndex: "category",
                key: "category",
                width: "15%",
            },
            {
                title: "Sub Category",
                dataIndex: "sub_category",
                key: "sub_category",
                width: "15%",
            },
            {
                title: previewRecord?.uploadedFile1 ? previewRecord.uploadedFile1.replace(/\.xlsx?$/, '') : "Guideline 1",
                dataIndex: "guideline_1",
                key: "guideline_1",
                width: "25%",
            },
            {
                title: previewRecord?.uploadedFile2 ? previewRecord.uploadedFile2.replace(/\.xlsx?$/, '') : "Guideline 2",
                dataIndex: "guideline_2",
                key: "guideline_2",
                width: "25%",
            },
            {
                title: "Comparison Notes",
                dataIndex: "comparison_notes",
                key: "comparison_notes",
                width: "10%",
            },
        ];
    }, [activeTab, previewData, previewRecord]);

    if (loading && ingestHistory.length === 0 && compareHistory.length === 0) {
        return <DashboardSkeleton />;
    }

    // Filter history data based on search text
    const filteredIngestHistory = ingestHistory.filter((record) => {
        const searchLower = searchText.toLowerCase();
        return (
            record.investor?.toLowerCase().includes(searchLower) ||
            record.version?.toLowerCase().includes(searchLower) ||
            record.uploadedFile?.toLowerCase().includes(searchLower)
        );
    });

    const filteredCompareHistory = compareHistory.filter((record) => {
        const searchLower = searchText.toLowerCase();
        return (
            record.investor?.toLowerCase().includes(searchLower) ||
            record.version?.toLowerCase().includes(searchLower) ||
            record.uploadedFile1?.toLowerCase().includes(searchLower) ||
            record.uploadedFile2?.toLowerCase().includes(searchLower)
        );
    });

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <div className="dashboard-search-wrapper">
                    <Input
                        placeholder="Search by investor, version, or file name..."
                        prefix={<SearchOutlined className="text-gray-400" />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        size="large"
                        allowClear
                        className="dashboard-search-input"
                    />
                </div>

                <div className="dashboard-actions">
                    <Button
                        danger
                        size="large"
                        icon={<DeleteOutlined />}
                        onClick={handleDeleteAll}
                        disabled={activeTab === "ingest" ? ingestHistory.length === 0 : compareHistory.length === 0}
                        className="action-btn"
                    >
                        Delete All
                    </Button>
                </div>
            </header>

            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                className="dashboard-tabs-container"
                items={[
                    {
                        key: "ingest",
                        label: "Ingest Guidelines",
                        children: (
                            <div style={{
                                height: '100%',
                                display: 'flex',
                                flexDirection: 'column',
                                overflow: 'hidden'
                            }}>
                                <Table
                                    columns={ingestColumns}
                                    dataSource={filteredIngestHistory}
                                    loading={loading}
                                    rowKey="id"
                                    bordered
                                    scroll={filteredIngestHistory.length > 0 ? { x: "max-content", y: 'calc(100vh - 350px)' } : undefined}
                                    pagination={{
                                        pageSize: 10,
                                        showSizeChanger: true,
                                        showTotal: (total) => `Total ${total} records`,
                                        position: ['bottomRight']
                                    }}
                                    locale={{
                                        emptyText: loading ? (
                                            <div className="empty-container">
                                                <Spin size="large"><div style={{ padding: 30 }} /></Spin>
                                            </div>
                                        ) : (
                                            <div className="empty-container">
                                                <Empty description="No history found" />
                                            </div>
                                        )
                                    }}
                                />
                            </div>
                        ),
                    },
                    {
                        key: "compare",
                        label: "Compare Guidelines",
                        children: (
                            <div style={{
                                height: '100%',
                                display: 'flex',
                                flexDirection: 'column',
                                overflow: 'hidden'
                            }}>
                                <Table
                                    columns={compareColumns}
                                    dataSource={filteredCompareHistory}
                                    loading={loading}
                                    rowKey="id"
                                    bordered
                                    scroll={filteredCompareHistory.length > 0 ? { x: "max-content", y: 'calc(100vh - 350px)' } : undefined}
                                    pagination={{
                                        pageSize: 10,
                                        showSizeChanger: true,
                                        showTotal: (total) => `Total ${total} records`,
                                        position: ['bottomRight']
                                    }}
                                    locale={{
                                        emptyText: loading ? (
                                            <div className="empty-container">
                                                <Spin size="large"><div style={{ padding: 30 }} /></Spin>
                                            </div>
                                        ) : (
                                            <div className="empty-container">
                                                <Empty description="No history found" />
                                            </div>
                                        )
                                    }}
                                />
                            </div>
                        ),
                    },
                ]}
            />

            {/* Preview Modal */}
            <React.Suspense fallback={<Modal open={previewVisible} footer={null} closable={false} centered><div className="p-10 text-center"><Spin size="large"><div style={{ padding: 30 }} /></Spin></div></Modal>}>
                <ExcelPreviewModal
                    visible={previewVisible}
                    onClose={() => setPreviewVisible(false)}
                    title={`Preview: ${previewTitle}`}
                    data={previewData}
                    columns={previewColumns}
                    showRowCount={false}
                    pageSize={20}
                    onDownload={handleDownload}
                    sessionId={previewRecord?.id}
                    isComparisonMode={activeTab === "compare"}
                    filenames={previewRecord?.filenames || []} // ✅ Pass filenames for tabs
                />
            </React.Suspense>

            {/* Delete Confirmation Modal */}
            <ConfirmModal
                visible={deleteModalVisible}
                onConfirm={handleConfirmDelete}
                onCancel={handleCancelDelete}
                title="Delete Record"
                message={`Are you sure you want to permanently delete ${recordToDelete
                    ? activeTab === "ingest"
                        ? recordToDelete.uploadedFile
                        : recordToDelete.uploadedFile1
                    : "this record"
                    }?`}
                confirmText="Yes, Delete"
                cancelText="Cancel"
                danger={true}
                loading={deleteLoading}
            />

            {/* Delete All Confirmation Modal */}
            <ConfirmModal
                visible={deleteAllModalVisible}
                onConfirm={handleConfirmDeleteAll}
                onCancel={() => setDeleteAllModalVisible(false)}
                title="Delete All Records"
                message={`Are you sure you want to permanently delete ALL ${activeTab === "ingest" ? "ingest" : "comparison"} history? This action cannot be undone.`}
                confirmText="Yes, Delete All"
                cancelText="Cancel"
                danger={true}
                loading={deleteLoading}
            />


        </div>
    );
};

export default DashboardPage;
