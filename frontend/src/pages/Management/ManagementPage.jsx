import React, { useState, useEffect } from "react";
import { Table, Card, Tag, Typography } from "antd";
import { authAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import dayjs from "dayjs";

const { Title } = Typography;

const ManagementPage = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            const response = await authAPI.getAllUsers();
            setUsers(response.data);
        } catch (error) {
            console.error("Failed to fetch users:", error);
            showToast.error("Failed to load users list");
        } finally {
            setLoading(false);
        }
    };

    const columns = [
        {
            title: "S.No",
            key: "index",
            width: 80,
            render: (text, record, index) => index + 1,
        },
        {
            title: "Username",
            dataIndex: "username",
            key: "username",
            render: (text) => <span className="font-medium">{text}</span>,
        },
        {
            title: "Email",
            dataIndex: "email",
            key: "email",
        },
        {
            title: "Role",
            dataIndex: "role",
            key: "role",
            render: (role) => (
                <Tag color={role === "admin" ? "blue" : "green"}>
                    {role ? role.toUpperCase() : "USER"}
                </Tag>
            ),
        },
        {
            title: "Registered On",
            dataIndex: "created_at",
            key: "created_at",
            render: (date) => (
                <span className="text-gray-500">
                    {date ? dayjs(date).format("MMM D, YYYY h:mm A") : "N/A"}
                </span>
            ),
        },
    ];

    return (
        <div className="max-w-6xl mx-auto">
            <div className="mb-6">
                <Title level={2}>User Management</Title>
                <p className="text-gray-500">View and manage registered users</p>
            </div>

            <Card className="shadow-sm border-gray-200" bordered={false}>
                <Table
                    columns={columns}
                    dataSource={users}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>
        </div>
    );
};

export default ManagementPage;
