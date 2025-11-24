import React, { useState, useEffect } from "react";
import { Table, Button, Space, Tabs, message, Modal } from "antd";
import { EyeOutlined, DeleteOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import ExcelPreviewModal from "../../components/ExcelPreviewModal";

const { TabPane } = Tabs;
const { confirm } = Modal;

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
            const response = await fetch("http://localhost:8003/history/ingest", {
                headers: {
                    "Authorization": `Bearer ${sessionStorage.getItem("access_token")}`
                }
            });
            if (!response.ok) throw new Error("Failed to fetch history");
            const data = await response.json();
            setIngestHistory(data);
        } catch (error) {
            console.error("Failed to fetch ingest history:", error);
            message.error("Failed to load ingest history");
        } finally {
            setLoading(false);
        }
    };

    const fetchCompareHistory = async () => {
        try {
            setLoading(true);
            const response = await fetch("http://localhost:8003/history/compare", {
                headers: {
                    "Authorization": `Bearer ${sessionStorage.getItem("access_token")}`
                }
            });
            if (!response.ok) throw new Error("Failed to fetch history");
            const data = await response.json();
            setCompareHistory(data);
        } catch (error) {
            console.error("Failed to fetch compare history:", error);
            message.error("Failed to load compare history");
        } finally {
            setLoading(false);
        }
    };

    const handleView = (record) => {
        console.log("View record:", record);
        if (!record.preview_data || record.preview_data.length === 0) {
            message.warning("No preview data available for this record");
            return;
        }

        // Set title based on record type
        if (activeTab === "ingest") {
            setPreviewTitle(`${record.investor} - ${record.version}`);
        } else {
            setPreviewTitle(`${record.uploadedFile1} vs ${record.uploadedFile2}`);
        }

        setPreviewData(record.preview_data);
        setPreviewVisible(true);
    };

    const handleDelete = (record) => {
        const isIngest = activeTab === "ingest";
        const endpoint = isIngest ? "ingest" : "compare";
        const fileName = isIngest ? record.uploadedFile : record.uploadedFile1;

        confirm({
            title: "Are you sure you want to delete this record?",
            icon: <ExclamationCircleOutlined />,
            content: `This will permanently delete ${fileName}`,
            okText: "Yes, Delete",
            okType: "danger",
            cancelText: "Cancel",
            onOk: async () => {
                try {
                    const response = await fetch(`http://localhost:8003/history/${endpoint}/${record.id}`, {
                        method: "DELETE",
                        headers: {
                            "Authorization": `Bearer ${sessionStorage.getItem("access_token")}`
                        }
                    });
                    if (!response.ok) throw new Error("Failed to delete");
                    message.success("Record deleted successfully");

                    // Refresh appropriate list
                    if (isIngest) {
                        fetchIngestHistory();
                    } else {
                        fetchCompareHistory();
                    }
                } catch (error) {
                    console.error("Failed to delete record:", error);
                    message.error("Failed to delete record");
                }
            }
        });
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
            title: "Attribute",
            dataIndex: "attribute",
            key: "attribute",
            width: "25%",
        },
        {
            title: "Guideline Summary",
            dataIndex: "guideline_summary",
            key: "guideline_summary",
            width: "55%",
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
            title: "Attribute",
            dataIndex: "attribute",
            key: "attribute",
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
            />
        </div>
    );
};

export default DashboardPage;
