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
        <Space size={[0, 4]} wrap style={{ display: 'flex', paddingBottom: '4px' }}>
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
    const [debouncedSearchText, setDebouncedSearchText] = useState("");

    const [ingestTableParams, setIngestTableParams] = useState({
        pagination: { current: 1, pageSize: 10, total: 0 },
        sortField: null,
        sortOrder: null,
        filters: null,
    });

    const [compareTableParams, setCompareTableParams] = useState({
        pagination: { current: 1, pageSize: 10, total: 0 },
        sortField: null,
        sortOrder: null,
        filters: null,
    });

    // Debounce search text
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearchText(searchText);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchText]);

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
            const params = {
                page: ingestTableParams.pagination.current,
                pageSize: ingestTableParams.pagination.pageSize,
                search: debouncedSearchText,
                sortField: ingestTableParams.sortField,
                sortOrder: ingestTableParams.sortOrder,
                filters: ingestTableParams.filters ? JSON.stringify(ingestTableParams.filters) : undefined
            };
            const response = await historyAPI.getIngestHistory(params);
            setIngestHistory(response.data.items || []);
            setIngestTableParams(prev => ({
                ...prev,
                pagination: { ...prev.pagination, total: response.data.total }
            }));
        } catch (error) {
            console.error("Failed to fetch ingest history:", error);
        } finally {
            setLoading(false);
        }
    }, [ingestTableParams.pagination.current, ingestTableParams.pagination.pageSize, ingestTableParams.sortField, ingestTableParams.sortOrder, ingestTableParams.filters, debouncedSearchText]);

    const fetchCompareHistory = React.useCallback(async () => {
        try {
            setLoading(true);
            const params = {
                page: compareTableParams.pagination.current,
                pageSize: compareTableParams.pagination.pageSize,
                search: debouncedSearchText,
                sortField: compareTableParams.sortField,
                sortOrder: compareTableParams.sortOrder,
                filters: compareTableParams.filters ? JSON.stringify(compareTableParams.filters) : undefined
            };
            const response = await historyAPI.getCompareHistory(params);
            setCompareHistory(response.data.items || []);
            setCompareTableParams(prev => ({
                ...prev,
                pagination: { ...prev.pagination, total: response.data.total }
            }));
        } catch (error) {
            console.error("Failed to fetch compare history:", error);
        } finally {
            setLoading(false);
        }
    }, [compareTableParams.pagination.current, compareTableParams.pagination.pageSize, compareTableParams.sortField, compareTableParams.sortOrder, compareTableParams.filters, debouncedSearchText]);

    const handleIngestTableChange = (pagination, filters, sorter) => {
        setIngestTableParams({
            pagination,
            filters,
            sortField: sorter.field,
            sortOrder: sorter.order,
        });
    };

    const handleCompareTableChange = (pagination, filters, sorter) => {
        setCompareTableParams({
            pagination,
            filters,
            sortField: sorter.field,
            sortOrder: sorter.order,
        });
    };

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
        const isComparison = record.uploadedFile1 !== undefined;

        if (!isComparison) {
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
            align: "center",
            render: (text) => {
                if (!text) return " - ";
                // Strip type suffix (e.g., "1_fulldoc" -> "1")
                return text.split('_')[0];
            },
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
            key: "actions",
            width: 120,
            fixed: 'right',
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="View Details">
                        <Button
                            type="text"
                            icon={<EyeOutlined style={{ fontSize: '18px', color: '#000000d9' }} />}
                            onClick={() => handleView(record)}
                            className="action-btn-new view-btn"
                        />
                    </Tooltip>
                    <Tooltip title="Delete Record">
                        <Button
                            type="text"
                            icon={<DeleteOutlined style={{ fontSize: '18px', color: '#ff4d4f' }} />}
                            onClick={() => handleDelete(record)}
                            className="action-btn-new delete-btn"
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ], [renderFileNames, handleView, handleDelete]);
    const compareColumns = React.useMemo(() => [
        {
            title: "S.no",
            key: "index",
            width: 80,
            render: (text, record, index) => {
                const { current, pageSize } = compareTableParams.pagination;
                return (current - 1) * pageSize + index + 1;
            },
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
            align: "center",
            render: (text) => {
                if (!text) return " - ";
                // Strip type suffix (e.g., "1_fulldoc" -> "1")
                return text.split('_')[0];
            },
        },
        {
            title: "File 1",
            dataIndex: "uploadedFile1",
            key: "uploadedFile1",
            render: renderFileNames,
        },
        {
            title: "File 2",
            dataIndex: "uploadedFile2",
            key: "uploadedFile2",
            render: renderFileNames,
        },
        {
            title: "Date",
            dataIndex: "created_at",
            key: "created_at",
            width: 200,
            render: (date) => {
                if (!date) return "-";
                return new Date(date).toLocaleString('en-GB', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            },
        },
        {
            title: "Action",
            key: "actions",
            width: 120,
            fixed: 'right',
            render: (_, record) => (
                <Space size="middle">
                    <Tooltip title="View Details">
                        <Button
                            type="text"
                            icon={<EyeOutlined style={{ fontSize: '18px', color: '#000000d9' }} />}
                            onClick={() => handleView(record)}
                            className="action-btn-new view-btn"
                        />
                    </Tooltip>
                    <Tooltip title="Delete Record">
                        <Button
                            type="text"
                            icon={<DeleteOutlined style={{ fontSize: '18px', color: '#ff4d4f' }} />}
                            onClick={() => handleDelete(record)}
                            className="action-btn-new delete-btn"
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ], [handleView, handleDelete, compareTableParams.pagination]);

    // Also update ingestColumns S.no for pagination
    const ingestColumnsFixed = React.useMemo(() => [
        {
            title: "S.no",
            key: "index",
            width: 80,
            render: (text, record, index) => {
                const { current, pageSize } = ingestTableParams.pagination;
                return (current - 1) * pageSize + index + 1;
            },
        },
        ...ingestColumns.slice(1)
    ], [ingestColumns, ingestTableParams.pagination]);

    const ingestDataSource = ingestHistory;
    const compareDataSource = compareHistory;

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
                width: 150,
            },
            {
                title: "Category",
                dataIndex: "category",
                key: "category",
                width: 180,
            },
            {
                title: "Sub Category",
                dataIndex: "sub_category",
                key: "sub_category",
                width: 180,
            },
            {
                title: previewRecord?.uploadedFile1 ? previewRecord.uploadedFile1.replace(/\.xlsx?$/, '') : "Guideline 1",
                dataIndex: "guideline_1",
                key: "guideline_1",
                width: 400,
            },
            {
                title: previewRecord?.uploadedFile2 ? previewRecord.uploadedFile2.replace(/\.xlsx?$/, '') : "Guideline 2",
                dataIndex: "guideline_2",
                key: "guideline_2",
                width: 400,
            },
            {
                title: "Comparison Notes",
                dataIndex: "comparison_notes",
                key: "comparison_notes",
                width: 250,
            },
        ];
    }, [activeTab, previewData, previewRecord]);

    if (loading && ingestHistory.length === 0 && compareHistory.length === 0) {
        return <DashboardSkeleton />;
    }

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
                                    columns={ingestColumnsFixed}
                                    dataSource={ingestDataSource}
                                    rowKey="id"
                                    pagination={{
                                        ...ingestTableParams.pagination,
                                        showSizeChanger: true,
                                        showTotal: (total) => `Total ${total} records`,
                                    }}
                                    onChange={handleIngestTableChange}
                                    scroll={{ x: 'max-content', y: 'calc(100vh - 360px)' }}
                                    className="history-table responsive-table"
                                    loading={loading}
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
                                    dataSource={compareDataSource}
                                    rowKey="id"
                                    pagination={{
                                        ...compareTableParams.pagination,
                                        showSizeChanger: true,
                                        showTotal: (total) => `Total ${total} records`,
                                    }}
                                    onChange={handleCompareTableChange}
                                    scroll={{ x: 'max-content', y: 'calc(100vh - 360px)' }}
                                    className="history-table responsive-table"
                                    loading={loading}
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
                    investor={previewRecord?.investor || ""}
                    version={previewRecord?.version || ""}
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
