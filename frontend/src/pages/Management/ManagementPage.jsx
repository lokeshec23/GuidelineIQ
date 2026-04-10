import React, { useState, useEffect, useDeferredValue, memo, useMemo } from "react";
import { Table, Card, Tag, Typography, Select, Input, Row, Col, Statistic } from "antd";
import { SearchOutlined, UserOutlined, TeamOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { authAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import dayjs from "dayjs";
import { TableSkeleton } from "../../components/common/SkeletonLoader";

const { Title } = Typography;

const ManagementPage = () => {
    const [users, setUsers] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [searchText, setSearchText] = useState("");
    const [debouncedSearchText, setDebouncedSearchText] = useState("");
    const [tableParams, setTableParams] = useState({
        pagination: {
            current: 1,
            pageSize: 12,
        },
    });

    // Debounce search text
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearchText(searchText);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchText]);

    const userStr = sessionStorage.getItem("user") || localStorage.getItem("user");
    const currentUser = userStr ? JSON.parse(userStr) : null;
    const isSuperAdmin = currentUser?.email === "admin@admin.com";

    useEffect(() => {
        fetchUsers();
    }, [tableParams.pagination.current, tableParams.pagination.pageSize, debouncedSearchText]);

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const params = {
                page: tableParams.pagination.current,
                pageSize: tableParams.pagination.pageSize,
                search: debouncedSearchText,
            };
            const response = await authAPI.getAllUsers(params);
            setUsers(response.data.items || []);
            setTotal(response.data.total || 0);
        } catch (error) {
            console.error("Failed to fetch users:", error);
            showToast.error("Failed to load users list");
        } finally {
            setLoading(false);
        }
    };

    const handleTableChange = (pagination) => {
        setTableParams({ pagination });
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

    const columnsMemo = useMemo(() => [
        {
            title: "S.No",
            key: "index",
            width: 80,
            render: (text, record, index) => {
                const { current, pageSize } = tableParams.pagination;
                return <span className="text-gray-500 font-medium">{(current - 1) * pageSize + index + 1}</span>;
            },
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
    ], [isSuperAdmin, users]);

    const totalUsers = total;
    // Note: adminCount and userCount will now represent current page counts unless we return global counts from API.
    // For now, let's keep them as global if the API returns them, or just use current page.
    // Given the current API response only has items and total, we'll just show current page counts or skip them.
    const adminCount = users.filter(u => u.role === 'admin').length;
    const userCount = users.length - adminCount;

    return (
        <div className="max-w-7xl mx-auto pb-10">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8">
                <div>
                    {/* <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600/10 text-blue-600 mb-3">
                        <TeamOutlined className="text-xl" />
                    </div> */}
                    {/* <Title level={2} className="!mb-1 tracking-tight">User Management</Title> */}
                    {/* <p className="text-gray-500 text-base">View, manage, and assign roles to registered users.</p> */}
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
                        <SearchInput onSearch={setSearchText} />
                    </div>

                    {/* Users Table */}
                    <div className="p-6">
                        <OptimizedTable
                            columns={columnsMemo}
                            dataSource={users}
                            loading={loading}
                            total={total}
                            current={tableParams.pagination.current}
                            pageSize={tableParams.pagination.pageSize}
                            onChange={handleTableChange}
                        />
                    </div>
                </Card>
            )}
        </div>
    );
};

// Sub-component to isolate search state and prevent re-rendering the whole page on every keystroke
const SearchInput = memo(({ onSearch }) => {
    const [innerValue, setInnerValue] = useState("");

    const handleChange = (e) => {
        const val = e.target.value;
        setInnerValue(val);
        onSearch(val);
    };

    return (
        <Input
            placeholder="Search by username or email..."
            prefix={<SearchOutlined className="text-gray-400" />}
            value={innerValue}
            onChange={handleChange}
            className="max-w-md h-10 rounded-lg bg-gray-50 border-transparent focus:bg-white hover:bg-white transition-colors"
            allowClear
        />
    );
});

// Memoized Table to prevent re-renders unless data or columns actually change
const OptimizedTable = memo(({ loading, dataSource, columns, total, current, pageSize, onChange }) => {
    return (
        <Table
            columns={columns}
            dataSource={dataSource}
            rowKey="id"
            loading={loading}
            pagination={{
                total,
                current,
                pageSize,
                showSizeChanger: true,
                className: "pb-2"
            }}
            onChange={onChange}
            className="custom-table"
            rowClassName={() => "hover:bg-blue-50/30 transition-colors"}
            virtual
            scroll={{ y: 500 }}
        />
    );
});

export default ManagementPage;
