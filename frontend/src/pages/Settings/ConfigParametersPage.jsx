import React, { useState, useEffect, useRef } from "react";
import { Table, Card, Button, Modal, Form, Input, Select, Space, Typography, Popconfirm, Tag, Checkbox } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import { dscrAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import { TableSkeleton } from "../../components/common/SkeletonLoader";

const { Title } = Typography;
const { Option } = Select;

const GUIDELINE_TYPE_OPTIONS = ["DSCR", "Full Doc", "Alt Doc"];

const ConfigParametersPage = () => {
    const [parameters, setParameters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingParam, setEditingParam] = useState(null);
    const [form] = Form.useForm();
    const [searchText, setSearchText] = useState("");
    const prevGuidelineTypeRef = useRef([]);

    useEffect(() => {
        fetchParameters();
    }, []);

    const  fetchParameters = async () => {
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
        const defaultType = [...GUIDELINE_TYPE_OPTIONS]; // DSCR + Full Doc + Alt Doc
        form.setFieldsValue({ guideline_type: defaultType });
        prevGuidelineTypeRef.current = defaultType;
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingParam(record);
        let guidelineType = record.guideline_type || [...GUIDELINE_TYPE_OPTIONS];
        if (guidelineType.includes("All")) {
            guidelineType = [...new Set(guidelineType.flatMap(t => t === "All" ? ["DSCR", "Full Doc", "Alt Doc"] : t))];
        }
        form.setFieldsValue({
            ...record,
            guideline_type: guidelineType
        });
        prevGuidelineTypeRef.current = guidelineType;
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

    const handleRemoveAll = async () => {
        try {
            await dscrAPI.deleteAllParameters();
            showToast.success("All parameters deleted successfully");
            fetchParameters();
        } catch (error) {
            console.error("Failed to delete all parameters:", error);
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

    const handleGuidelineTypeChange = (checkedValues) => {
        form.setFieldsValue({ guideline_type: checkedValues });
        prevGuidelineTypeRef.current = checkedValues;
    };

    const filteredParameters = parameters.filter(p =>
        p.parameter.toLowerCase().includes(searchText.toLowerCase()) ||
        p.category.toLowerCase().includes(searchText.toLowerCase())
    );

    const guidelineTypeColorMap = {
        "DSCR": "blue",
        "Full Doc": "green",
        "Alt Doc": "orange"
    };

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
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 200,
            filters: GUIDELINE_TYPE_OPTIONS.map(t => ({ text: t, value: t })),
            onFilter: (value, record) => {
                let types = record.guideline_type || ["DSCR", "Full Doc", "Alt Doc"];
                if (types.includes("All")) {
                    types = [...new Set(types.flatMap(t => t === "All" ? ["DSCR", "Full Doc", "Alt Doc"] : t))];
                }
                return types.includes(value);
            },
            render: (types) => {
                let displayTypes = types || ["DSCR", "Full Doc", "Alt Doc"];
                if (displayTypes.includes("All")) {
                    displayTypes = [...new Set(displayTypes.flatMap(t => t === "All" ? ["DSCR", "Full Doc", "Alt Doc"] : t))];
                }
                return (
                    <Space size={[0, 4]} wrap>
                        {displayTypes.map(t => (
                            <Tag key={t} color={guidelineTypeColorMap[t] || "default"} style={{ margin: '2px' }}>
                                {t}
                            </Tag>
                        ))}
                    </Space>
                );
            }
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
                <div className="flex gap-2">
                    <Popconfirm
                        title="Delete all parameters?"
                        description="Are you sure you want to delete ALL parameters? This cannot be undone."
                        onConfirm={handleRemoveAll}
                        okText="Yes"
                        cancelText="No"
                        okButtonProps={{ danger: true }}
                    >
                        <Button
                            danger
                            type="primary"
                            icon={<DeleteOutlined />}
                            size="large"
                            className="rounded-lg h-11 px-6 shadow-md transition-all"
                            disabled={parameters.length === 0}
                        >
                            Remove All
                        </Button>
                    </Popconfirm>
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
            </div>

            {loading ? (
                <TableSkeleton rows={12} columns={5} />
            ) : (
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
            )}

            <Modal
                title={editingParam ? "Edit Parameter" : "Add Parameter"}
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
                        name="guideline_type"
                        label="Guideline Type"
                        rules={[{ required: true, message: "Please select at least one guideline type" }]}
                    >
                        <Checkbox.Group
                            onChange={handleGuidelineTypeChange}
                            style={{ width: "100%" }}
                        >
                            <div className="flex gap-4 flex-wrap">
                                {GUIDELINE_TYPE_OPTIONS.map(option => (
                                    <Checkbox key={option} value={option}>
                                        <Tag color={guidelineTypeColorMap[option] || "default"} style={{ cursor: "pointer" }}>
                                            {option}
                                        </Tag>
                                    </Checkbox>
                                ))}
                            </div>
                        </Checkbox.Group>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default ConfigParametersPage;
