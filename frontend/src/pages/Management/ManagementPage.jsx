import React, { useState, useEffect } from "react";
import { Table, Card, Tag, Typography, Select, Input, Row, Col, Statistic } from "antd";
import { SearchOutlined, UserOutlined, TeamOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { authAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import dayjs from "dayjs";
import { TableSkeleton } from "../../components/common/SkeletonLoader";

const { Title } = Typography;

const ManagementPage = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchText, setSearchText] = useState("");

    const userStr = sessionStorage.getItem("user") || localStorage.getItem("user");
    const currentUser = userStr ? JSON.parse(userStr) : null;
    const isSuperAdmin = currentUser?.email === "admin@admin.com";

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

    const handleRoleChange = async (userId, newRole) => {
        try {
            await authAPI.updateUserRole(userId, { role: newRole });
            showToast.success("User role updated successfully");
            // Optimistically update the local state to avoid a full fetch
            setUsers(users.map(user =>
                user.id === userId ? { ...user, role: newRole } : user
            ));
        } catch (error) {
            console.error("Failed to update user role:", error);
            const errorMessage = error.response?.data?.detail || "Failed to update user role";
            showToast.error(errorMessage);
        }
    };

    const columns = [
        {
            title: "S.No",
            key: "index",
            width: 80,
            render: (text, record, index) => <span className="text-gray-500 font-medium">{index + 1}</span>,
        },
        {
            title: "Username",
            dataIndex: "username",
            key: "username",
            render: (text) => (
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs uppercase border border-blue-100">
                        {text.charAt(0)}
                    </div>
                    <span className="font-semibold text-gray-800">{text}</span>
                </div>
            ),
        },
        {
            title: "Email",
            dataIndex: "email",
            key: "email",
            render: (text) => <span className="text-gray-600">{text}</span>,
        },
        {
            title: "Role",
            dataIndex: "role",
            key: "role",
            render: (role, record) => (
                isSuperAdmin ? (
                    <Select
                        value={role || "user"}
                        style={{ width: 130 }}
                        bordered={false}
                        className="bg-gray-50 rounded-lg admin-role-select"
                        onChange={(value) => handleRoleChange(record.id, value)}
                        onClick={(e) => e.stopPropagation()}
                        options={[
                            { value: 'admin', label: <span className="font-medium text-emerald-600">ADMIN</span> },
                            { value: 'user', label: <span className="font-medium text-blue-600">USER</span> }
                        ]}
                    />
                ) : (
                    <Tag className={`px-3 py-1 rounded-full font-medium uppercase text-xs border-transparent ${role === 'admin' ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue-600'}`}>
                        {role || "user"}
                    </Tag>
                )
            ),
        },
        {
            title: "Registered On",
            dataIndex: "created_at",
            key: "created_at",
            render: (date) => (
                <span className="text-gray-500 text-sm">
                    {date ? dayjs(date).format("MMM D, YYYY h:mm A") : "N/A"}
                </span>
            ),
        },
    ];

    const filteredUsers = users.filter(u =>
        u.username.toLowerCase().includes(searchText.toLowerCase()) ||
        u.email.toLowerCase().includes(searchText.toLowerCase())
    );

    const totalUsers = users.length;
    const adminCount = users.filter(u => u.role === 'admin').length;
    const userCount = totalUsers - adminCount;

    return (
        <div className="max-w-7xl mx-auto pb-10">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8">
                <div>
                    <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600/10 text-blue-600 mb-3">
                        <TeamOutlined className="text-xl" />
                    </div>
                    <Title level={2} className="!mb-1 tracking-tight">User Management</Title>
                    <p className="text-gray-500 text-base">View, manage, and assign roles to registered users.</p>
                </div>
            </div>

            {/* Stats Overview */}
            <Row gutter={[24, 24]} className="mb-8">
                <Col xs={24} sm={8}>
                    <Card className="shadow-sm border-gray-100 rounded-2xl hover:shadow-md transition-shadow h-full">
                        <Statistic
                            title={<span className="text-gray-500 font-medium flex items-center gap-2"><TeamOutlined /> Total Users</span>}
                            value={totalUsers}
                            valueStyle={{ color: '#1e293b', fontWeight: 600, fontSize: '28px' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card className="shadow-sm border-gray-100 rounded-2xl hover:shadow-md transition-shadow h-full">
                        <Statistic
                            title={<span className="text-emerald-500 font-medium flex items-center gap-2"><SafetyCertificateOutlined /> Admins</span>}
                            value={adminCount}
                            valueStyle={{ color: '#10b981', fontWeight: 600, fontSize: '28px' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card className="shadow-sm border-gray-100 rounded-2xl hover:shadow-md transition-shadow h-full">
                        <Statistic
                            title={<span className="text-blue-500 font-medium flex items-center gap-2"><UserOutlined /> Regular Users</span>}
                            value={userCount}
                            valueStyle={{ color: '#3b82f6', fontWeight: 600, fontSize: '28px' }}
                        />
                    </Card>
                </Col>
            </Row>

            {loading ? (
                <TableSkeleton rows={10} columns={5} />
            ) : (
                <Card className="shadow-sm border-gray-200 rounded-2xl overflow-hidden" bordered={false} bodyStyle={{ padding: 0 }}>
                    {/* Table Header Controls */}
                    <div className="p-5 border-b border-gray-100 bg-white flex justify-between items-center">
                        <Input
                            placeholder="Search by username or email..."
                            prefix={<SearchOutlined className="text-gray-400" />}
                            value={searchText}
                            onChange={e => setSearchText(e.target.value)}
                            className="max-w-md h-10 rounded-lg bg-gray-50 border-transparent focus:bg-white hover:bg-white transition-colors"
                            allowClear
                        />
                    </div>

                    {/* Users Table */}
                    <div className="p-6">
                        <Table
                            columns={columns}
                            dataSource={filteredUsers}
                            rowKey="id"
                            loading={loading}
                            pagination={{
                                pageSize: 10,
                                showSizeChanger: true,
                                className: "pb-2"
                            }}
                            className="custom-table"
                            rowClassName={() => "hover:bg-blue-50/30 transition-colors"}
                        />
                    </div>
                </Card>
            )}
        </div>
    );
};

export default ManagementPage;
