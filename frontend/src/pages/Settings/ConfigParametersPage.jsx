import React, { useState, useEffect, useRef, useContext } from "react";
import { Table, Card, Button, Modal, Form, Input, Select, Space, Typography, Popconfirm, Tag, Checkbox, Divider, Tooltip, Row, Col, Statistic, Skeleton } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, SettingOutlined, AppstoreOutlined, DatabaseOutlined, TagsOutlined, TeamOutlined, DownloadOutlined } from "@ant-design/icons";
import { dscrAPI, investorAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import { TableSkeleton } from "../../components/common/SkeletonLoader";
import { useAuth } from "../../context/AuthContext";

const { Title } = Typography;
const { Option } = Select;

const GUIDELINE_TYPE_OPTIONS = ["DSCR", "Full Doc", "Alt Doc"];

const ConfigParametersPage = () => {
    const { user } = useAuth();
    const isAdmin = user?.role === "admin";

    // Parameter State
    const [parameters, setParameters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingParam, setEditingParam] = useState(null);
    const [form] = Form.useForm();
    const [searchText, setSearchText] = useState("");
    const prevGuidelineTypeRef = useRef([]);

    // Investor State
    const [investors, setInvestors] = useState([]);
    const [selectedInvestorId, setSelectedInvestorId] = useState("null"); // 'null' represents General

    // Manage Investors Modal State
    const [isManageInvestorsVisible, setIsManageInvestorsVisible] = useState(false);
    const [investorForm] = Form.useForm();
    const [editingInvestor, setEditingInvestor] = useState(null);
    const [investorsLoading, setInvestorsLoading] = useState(false);
    const [investorSubmitting, setInvestorSubmitting] = useState(false);

    // Import from General Parameters State
    const [isImportModalVisible, setIsImportModalVisible] = useState(false);
    const [generalParams, setGeneralParams] = useState([]);
    const [selectedParamIds, setSelectedParamIds] = useState([]);
    const [importLoading, setImportLoading] = useState(false);
    const [importSearchText, setImportSearchText] = useState("");
    const [generalParamsLoading, setGeneralParamsLoading] = useState(false);

    useEffect(() => {
        fetchInvestors();
    }, []);

    useEffect(() => {
        fetchParameters();
    }, [selectedInvestorId]);

    const fetchInvestors = async () => {
        try {
            const response = await investorAPI.listInvestors();
            setInvestors(response.data);
        } catch (error) {
            console.error("Failed to fetch investors:", error);
        }
    };

    const fetchParameters = async () => {
        setLoading(true);
        try {
            const response = await dscrAPI.listParameters(selectedInvestorId);
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
            // Delete only the parameters for the currently selected context,
            // NOT all parameters globally across all investors.
            await Promise.all(parameters.map(p => dscrAPI.deleteParameter(p.id)));
            showToast.success("All parameters deleted successfully");
            fetchParameters();
        } catch (error) {
            console.error("Failed to delete all parameters:", error);
        }
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();

            // Inject selected investor ID if not general
            const payload = { ...values };
            if (selectedInvestorId !== "null") {
                payload.investor_id = selectedInvestorId;
            }

            if (editingParam) {
                await dscrAPI.updateParameter(editingParam.id, payload);
                showToast.success("Parameter updated successfully");
            } else {
                await dscrAPI.createParameter(payload);
                showToast.success("Parameter created successfully");
            }

            setIsModalVisible(false);
            fetchParameters();
        } catch (error) {
            console.error("Failed to save parameter:", error);
        }
    };

    /* === Import from General Parameters Flow === */
    const fetchGeneralParameters = async () => {
        setGeneralParamsLoading(true);
        try {
            const response = await dscrAPI.listParameters("null");
            setGeneralParams(response.data);
        } catch (error) {
            console.error("Failed to fetch general parameters:", error);
            showToast.error("Failed to load general parameters");
        } finally {
            setGeneralParamsLoading(false);
        }
    };

    const handleOpenImportModal = async () => {
        setSelectedParamIds([]);
        setImportSearchText("");
        setIsImportModalVisible(true);
        await fetchGeneralParameters();
    };

    const handleImportParams = async () => {
        if (selectedParamIds.length === 0) {
            showToast.warning("Please select at least one parameter to import.");
            return;
        }
        setImportLoading(true);
        try {
            const toImport = generalParams.filter(p => selectedParamIds.includes(p.id));
            await Promise.all(
                toImport.map(p =>
                    dscrAPI.createParameter({
                        parameter: p.parameter,
                        category: p.category,
                        subcategory: p.subcategory,
                        guideline_type: p.guideline_type,
                        investor_id: selectedInvestorId,
                    })
                )
            );
            showToast.success(`${toImport.length} parameter(s) imported successfully.`);
            setIsImportModalVisible(false);
            fetchParameters();
        } catch (error) {
            console.error("Failed to import parameters:", error);
        } finally {
            setImportLoading(false);
        }
    };

    /* === Manage Investors Flow === */
    const handleManageInvestors = () => {
        if (!isAdmin) return;
        setIsManageInvestorsVisible(true);
    };

    const handleInvestorEdit = (inv) => {
        setEditingInvestor(inv);
        investorForm.setFieldsValue({ name: inv.name });
    };

    const handleInvestorDelete = async (id) => {
        try {
            await investorAPI.deleteInvestor(id);
            showToast.success("Investor deleted successfully");
            if (selectedInvestorId === id) setSelectedInvestorId("null");
            fetchInvestors();
        } catch (error) {
            console.error("Failed to delete investor", error);
        }
    };

    const handleInvestorSubmit = async () => {
        try {
            const values = await investorForm.validateFields();
            setInvestorSubmitting(true);
            if (editingInvestor) {
                await investorAPI.updateInvestor(editingInvestor.id, values);
                showToast.success("Investor updated successfully");
            } else {
                await investorAPI.createInvestor(values);
                showToast.success("Investor created successfully");
            }
            investorForm.resetFields();
            setEditingInvestor(null);
            fetchInvestors();
        } catch (error) {
            console.error("Failed to save investor", error);
        } finally {
            setInvestorSubmitting(false);
        }
    };

    const handleInvestorFormCancel = () => {
        investorForm.resetFields();
        setEditingInvestor(null);
    };

    const handleManageInvestorsClose = () => {
        setIsManageInvestorsVisible(false);
        handleInvestorFormCancel();
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
        "Alt Doc": "purple"
    };

    const columns = [
        {
            title: "Parameter Name",
            dataIndex: "parameter",
            key: "parameter",
            sorter: (a, b) => a.parameter.localeCompare(b.parameter),
            render: (text) => <span className="font-semibold text-[var(--text-primary)]">{text}</span>
        },
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            sorter: (a, b) => a.category.localeCompare(b.category),
            render: (text) => (
                <Tag className="bg-blue-50 text-blue-600 border-blue-200 px-3 py-1 rounded-full font-medium">
                    {text}
                </Tag>
            )
        },
        {
            title: "Subcategory",
            dataIndex: "subcategory",
            key: "subcategory",
            render: (text) => <span className="text-[var(--text-secondary)]">{text || "—"}</span>
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 250,
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
                    <Space size={[0, 6]} wrap>
                        {displayTypes.map(t => (
                            <Tag
                                key={t}
                                color={guidelineTypeColorMap[t] || "default"}
                                className="px-3 rounded-full text-xs font-medium border-transparent cursor-default scale-100 hover:scale-[1.02] transition-transform"
                            >
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
            width: 120,
            render: (_, record) => (
                <Space size="small">
                    <Tooltip title="Edit">
                        <Button
                            type="text"
                            icon={<EditOutlined className="text-gray-400 hover:text-blue-500 transition-colors" />}
                            onClick={() => handleEdit(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Delete">
                        <Popconfirm
                            title="Delete parameter?"
                            description="Are you sure you want to delete this parameter?"
                            onConfirm={() => handleDelete(record.id)}
                            okText="Yes"
                            cancelText="No"
                            okButtonProps={{ danger: true }}
                        >
                            <Button
                                type="text"
                                icon={<DeleteOutlined className="text-gray-400 hover:text-red-500 transition-colors" />}
                            />
                        </Popconfirm>
                    </Tooltip>
                </Space>
            ),
        },
    ];

    // Calculate stats
    const totalParams = parameters.length;

    const getTypeCount = (type) => parameters.filter(p => {
        let types = p.guideline_type || ["DSCR", "Full Doc", "Alt Doc"];
        if (typeof types === 'string') {
            types = [types];
        }
        if (types.includes("All")) {
            types = [...new Set(types.flatMap(t => t === "All" ? ["DSCR", "Full Doc", "Alt Doc"] : t))];
        }
        return types.includes(type);
    }).length;

    const dscrCount = getTypeCount("DSCR");
    const fullDocCount = getTypeCount("Full Doc");
    const altDocCount = getTypeCount("Alt Doc");

    const activeContextName = selectedInvestorId === "null"
        ? "General Properties"
        : investors.find(inv => inv.id === selectedInvestorId)?.name || "Unknown";

    return (
        <div className="max-w-7xl mx-auto pb-10">
            {/* Header / Context Filter Bar */}
            <div className="mb-6">
                <div className="bg-[var(--bg-surface)] p-3 rounded-2xl shadow-sm border border-[var(--color-border)] w-full md:w-1/2 flex items-center gap-4">
                    <span className="text-[var(--text-secondary)] font-semibold text-sm flex items-center gap-2 ml-2 whitespace-nowrap uppercase tracking-wider">
                        <DatabaseOutlined className="text-blue-500 text-lg" /> Active Context
                    </span>
                    <Select
                        value={selectedInvestorId}
                        onChange={(val) => setSelectedInvestorId(val)}
                        className="bg-[var(--bg-base)] rounded-xl investor-select flex-1"
                        size="large"
                        bordered={false}
                        options={[
                            { label: <span className="font-medium text-[var(--text-primary)]">General parameters</span>, value: "null" },
                            ...investors.map(inv => ({ label: <span className="font-medium text-[var(--text-primary)]">{inv.name}</span>, value: inv.id }))
                        ]}
                    />
                    {isAdmin && (
                        <Tooltip title="Manage Contexts">
                            <Button
                                type="text"
                                icon={<SettingOutlined className="text-lg" />}
                                onClick={handleManageInvestors}
                                className="flex items-center justify-center text-gray-400 hover:text-blue-600 hover:bg-blue-50 h-10 w-10 mr-1 rounded-xl transition-colors"
                            />
                        </Tooltip>
                    )}
                </div>
            </div>

            {/* Stats Overview */}
            <Row gutter={[24, 24]} className="mb-8 flex items-stretch">
                <Col xs={24} md={12}>
                    <Card className="shadow-sm border-[var(--color-border)] rounded-2xl hover:shadow-md transition-shadow h-full flex flex-col justify-center bg-[var(--bg-surface)]">
                        <Statistic
                            title={<span className="text-[var(--text-secondary)] font-medium flex items-center gap-2"><AppstoreOutlined /> Total Parameters</span>}
                            value={totalParams}
                            valueStyle={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '28px' }}
                            formatter={(val) => loading ? <Skeleton.Button active size="small" style={{ minWidth: "60px", height: "38px", borderRadius: "6px" }} /> : val}
                        />
                    </Card>
                </Col>
                <Col xs={24} md={12}>
                    <Card className="shadow-sm border-[var(--color-border)] rounded-2xl hover:shadow-md transition-shadow h-full bg-[var(--bg-surface)]">
                        <span className="text-[var(--text-secondary)] font-medium flex items-center gap-2 mb-3 text-sm"><TagsOutlined /> Types Breakdown</span>
                        <div className="flex justify-between items-center w-full">
                            <Statistic
                                title={<span className="text-blue-500 font-semibold text-[11px] uppercase tracking-wider">DSCR</span>}
                                value={dscrCount}
                                valueStyle={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '20px' }}
                                formatter={(val) => loading ? <Skeleton.Button active size="small" style={{ minWidth: "40px", height: "30px", borderRadius: "6px" }} /> : val}
                            />
                            <Divider type="vertical" className="h-8 border-[var(--color-border)] mx-1 lg:mx-2" />
                            <Statistic
                                title={<span className="text-green-500 font-semibold text-[11px] uppercase tracking-wider">Full Doc</span>}
                                value={fullDocCount}
                                valueStyle={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '20px' }}
                                formatter={(val) => loading ? <Skeleton.Button active size="small" style={{ minWidth: "40px", height: "30px", borderRadius: "6px" }} /> : val}
                            />
                            <Divider type="vertical" className="h-8 border-[var(--color-border)] mx-1 lg:mx-2" />
                            <Statistic
                                title={<span className="text-purple-500 font-semibold text-[11px] uppercase tracking-wider">Alt Doc</span>}
                                value={altDocCount}
                                valueStyle={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '20px' }}
                                formatter={(val) => loading ? <Skeleton.Button active size="small" style={{ minWidth: "40px", height: "30px", borderRadius: "6px" }} /> : val}
                            />
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Main Content Area */}
            <Card className="shadow-sm border-[var(--color-border)] rounded-2xl overflow-hidden bg-[var(--bg-surface)]" bordered={false} bodyStyle={{ padding: 0 }}>
                {/* Table Header Controls */}
                <div className="p-5 border-b border-[var(--color-border)] bg-[var(--bg-surface)] flex flex-col sm:flex-row justify-between items-center gap-4">
                    <Input
                        placeholder="Search parameters or categories..."
                        prefix={<SearchOutlined className="text-gray-400" />}
                        value={searchText}
                        onChange={e => setSearchText(e.target.value)}
                        className="max-w-md h-10 rounded-lg bg-[var(--bg-base)] border-transparent focus:bg-[var(--bg-surface)] hover:bg-[var(--bg-surface)] transition-colors text-[var(--text-primary)]"
                        allowClear
                    />
                    <div className="flex gap-3 w-full sm:w-auto">
                        {selectedInvestorId !== "null" && (
                            <Button
                                icon={<DownloadOutlined />}
                                onClick={handleOpenImportModal}
                                className="rounded-lg font-medium border-blue-200 text-blue-600 hover:bg-blue-50 hover:border-blue-400"
                            >
                                Import from General
                            </Button>
                        )}
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={handleAdd}
                            className="bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm font-medium"
                        >
                            Add Parameter
                        </Button>
                        <Popconfirm
                            title="Delete all parameters?"
                            description={`Are you sure you want to delete ALL parameters for the selected context?`}
                            onConfirm={handleRemoveAll}
                            okText="Yes"
                            cancelText="No"
                            okButtonProps={{ danger: true }}
                        >
                            <Button
                                danger
                                icon={<DeleteOutlined />}
                                disabled={parameters.length === 0}
                                className="rounded-lg"
                            >
                                Remove All
                            </Button>
                        </Popconfirm>


                    </div>
                </div>

                {/* Table */}
                {loading ? (
                    <div className="p-6">
                        <TableSkeleton rows={8} columns={5} />
                    </div>
                ) : (
                    <div className="p-6">
                        <Table
                            columns={columns}
                            dataSource={filteredParameters}
                            rowKey="id"
                            pagination={{
                                pageSize: 12,
                                showSizeChanger: true,
                                className: "px-6 pb-2"
                            }}
                            className="custom-table"
                            rowClassName={() => "hover:bg-blue-50/30 transition-colors cursor-pointer"}
                        />
                    </div>
                )}
            </Card>

            {/* Parameter Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-[var(--text-primary)] text-lg font-semibold">
                        {editingParam ? <EditOutlined className="text-blue-500" /> : <PlusOutlined className="text-blue-500" />}
                        {editingParam ? "Edit Parameter" : "Add New Parameter"}
                    </div>
                }
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                okText={editingParam ? "Update Parameter" : "Create Parameter"}
                destroyOnClose
                centered
                maskClosable={false}
                width={650}
                className="parameter-modal"
                okButtonProps={{ className: "bg-blue-600 rounded-lg font-medium shadow-sm h-10 px-6" }}
                cancelButtonProps={{ className: "rounded-lg h-10 px-6" }}
            >
                <Form
                    form={form}
                    layout="vertical"
                    className="mt-6"
                    requiredMark={false}
                >
                    <Form.Item
                        name="parameter"
                        label={<span className="font-medium text-[var(--text-primary)]">Parameter Name</span>}
                        rules={[{ required: true, message: "Please enter parameter name" }]}
                    >
                        <Input placeholder="e.g. Credit Score Requirements" className="h-11 rounded-lg bg-[var(--bg-base)] text-[var(--text-primary)] focus:bg-[var(--bg-surface)] hover:bg-[var(--bg-surface)]" />
                    </Form.Item>

                    <div className="grid grid-cols-2 gap-5 mt-2">
                        <Form.Item
                            name="category"
                            label={<span className="font-medium text-[var(--text-primary)]">Category</span>}
                            rules={[{ required: true, message: "Please enter category" }]}
                        >
                            <Input placeholder="e.g. Credit / Housing" className="h-11 rounded-lg bg-[var(--bg-base)] text-[var(--text-primary)] focus:bg-[var(--bg-surface)] hover:bg-[var(--bg-surface)]" />
                        </Form.Item>

                        <Form.Item
                            name="subcategory"
                            label={<span className="font-medium text-[var(--text-primary)]">Subcategory</span>}
                            initialValue="Feature Eligibility"
                        >
                            <Input placeholder="Optional" className="h-11 rounded-lg bg-[var(--bg-base)] text-[var(--text-primary)] focus:bg-[var(--bg-surface)] hover:bg-[var(--bg-surface)]" />
                        </Form.Item>
                    </div>

                    <Form.Item
                        name="guideline_type"
                        label={<span className="font-medium text-[var(--text-primary)]">Guideline Compatibility</span>}
                        rules={[{ required: true, message: "Please select at least one guideline type" }]}
                        className="mt-2 mb-0"
                    >
                        <Checkbox.Group
                            onChange={handleGuidelineTypeChange}
                            className="w-full bg-[var(--bg-base)] p-4 rounded-xl border border-[var(--color-border)]"
                        >
                            <div className="flex gap-6 flex-wrap">
                                {GUIDELINE_TYPE_OPTIONS.map(option => (
                                    <Checkbox key={option} value={option}>
                                        <span className="text-[var(--text-primary)] font-medium ml-1">{option}</span>
                                    </Checkbox>
                                ))}
                            </div>
                        </Checkbox.Group>
                    </Form.Item>
                </Form>
            </Modal>

            {/* Import from General Parameters Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-[var(--text-primary)] text-lg font-semibold">
                        <DownloadOutlined className="text-blue-500" />
                        Import from General Parameters
                    </div>
                }
                open={isImportModalVisible}
                onCancel={() => setIsImportModalVisible(false)}
                onOk={handleImportParams}
                okText={`Import Selected (${selectedParamIds.length})`}
                okButtonProps={{
                    className: "bg-blue-600 rounded-lg font-medium shadow-sm h-10 px-6",
                    loading: importLoading,
                    disabled: selectedParamIds.length === 0,
                }}
                cancelButtonProps={{ className: "rounded-lg h-10 px-6" }}
                width={680}
                centered
                destroyOnClose
                maskClosable={false}
            >
                <div className="mt-4 flex flex-col gap-4">
                    {/* Search within modal */}
                    <Input
                        placeholder="Search general parameters..."
                        prefix={<SearchOutlined className="text-gray-400" />}
                        value={importSearchText}
                        onChange={e => setImportSearchText(e.target.value)}
                        className="h-10 rounded-lg bg-[var(--bg-base)] border-transparent focus:bg-[var(--bg-surface)] text-[var(--text-primary)]"
                        allowClear
                    />

                    {/* Select-all row */}
                    {!generalParamsLoading && generalParams.length > 0 && (
                        <div className="flex items-center justify-between px-1">
                            <Checkbox
                                indeterminate={
                                    selectedParamIds.length > 0 &&
                                    selectedParamIds.length < generalParams.filter(p =>
                                        p.parameter.toLowerCase().includes(importSearchText.toLowerCase()) ||
                                        p.category.toLowerCase().includes(importSearchText.toLowerCase())
                                    ).length
                                }
                                checked={
                                    generalParams.filter(p =>
                                        p.parameter.toLowerCase().includes(importSearchText.toLowerCase()) ||
                                        p.category.toLowerCase().includes(importSearchText.toLowerCase())
                                    ).length > 0 &&
                                    generalParams
                                        .filter(p =>
                                            p.parameter.toLowerCase().includes(importSearchText.toLowerCase()) ||
                                            p.category.toLowerCase().includes(importSearchText.toLowerCase())
                                        )
                                        .every(p => selectedParamIds.includes(p.id))
                                }
                                onChange={e => {
                                    const visible = generalParams.filter(p =>
                                        p.parameter.toLowerCase().includes(importSearchText.toLowerCase()) ||
                                        p.category.toLowerCase().includes(importSearchText.toLowerCase())
                                    );
                                    if (e.target.checked) {
                                        setSelectedParamIds(prev => [
                                            ...new Set([...prev, ...visible.map(p => p.id)])
                                        ]);
                                    } else {
                                        const visibleIds = visible.map(p => p.id);
                                        setSelectedParamIds(prev => prev.filter(id => !visibleIds.includes(id)));
                                    }
                                }}
                            >
                                <span className="text-sm font-medium text-[var(--text-secondary)]">Select All Visible</span>
                            </Checkbox>
                            <span className="text-xs text-gray-400 font-medium">
                                {selectedParamIds.length} selected
                            </span>
                        </div>
                    )}

                    {/* Parameter list */}
                    <div className="max-h-80 overflow-y-auto border border-[var(--color-border)] rounded-xl divide-y divide-[var(--color-border)]">
                        {generalParamsLoading ? (
                            <div className="p-6">
                                <TableSkeleton rows={5} columns={3} />
                            </div>
                        ) : generalParams.filter(p =>
                            p.parameter.toLowerCase().includes(importSearchText.toLowerCase()) ||
                            p.category.toLowerCase().includes(importSearchText.toLowerCase())
                        ).length === 0 ? (
                            <div className="text-center py-12 text-gray-400">
                                <DatabaseOutlined className="text-3xl mb-2 block mx-auto" />
                                <div className="font-medium">{importSearchText ? "No matching parameters" : "No general parameters found"}</div>
                            </div>
                        ) : (
                            generalParams
                                .filter(p =>
                                    p.parameter.toLowerCase().includes(importSearchText.toLowerCase()) ||
                                    p.category.toLowerCase().includes(importSearchText.toLowerCase())
                                )
                                .map(param => (
                                    <div
                                        key={param.id}
                                        className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-blue-500/10 ${selectedParamIds.includes(param.id) ? "bg-blue-500/10" : "bg-[var(--bg-surface)]"
                                            }`}
                                        onClick={() => setSelectedParamIds(prev =>
                                            prev.includes(param.id)
                                                ? prev.filter(id => id !== param.id)
                                                : [...prev, param.id]
                                        )}
                                    >
                                        <Checkbox
                                            checked={selectedParamIds.includes(param.id)}
                                            onChange={() => { }}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="font-semibold text-[var(--text-primary)] text-sm truncate">{param.parameter}</div>
                                            <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                                                <Tag className="bg-blue-50 text-blue-500 border-blue-100 text-[11px] px-2 py-0 rounded-full">{param.category}</Tag>
                                                {param.subcategory && <span className="ml-1">{param.subcategory}</span>}
                                            </div>
                                        </div>
                                        <Space size={[0, 4]} wrap className="justify-end shrink-0">
                                            {(() => {
                                                let types = param.guideline_type || ["DSCR", "Full Doc", "Alt Doc"];
                                                if (types.includes("All")) {
                                                    types = [...new Set(types.flatMap(t => t === "All" ? ["DSCR", "Full Doc", "Alt Doc"] : t))];
                                                }
                                                return types.map(t => (
                                                    <Tag
                                                        key={t}
                                                        color={guidelineTypeColorMap[t]}
                                                        className="text-[10px] px-2 rounded-full border-transparent"
                                                    >
                                                        {t}
                                                    </Tag>
                                                ));
                                            })()}
                                        </Space>
                                    </div>
                                ))
                        )}
                    </div>
                </div>
            </Modal>

            {/* Manage Investors Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-[var(--text-primary)] text-lg font-semibold">
                        <TeamOutlined className="text-blue-500" />
                        Manage Contexts (Investors)
                    </div>
                }
                open={isManageInvestorsVisible}
                onCancel={handleManageInvestorsClose}
                footer={null}
                width={550}
                destroyOnClose
                centered
            >
                <div className="mb-6 mt-4">
                    <div className="bg-[var(--bg-base)] p-5 rounded-xl border border-[var(--color-border)]">
                        <span className="text-sm tracking-wide uppercase text-blue-600 font-bold mb-3 block">
                            {editingInvestor ? "Edit Context" : "Add New Context"}
                        </span>
                        <Form
                            form={investorForm}
                            layout="inline"
                            onFinish={handleInvestorSubmit}
                            className="flex items-start w-full gap-2"
                        >
                            <Form.Item
                                name="name"
                                rules={[{ required: true, message: 'Name is required' }]}
                                className="flex-grow m-0"
                            >
                                <Input placeholder="e.g. Rocket Mortgage" className="h-10 rounded-lg bg-[var(--bg-surface)] text-[var(--text-primary)]" />
                            </Form.Item>
                            <Form.Item className="m-0">
                                <Button type="primary" htmlType="submit" loading={investorSubmitting} className="h-10 px-6 rounded-lg font-medium shadow-sm">
                                    {editingInvestor ? "Update" : "Add"}
                                </Button>
                            </Form.Item>
                            {editingInvestor && (
                                <Form.Item className="m-0">
                                    <Button onClick={handleInvestorFormCancel} className="h-10 px-4 rounded-lg">
                                        Cancel
                                    </Button>
                                </Form.Item>
                            )}
                        </Form>
                    </div>
                </div>

                <div className="flex items-center justify-between mb-3 mt-8">
                    <span className="text-sm tracking-wide uppercase text-[var(--text-secondary)] font-bold">Existing Contexts</span>
                    <span className="bg-[var(--bg-base)] text-[var(--text-primary)] px-2 py-0.5 rounded-full text-xs font-semibold">{investors.length} Total</span>
                </div>

                <div className="max-h-72 overflow-y-auto border border-[var(--color-border)] rounded-xl">
                    {investors.length === 0 ? (
                        <div className="text-center py-10 bg-[var(--bg-base)]">
                            <DatabaseOutlined className="text-3xl text-[var(--text-secondary)] mb-2 block mx-auto" />
                            <div className="text-[var(--text-secondary)] font-medium">No contexts added yet</div>
                        </div>
                    ) : (
                        <Table
                            size="middle"
                            dataSource={investors}
                            rowKey="id"
                            pagination={false}
                            className="border-0"
                            columns={[
                                {
                                    title: "Name",
                                    dataIndex: "name",
                                    key: "name",
                                    render: (text) => <span className="font-semibold text-[var(--text-primary)]">{text}</span>
                                },
                                {
                                    title: "Actions",
                                    key: "actions",
                                    width: 120,
                                    align: 'right',
                                    render: (_, record) => (
                                        <Space size="small">
                                            <Tooltip title="Edit Context">
                                                <Button
                                                    type="text"
                                                    icon={<EditOutlined className="text-gray-400 hover:text-blue-500" />}
                                                    onClick={() => handleInvestorEdit(record)}
                                                />
                                            </Tooltip>
                                            <Tooltip title="Delete Context">
                                                <Popconfirm
                                                    title="Delete context?"
                                                    description="Parameters linked to this context will also be deleted."
                                                    onConfirm={() => handleInvestorDelete(record.id)}
                                                    okText="Yes"
                                                    cancelText="No"
                                                    okButtonProps={{ danger: true }}
                                                >
                                                    <Button
                                                        type="text"
                                                        icon={<DeleteOutlined className="text-gray-400 hover:text-red-500" />}
                                                    />
                                                </Popconfirm>
                                            </Tooltip>
                                        </Space>
                                    ),
                                }
                            ]}
                        />
                    )}
                </div>
            </Modal>
        </div>
    );
};

export default ConfigParametersPage;
