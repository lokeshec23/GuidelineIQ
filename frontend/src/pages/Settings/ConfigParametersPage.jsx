import React, { useState, useEffect } from "react";
import { Table, Card, Button, Modal, Form, Input, Select, Space, Typography, Popconfirm, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import { dscrAPI } from "../../services/api";
import { showToast } from "../../utils/toast";

const { Title } = Typography;
const { Option } = Select;

const ConfigParametersPage = () => {
    const [parameters, setParameters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingParam, setEditingParam] = useState(null);
    const [form] = Form.useForm();
    const [searchText, setSearchText] = useState("");

    useEffect(() => {
        fetchParameters();
    }, []);

    const fetchParameters = async () => {
        setLoading(true);
        try {
            const response = await dscrAPI.listParameters();
            setParameters(response.data);
        } catch (error) {
            console.error("Failed to fetch parameters:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingParam(null);
        form.resetFields();
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingParam(record);
        form.setFieldsValue(record);
        setIsModalVisible(true);
    };

    const handleDelete = async (id) => {
        try {
            await dscrAPI.deleteParameter(id);
            showToast.success("Parameter deleted successfully");
            fetchParameters();
        } catch (error) {
            console.error("Failed to delete parameter:", error);
        }
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();

            if (editingParam) {
                await dscrAPI.updateParameter(editingParam.id, values);
                showToast.success("Parameter updated successfully");
            } else {
                await dscrAPI.createParameter(values);
                showToast.success("Parameter created successfully");
            }

            setIsModalVisible(false);
            fetchParameters();
        } catch (error) {
            console.error("Failed to save parameter:", error);
        }
    };

    const filteredParameters = parameters.filter(p =>
        p.parameter.toLowerCase().includes(searchText.toLowerCase()) ||
        p.category.toLowerCase().includes(searchText.toLowerCase())
    );

    const columns = [
        {
            title: "Parameter",
            dataIndex: "parameter",
            key: "parameter",
            sorter: (a, b) => a.parameter.localeCompare(b.parameter),
            render: (text) => <span className="font-medium text-gray-800">{text}</span>
        },
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            sorter: (a, b) => a.category.localeCompare(b.category),
            render: (text) => <Tag color="blue">{text}</Tag>
        },
        {
            title: "Subcategory",
            dataIndex: "subcategory",
            key: "subcategory",
        },
        {
            title: "PPE Field",
            dataIndex: "ppe_field",
            key: "ppe_field",
            render: (text) => text || <span className="text-gray-400 italic">None</span>
        },
        {
            title: "Actions",
            key: "actions",
            width: 150,
            render: (_, record) => (
                <Space size="middle">
                    <Button
                        type="text"
                        icon={<EditOutlined className="text-blue-500" />}
                        onClick={() => handleEdit(record)}
                    />
                    <Popconfirm
                        title="Delete parameter?"
                        description="Are you sure you want to delete this parameter?"
                        onConfirm={() => handleDelete(record.id)}
                        okText="Yes"
                        cancelText="No"
                    >
                        <Button
                            type="text"
                            icon={<DeleteOutlined className="text-red-500" />}
                        />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <Title level={2}>Config Parameters</Title>
                    <p className="text-gray-500 text-base">Manage parameters for extraction and mapping</p>
                </div>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleAdd}
                    size="large"
                    className="bg-blue-600 hover:bg-blue-700 rounded-lg h-11 px-6 shadow-md transition-all"
                >
                    Add Parameter
                </Button>
            </div>

            <Card className="shadow-sm border-gray-200 rounded-xl overflow-hidden" bordered={false}>
                <div className="mb-4">
                    <Input
                        placeholder="Search parameters or categories..."
                        prefix={<SearchOutlined className="text-gray-400" />}
                        value={searchText}
                        onChange={e => setSearchText(e.target.value)}
                        className="max-w-md h-10 rounded-lg"
                        allowClear
                    />
                </div>
                <Table
                    columns={columns}
                    dataSource={filteredParameters}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 12, showSizeChanger: true }}
                    className="custom-table"
                />
            </Card>

            <Modal
                title={editingParam ? "Edit DSCR Parameter" : "Add DSCR Parameter"}
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                okText={editingParam ? "Update" : "Create"}
                destroyOnClose
                centered
                maskClosable={false}
                width={600}
                okButtonProps={{ className: "bg-blue-600 h-10 px-6 rounded-lg" }}
                cancelButtonProps={{ className: "h-10 px-6 rounded-lg" }}
            >
                <Form
                    form={form}
                    layout="vertical"
                    className="mt-4"
                >
                    <Form.Item
                        name="parameter"
                        label="Parameter Name"
                        rules={[{ required: true, message: "Please enter parameter name" }]}
                    >
                        <Input placeholder="e.g. Credit Score Requirements" className="h-10 rounded-lg" />
                    </Form.Item>

                    <div className="grid grid-cols-2 gap-4">
                        <Form.Item
                            name="category"
                            label="Category"
                            rules={[{ required: true, message: "Please enter category" }]}
                        >
                            <Input placeholder="e.g. Credit / Housing" className="h-10 rounded-lg" />
                        </Form.Item>

                        <Form.Item
                            name="subcategory"
                            label="Subcategory"
                            initialValue="Feature Eligibility"
                        >
                            <Input className="h-10 rounded-lg" />
                        </Form.Item>
                    </div>

                    <Form.Item
                        name="ppe_field"
                        label="PPE Field Type"
                    >
                        <Select placeholder="Select field type" className="h-10" dropdownClassName="rounded-lg">
                            <Option value="Hard">Hard</Option>
                            <Option value="Soft">Soft</Option>
                            <Option value="Text">Text</Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default ConfigParametersPage;
