import React, { useState } from "react";
import { Table, Button, Space, Tabs } from "antd";
import { EyeOutlined, DeleteOutlined } from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";

const { TabPane } = Tabs;

const DashboardPage = () => {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState("ingest");

    // Mock data - replace with API calls when backend is ready
    const ingestHistory = [
        {
            id: "1",
            investor: "Michael Brown",
            version: "V 12.01",
            uploadedFile: "File Name.pdf",
            extractedFile: "File Name.pdf",
        },
        {
            id: "2",
            investor: "Michael Brown",
            version: "V 12.01",
            uploadedFile: "File Name.pdf",
            extractedFile: "File Name.pdf",
        },
    ];

    const compareHistory = [
        {
            id: "1",
            extractedFile: "File Name.pdf",
            uploadedFile1: "File Name.pdf",
            uploadedFile2: "File Name.pdf",
        },
        {
            id: "2",
            extractedFile: "File Name.pdf",
            uploadedFile1: "File Name.pdf",
            uploadedFile2: "File Name.pdf",
        },
    ];

    const handleView = (record) => {
        console.log("View record:", record);
        // TODO: Implement view functionality
    };

    const handleDelete = (record) => {
        console.log("Delete record:", record);
        // TODO: Implement delete functionality
    };

    // Ingest Guidelines Table Columns
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
            title: "Actions",
            key: "actions",
            width: 120,
            render: (_, record) => (
                <Space size="middle">
                    <Button
                        type="text"
                        icon={<EyeOutlined />}
                        onClick={() => handleView(record)}
                        className="text-gray-600 hover:text-blue-500"
                    />
                    <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record)}
                        className="hover:text-red-500"
                    />
                </Space>
            ),
        },
    ];

    // Compare Guidelines Table Columns
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
            title: "Actions",
            key: "actions",
            width: 120,
            render: (_, record) => (
                <Space size="middle">
                    <Button
                        type="text"
                        icon={<EyeOutlined />}
                        onClick={() => handleView(record)}
                        className="text-gray-600 hover:text-blue-500"
                    />
                    <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record)}
                        className="hover:text-red-500"
                    />
                </Space>
            ),
        },
    ];

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-semibold text-gray-800 mb-2">
                    Welcome back, {user?.username || "User"}
                </h1>
                <p className="text-gray-500">View and manage your processing history</p>
            </div>

            {/* Tabs with Tables */}
            <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <Tabs
                    activeKey={activeTab}
                    onChange={setActiveTab}
                    className="dashboard-tabs"
                    tabBarStyle={{
                        padding: "0 24px",
                        margin: 0,
                        borderBottom: "1px solid #f0f0f0",
                    }}
                    tabBarExtraContent={
                        <div className="flex gap-2 mr-4">
                            <Button
                                type={activeTab === "ingest" ? "primary" : "default"}
                                onClick={() => setActiveTab("ingest")}
                                className="rounded-md"
                            >
                                Ingest Guidelines
                            </Button>
                            <Button
                                type={activeTab === "compare" ? "primary" : "default"}
                                onClick={() => setActiveTab("compare")}
                                className="rounded-md"
                            >
                                Compare Guidelines
                            </Button>
                        </div>
                    }
                >
                    <TabPane tab="" key="ingest">
                        <div className="p-6">
                            <Table
                                columns={ingestColumns}
                                dataSource={ingestHistory}
                                rowKey="id"
                                pagination={{
                                    pageSize: 10,
                                    showSizeChanger: true,
                                    showTotal: (total) => `Total ${total} items`,
                                }}
                                className="dashboard-table"
                            />
                        </div>
                    </TabPane>
                    <TabPane tab="" key="compare">
                        <div className="p-6">
                            <Table
                                columns={compareColumns}
                                dataSource={compareHistory}
                                rowKey="id"
                                pagination={{
                                    pageSize: 10,
                                    showSizeChanger: true,
                                    showTotal: (total) => `Total ${total} items`,
                                }}
                                className="dashboard-table"
                            />
                        </div>
                    </TabPane>
                </Tabs>
            </div>
        </div>
    );
};

export default DashboardPage;
