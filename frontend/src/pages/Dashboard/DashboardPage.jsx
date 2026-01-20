import React, { useState, useEffect } from "react";
import { Table, Button, Space, Tabs } from "antd";
import { EyeOutlined, DeleteOutlined } from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import ExcelPreviewModal from "../../components/ExcelPreviewModal";
import ConfirmModal from "../../components/ConfirmModal";
import { historyAPI, ingestAPI, compareAPI } from "../../services/api";
import { showToast } from "../../utils/toast";

const { TabPane } = Tabs;

const DashboardPage = () => {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState("ingest");
    const [ingestHistory, setIngestHistory] = useState([]);
    const [compareHistory, setCompareHistory] = useState([]);
    const [loading, setLoading] = useState(false);

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
        console.log("View record:", record);
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
            setPreviewTitle(`${record.investor} - ${record.version}`);
        } else {
            setPreviewTitle(`${record.uploadedFile1} vs ${record.uploadedFile2}`);
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
        },
        {
            title: "Version",
            dataIndex: "version",
            key: "version",
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 120,
            render: (text) => text || "-",
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
            title: "Uploaded File Name",
            dataIndex: "uploadedFile",
            key: "uploadedFile",
        },
        {
            title: "Extracted File Name",
            dataIndex: "extractedFile",
            key: "extractedFile",
        },
        {
            title: "Action",
            key: "action",
            width: 120,
            fixed: "right",
            render: (_, record) => (
                <Space size="small">
                    <Button
                        type="text"
                        icon={<EyeOutlined />}
                        onClick={() => handleView(record)}
                    />
                    <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record)}
                    />
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
            title: "Extracted File Name",
            dataIndex: "extractedFile",
            key: "extractedFile",
        },
        {
            title: "Uploaded File Name 1",
            dataIndex: "uploadedFile1",
            key: "uploadedFile1",
        },
        {
            title: "Uploaded File Name 2",
            dataIndex: "uploadedFile2",
            key: "uploadedFile2",
        },
        {
            title: "Action",
            key: "action",
            width: 120,
            fixed: "right",
            render: (_, record) => (
                <Space size="small">
                    <Button
                        type="text"
                        icon={<EyeOutlined />}
                        onClick={() => handleView(record)}
                    />
                    <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record)}
                    />
                </Space>
            ),
        },
    ], [handleView, handleDelete]);

    // Preview modal columns - dynamic based on data type
    const previewColumns = React.useMemo(() => {
        // For Ingest tab, we return null to let ExcelPreviewModal auto-generate columns
        // This supports both legacy data (category/rule) and new RAG data (DSCR parameters)
        if (activeTab === "ingest") return null;

        // For Compare tab, we keep the specific columns
        return [
            {
                title: "Rule ID",
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
                title: "Guideline 1",
                dataIndex: "guideline_1",
                key: "guideline_1",
                width: "25%",
            },
            {
                title: "Guideline 2",
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
    }, [activeTab]);

    return (
        <div className="px-6">
            <div className="flex justify-between items-center mb-4">
                {/* <div className="mb-2">
                    <h1 className="text-2xl font-semibold text-gray-800">Dashboard</h1>
                    <p className="text-gray-500 mt-1">View and manage your processing history</p>
                </div> */}
                <div className="flex-1"></div>
                <Button
                    danger
                    icon={<DeleteOutlined />}
                    onClick={handleDeleteAll}
                    disabled={activeTab === "ingest" ? ingestHistory.length === 0 : compareHistory.length === 0}
                >
                    Delete All
                </Button>
            </div>

            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                className="dashboard-tabs"
            >
                <TabPane tab="Ingest Guidelines" key="ingest">
                    <div className="bg-white rounded-lg shadow-sm p-6">
                        <Table
                            columns={ingestColumns}
                            dataSource={ingestHistory}
                            loading={loading}
                            rowKey="id"
                            bordered
                            scroll={{ x: "max-content" }}
                            pagination={{
                                pageSize: 10,
                                showSizeChanger: true,
                                showTotal: (total) => `Total ${total} records`,
                            }}
                            locale={{
                                emptyText: loading ? "Loading..." : "No ingest history found"
                            }}
                        />
                    </div>
                </TabPane>

                <TabPane tab="Compare Guidelines" key="compare">
                    <div className="bg-white rounded-lg shadow-sm p-6">
                        <Table
                            columns={compareColumns}
                            dataSource={compareHistory}
                            loading={loading}
                            rowKey="id"
                            bordered
                            scroll={{ x: "max-content" }}
                            pagination={{
                                pageSize: 10,
                                showSizeChanger: true,
                                showTotal: (total) => `Total ${total} records`,
                            }}
                            locale={{
                                emptyText: loading ? "Loading..." : "No compare history found"
                            }}
                        />
                    </div>
                </TabPane>
            </Tabs>

            {/* Preview Modal */}
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
