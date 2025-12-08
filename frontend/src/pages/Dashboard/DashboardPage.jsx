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
    const [recordToDelete, setRecordToDelete] = useState(null);
    const [deleteLoading, setDeleteLoading] = useState(false);



    useEffect(() => {
        if (activeTab === "ingest") {
            fetchIngestHistory();
        } else {
            fetchCompareHistory();
        }
    }, [activeTab]);

    const fetchIngestHistory = async () => {
        try {
            setLoading(true);
            const response = await historyAPI.getIngestHistory();
            setIngestHistory(response.data);
        } catch (error) {
            console.error("Failed to fetch ingest history:", error);
            showToast.error("Failed to load ingest history");
        } finally {
            setLoading(false);
        }
    };

    const fetchCompareHistory = async () => {
        try {
            setLoading(true);
            const response = await historyAPI.getCompareHistory();
            setCompareHistory(response.data);
        } catch (error) {
            console.error("Failed to fetch compare history:", error);
            showToast.error("Failed to load compare history");
        } finally {
            setLoading(false);
        }
    };

    const handleView = (record) => {
        console.log("View record:", record);
        if (!record.preview_data || record.preview_data.length === 0) {
            showToast.warning("No preview data available for this record");
            return;
        }

        // Set title based on record type
        if (activeTab === "ingest") {
            setPreviewTitle(`${record.investor} - ${record.version}`);
        } else {
            setPreviewTitle(`${record.uploadedFile1} vs ${record.uploadedFile2}`);
        }

        setPreviewData(record.preview_data);
        setPreviewRecord(record);
        setPreviewVisible(true);
    };

    const handleDownload = () => {
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
            showToast.error("Failed to start download");
        }
    };

    const handleDelete = (record) => {
        setRecordToDelete(record);
        setDeleteModalVisible(true);
    };

    const handleConfirmDelete = async () => {
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
            showToast.error("Failed to delete record");
        } finally {
            setDeleteLoading(false);
        }
    };

    const handleCancelDelete = () => {
        setDeleteModalVisible(false);
        setRecordToDelete(null);
    };

    const ingestColumns = [
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
    ];

    const compareColumns = [
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
    ];

    // Preview modal columns - dynamic based on data type
    const previewColumns = activeTab === "ingest" ? [
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            width: "20%",
        },
        {
            title: "Sub Category",
            dataIndex: "sub_category",
            key: "sub_category",
            width: "20%",
        },
        {
            title: "Guideline Summary",
            dataIndex: "guideline_summary",
            key: "guideline_summary",
            width: "50%",
        },
        {
            title: "Page Number",
            dataIndex: "page_number",
            key: "page_number",
            width: "10%",
        },
    ] : [
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

    return (
        <div className="px-8 py-6">
            {/* <div className="mb-2">
                <h1 className="text-2xl font-semibold text-gray-800">Dashboard</h1>
                <p className="text-gray-500 mt-1">View and manage your processing history</p>
            </div> */}

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


        </div>
    );
};

export default DashboardPage;
