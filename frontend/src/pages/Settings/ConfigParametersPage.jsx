import React, { useState, useEffect, useRef, useMemo, useCallback, useDeferredValue, memo } from "react";
import { Table, Card, Button, Modal, Form, Input, Select, Space, Typography, Popconfirm, Tag, Checkbox, Divider, Tooltip, Row, Col, Statistic, Skeleton, Tabs } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, SettingOutlined, AppstoreOutlined, DatabaseOutlined, TagsOutlined, TeamOutlined, DownloadOutlined, FilterFilled, ReloadOutlined, UploadOutlined, InboxOutlined, FileExcelOutlined } from "@ant-design/icons";
import { dscrAPI, investorAPI, guidelineTypeAPI } from "../../services/api";
import { showToast } from "../../utils/toast";
import { TableSkeleton } from "../../components/common/SkeletonLoader";
import { useAuth } from "../../context/AuthContext";

const { Title } = Typography;
const { Option } = Select;

const ConfigParametersPage = () => {
    const { user } = useAuth();
    const isAdmin = user?.role === "admin";

    // Guideline Type State
    const [guidelineTypes, setGuidelineTypes] = useState([]);
    const [guidelineTypesLoading, setGuidelineTypesLoading] = useState(false);
    // Parameter State
    const [parameters, setParameters] = useState([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [serverBreakdown, setServerBreakdown] = useState({});
    const [tableParams, setTableParams] = useState({
        pagination: {
            current: 1,
            pageSize: 12,
        },
        filters: null,
        sortField: null,
        sortOrder: null,
    });

    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingParam, setEditingParam] = useState(null);
    const [form] = Form.useForm();
    const [searchText, setSearchText] = useState("");
    const [debouncedSearchText, setDebouncedSearchText] = useState("");
    const prevGuidelineTypeRef = useRef([]);

    const [activeTab, setActiveTab] = useState("single");
    const [excelFile, setExcelFile] = useState(null);
    const [bulkUploading, setBulkUploading] = useState(false);

    // Debounce search text
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearchText(searchText);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchText]);

    // Investor State
    const [investors, setInvestors] = useState([]);
    const [selectedInvestorId, setSelectedInvestorId] = useState(null);

    // Manage Investors Modal State
    const [isManageInvestorsVisible, setIsManageInvestorsVisible] = useState(false);
    const [investorForm] = Form.useForm();
    const [editingInvestor, setEditingInvestor] = useState(null);
    const [investorsLoading, setInvestorsLoading] = useState(false);
    const [investorSubmitting, setInvestorSubmitting] = useState(false);

    /* === Import from General Parameters === */
    const [isImportModalVisible, setIsImportModalVisible] = useState(false);


    // Manage Guideline Types State
    const [gTypeForm] = Form.useForm();
    const [editingGType, setEditingGType] = useState(null);
    const [gTypeSubmitting, setGTypeSubmitting] = useState(false);

    useEffect(() => {
        fetchInvestors();
        fetchGuidelineTypes();
    }, []);

    const fetchGuidelineTypes = async () => {
        setGuidelineTypesLoading(true);
        try {
            // Fetch with large pageSize to ensure all types are available for filters/dropdowns
            const response = await guidelineTypeAPI.listTypes({ pageSize: 100 });
            setGuidelineTypes(response.data.items || []);
        } catch (error) {
            console.error("Failed to fetch guideline types:", error);
            showToast.error("Failed to load guideline types");
        } finally {
            setGuidelineTypesLoading(false);
        }
    };

    // Re-fetch parameters whenever table params, debounced search, or investor changes
    useEffect(() => {
        if (selectedInvestorId) {
            fetchParameters();
        }
    }, [
        selectedInvestorId,
        tableParams.pagination.current,
        tableParams.pagination.pageSize,
        tableParams.filters,
        tableParams.sortField,
        tableParams.sortOrder,
        debouncedSearchText
    ]);

    const fetchInvestors = async () => {
        try {
            // Fetch with large pageSize to ensure all investors are available in the dropdown
            const response = await investorAPI.listInvestors({ pageSize: 100 });
            const data = response.data.items || [];
            setInvestors(data);
            if (data.length > 0 && !selectedInvestorId) {
                // Set the first investor — this triggers the selectedInvestorId useEffect
                // which will call fetchParameters(). No manual call needed here.
                setSelectedInvestorId(data[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch investors:", error);
            showToast.error("Failed to load investors");
        }
    };

    const fetchParameters = async (investorId = selectedInvestorId) => {
        if (!investorId) return;
        setLoading(true);
        try {
            const params = {
                page: tableParams.pagination.current,
                pageSize: tableParams.pagination.pageSize,
                search: debouncedSearchText,
                sortField: tableParams.sortField,
                sortOrder: tableParams.sortOrder,
                filters: tableParams.filters ? JSON.stringify(tableParams.filters) : undefined
            };
            const response = await dscrAPI.listParameters(investorId, params);
            setParameters(response.data.items || []);
            setTotal(response.data.total || 0);
            setServerBreakdown(response.data.breakdown || {});
        } catch (error) {
            console.error("Failed to fetch parameters:", error);
            showToast.error("Failed to load parameters. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleTableChange = (pagination, filters, sorter) => {
        setTableParams({
            pagination,
            filters,
            sortField: sorter.field,
            sortOrder: sorter.order,
        });
    };

    const handleClearFilters = () => {
        setSearchText("");
        setTableParams(prev => ({
            ...prev,
            pagination: { ...prev.pagination, current: 1 },
            filters: null,
        }));
        // showToast.info("Filters reset");
    };

    const handleAdd = () => {
        setEditingParam(null);
        setActiveTab("single");
        setExcelFile(null);
        form.resetFields();
        const defaultType = guidelineTypes.map(t => t.name);
        form.setFieldsValue({ guideline_type: defaultType });
        prevGuidelineTypeRef.current = defaultType;
        setIsModalVisible(true);
    };

    const handleEdit = useCallback((record) => {
        setEditingParam(record);
        let guidelineType = record.guideline_type || guidelineTypes.map(t => t.name);
        if (guidelineType.includes("All")) {
            guidelineType = guidelineTypes.map(t => t.name);
        }
        form.setFieldsValue({
            ...record,
            guideline_type: guidelineType
        });
        prevGuidelineTypeRef.current = guidelineType;
        setIsModalVisible(true);
    }, [form]);

    const handleDelete = useCallback(async (record) => {
        try {
            await dscrAPI.deleteParameter(record.id);
            showToast.success("Parameter deleted successfully");
            fetchParameters();
        } catch (error) {
            console.error("Failed to delete parameter:", error);
        }
    }, [selectedInvestorId]); // Added dependency to ensure fetchParameters is current

    const handleRemoveAll = async () => {
        try {
            setLoading(true);
            const deleteParams = {
                investor_id: selectedInvestorId,
                search: debouncedSearchText,
                filters: tableParams.filters ? JSON.stringify(tableParams.filters) : undefined
            };

            await dscrAPI.deleteAllParameters(deleteParams);
            showToast.success("All matching parameters deleted successfully");

            // Reset to first page after deletion
            setTableParams(prev => ({
                ...prev,
                pagination: { ...prev.pagination, current: 1 }
            }));
            fetchParameters();
        } catch (error) {
            console.error("Failed to delete all parameters:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();

            const payload = { ...values, is_active: true };
            if (selectedInvestorId) {
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

    const handleExcelFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (ext !== 'xlsx' && ext !== 'xls') {
                showToast.error("Only Excel files (.xlsx, .xls) are allowed");
                setExcelFile(null);
                return;
            }
            setExcelFile(file);
        }
    };

    const handleBulkUploadSubmit = async () => {
        if (!excelFile) {
            showToast.warning("Please upload an Excel file first");
            return;
        }

        const formData = new FormData();
        formData.append("file", excelFile);

        setBulkUploading(true);
        try {
            const response = await dscrAPI.bulkUploadGeneralParameters(formData, selectedInvestorId);
            showToast.success(response.data.message || "Excel file uploaded and imported successfully");

            // Clean up states
            setExcelFile(null);
            setActiveTab("single");
            setIsModalVisible(false);

            // Refresh list
            fetchParameters();
        } catch (error) {
            console.error("Bulk upload failed:", error);
        } finally {
            setBulkUploading(false);
        }
    };

    const handleOpenImportModal = () => {
        setIsImportModalVisible(true);
    };



    const guidelineTypeColorMap = useMemo(() => {
        const map = {};
        guidelineTypes.forEach(t => {
            map[t.name] = t.color || "default";
        });
        return map;
    }, [guidelineTypes]);


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
            if (selectedInvestorId === id) setSelectedInvestorId(null);
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

    /* === Manage Guideline Types Flow === */
    const handleGTypeEdit = (type) => {
        setEditingGType(type);
        gTypeForm.setFieldsValue({
            name: type.name
        });
    };

    const handleGTypeDelete = async (id) => {
        try {
            await guidelineTypeAPI.deleteType(id);
            showToast.success("Guideline type deleted successfully");
            fetchGuidelineTypes();
        } catch (error) {
            console.error("Failed to delete guideline type", error);
        }
    };

    const handleGTypeSubmit = async () => {
        try {
            const values = await gTypeForm.validateFields();
            setGTypeSubmitting(true);

            if (editingGType) {
                await guidelineTypeAPI.updateType(editingGType.id, {
                    ...values,
                    color: editingGType.color || GTYPE_COLORS[Math.floor(Math.random() * GTYPE_COLORS.length)]
                });
                showToast.success("Guideline type updated successfully");
            } else {
                const randomColor = GTYPE_COLORS[Math.floor(Math.random() * GTYPE_COLORS.length)];
                await guidelineTypeAPI.createType({
                    ...values,
                    color: randomColor
                });
                showToast.success("Guideline type created successfully");
            }
            gTypeForm.resetFields();
            setEditingGType(null);
            fetchGuidelineTypes();
        } catch (error) {
            console.error("Failed to save guideline type", error);
        } finally {
            setGTypeSubmitting(false);
        }
    };

    const handleGTypeFormCancel = () => {
        gTypeForm.resetFields();
        setEditingGType(null);
    };

    const GTYPE_COLORS = ["blue", "green", "purple", "orange", "red", "cyan", "magenta", "gold"];

    const mainCategoryFilters = useMemo(() => {
        const categories = [...new Set(parameters.map(p => p.category))].filter(Boolean);
        return categories.sort().map(cat => ({ text: cat, value: cat }));
    }, [parameters]);

    const mainSubcategoryFilters = useMemo(() => {
        const subcats = [...new Set(parameters.map(p => p.subcategory))].filter(Boolean);
        return subcats.sort().map(sub => ({ text: sub, value: sub }));
    }, [parameters]);

    const mainParameterFilters = useMemo(() => {
        const parms = [...new Set(parameters.map(p => p.parameter))].filter(Boolean);
        return parms.sort().map(p => ({ text: p, value: p }));
    }, [parameters]);

    const columns = useMemo(() => [
        {
            title: "Parameter Name",
            dataIndex: "parameter",
            key: "parameter",
            sorter: true,
            filters: mainParameterFilters,
            filterSearch: true,
            filteredValue: tableParams.filters?.parameter || null,
            filterIcon: (filtered) => <FilterFilled style={{ color: filtered ? '#3b82f6' : undefined }} />,
            render: (text) => <span className="font-semibold text-gray-800">{text}</span>
        },
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            sorter: true,
            filters: mainCategoryFilters,
            filterSearch: true,
            filteredValue: tableParams.filters?.category || null,
            filterIcon: (filtered) => <FilterFilled style={{ color: filtered ? '#3b82f6' : undefined }} />,
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
            sorter: true,
            filters: mainSubcategoryFilters,
            filterSearch: true,
            filteredValue: tableParams.filters?.subcategory || null,
            filterIcon: (filtered) => <FilterFilled style={{ color: filtered ? '#3b82f6' : undefined }} />,
            render: (text) => <span className="text-gray-600">{text || "—"}</span>
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 250,
            sorter: true,
            filters: guidelineTypes.map(t => ({ text: t.name, value: t.name })),
            filteredValue: tableParams.filters?.guideline_type || null,
            filterIcon: (filtered) => <FilterFilled style={{ color: filtered ? '#3b82f6' : undefined }} />,
            render: (types) => {
                let displayTypes = types || guidelineTypes.map(t => t.name);
                if (displayTypes.includes("All")) {
                    displayTypes = guidelineTypes.map(t => t.name);
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
                            onConfirm={() => handleDelete(record)}
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
    ], [mainCategoryFilters, mainSubcategoryFilters, mainParameterFilters, handleEdit, handleDelete, guidelineTypeColorMap, guidelineTypes]);

    // Calculate stats
    const { totalParams, breakdown } = useMemo(() => {
        // If we have breakdown from server, use it
        if (Object.keys(serverBreakdown).length > 0) {
            return {
                totalParams: total,
                breakdown: guidelineTypes.map(t => ({
                    name: t.name,
                    count: serverBreakdown[t.name] || 0,
                    color: t.color || "blue"
                }))
            };
        }

        // Fallback to local calculation if server breakdown is missing (e.g. during loading or error)
        return {
            totalParams: total || parameters.length,
            breakdown: guidelineTypes.map(t => ({
                name: t.name,
                count: parameters.filter(p => {
                    let types = p.guideline_type || guidelineTypes.map(gt => gt.name);
                    if (typeof types === 'string') types = [types];
                    if (types.includes("All")) types = guidelineTypes.map(gt => gt.name);
                    return types.includes(t.name);
                }).length,
                color: t.color || "blue"
            }))
        };
    }, [parameters, total, serverBreakdown, guidelineTypes]);

    const activeContextName = investors.find(inv => inv.id === selectedInvestorId)?.name || "Unknown";

    return (
        <div className="max-w-7xl mx-auto pb-10">
            {/* Header / Investor Filter Bar */}
            <div className="mb-8">
                <div className="bg-white p-2 md:p-3 rounded-2xl shadow-sm border border-gray-100 w-full lg:w-1/2 flex items-center gap-4 transition-all hover:bg-white/80">
                    <span className="text-gray-500 font-semibold text-sm flex items-center gap-2 ml-2 whitespace-nowrap uppercase tracking-wider">
                        <DatabaseOutlined className="text-blue-500 text-lg" /> Active Investor
                    </span>
                    <Select
                        value={selectedInvestorId}
                        onChange={(val) => setSelectedInvestorId(val)}
                        className="bg-gray-50 rounded-xl investor-select flex-1"
                        size="large"
                        bordered={false}
                        options={[
                            ...investors.map(inv => ({ label: <span className="font-medium text-gray-700">{inv.name}</span>, value: inv.id }))
                        ]}
                    />
                    {isAdmin && (
                        <Tooltip title="Manage Investors">
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
            <Row gutter={[24, 24]} className="mb-8 items-stretch">
                <Col xs={24} md={8}>
                    <Card
                        className="shadow-sm border-gray-100 rounded-2xl hover:shadow-md transition-all duration-300 h-full overflow-hidden"
                        bodyStyle={{ padding: '24px', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
                    >
                        <Statistic
                            title={
                                <span className="text-gray-400 font-semibold flex items-center gap-2 mb-1 text-xs uppercase tracking-widest">
                                    <AppstoreOutlined className="text-blue-500" /> Total Parameters
                                </span>
                            }
                            value={totalParams}
                            valueStyle={{ color: '#0f172a', fontWeight: 700, fontSize: '32px', lineHeight: 1 }}
                            formatter={(val) => loading ? <Skeleton.Button active size="small" style={{ width: "80px", height: "32px", borderRadius: "8px" }} /> : val}
                        />
                    </Card>
                </Col>
                <Col xs={24} md={16}>
                    <Card
                        className="shadow-sm border-gray-100 rounded-2xl hover:shadow-md transition-all duration-300 h-full overflow-hidden"
                        bodyStyle={{ padding: '24px', height: '100%' }}
                    >
                        <div className="flex flex-col h-full">
                            <span className="text-gray-400 font-semibold flex items-center gap-2 mb-4 text-xs uppercase tracking-widest">
                                <TagsOutlined className="text-indigo-500" /> Types Breakdown
                            </span>
                            <div className="flex flex-wrap gap-x-10 gap-y-6 items-center">
                                {breakdown.map((item) => (
                                    <div key={item.name} className="flex flex-col min-w-[100px]">
                                        <span className="text-[10px] font-bold uppercase tracking-[0.1em] mb-2" style={{ color: item.color }}>
                                            {item.name}
                                        </span>
                                        <div className="flex items-baseline gap-1.5">
                                            {loading ? (
                                                <Skeleton.Button active size="small" style={{ width: "40px", height: "28px", borderRadius: "6px" }} />
                                            ) : (
                                                <span className="text-2xl font-bold text-slate-800 tracking-tight leading-none">
                                                    {item.count}
                                                </span>
                                            )}
                                            <span className="text-[11px] text-gray-400 font-medium uppercase">units</span>
                                        </div>
                                    </div>
                                ))}
                                {breakdown.length === 0 && !loading && (
                                    <span className="text-gray-400 italic text-sm">No types defined</span>
                                )}
                            </div>
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Main Content Area */}
            <Card className="shadow-sm border-gray-200 rounded-2xl overflow-hidden" bordered={false} bodyStyle={{ padding: 0 }}>
                {/* Table Header Controls */}
                <div className="p-5 border-b border-gray-100 bg-white flex flex-col xl:flex-row justify-between xl:items-center gap-4">
                    <div className="relative flex-1 max-w-xl">
                        <SearchInput onSearch={setSearchText} value={searchText} />
                    </div>
                    <div className="flex flex-wrap gap-3 items-center">
                        <Tooltip title="Reset all filters and search">
                            <Button
                                icon={<ReloadOutlined />}
                                onClick={handleClearFilters}
                                className="rounded-lg border-gray-200 text-gray-500 hover:text-blue-600 hover:border-blue-300 transition-all"
                            />
                        </Tooltip>
                        {selectedInvestorId && (
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
                            title="Delete all matching parameters?"
                            description={
                                (debouncedSearchText || tableParams.filters)
                                    ? "Are you sure you want to delete ALL parameters matching the current filters across all pages?"
                                    : `Are you sure you want to delete ALL parameters for the selected investor?`
                            }
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
                        <TableSkeleton rows={8} columns={5} showHeader={false} />
                    </div>
                ) : (
                    <div className="p-6 animate-fade-in">
                        <OptimizedTable
                            columns={columns}
                            dataSource={parameters}
                            loading={loading}
                            total={total}
                            current={tableParams.pagination.current}
                            pageSize={tableParams.pagination.pageSize}
                            onChange={handleTableChange}
                            scroll={{ y: 600 }}
                        />
                    </div>
                )}
            </Card>

            {/* Parameter Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-gray-800 text-lg font-semibold">
                        {editingParam ? <EditOutlined className="text-blue-500" /> : <PlusOutlined className="text-blue-500" />}
                        {editingParam ? "Edit Parameter" : "Add New Parameter"}
                    </div>
                }
                open={isModalVisible}
                onOk={editingParam || activeTab === "single" ? handleModalOk : handleBulkUploadSubmit}
                onCancel={() => {
                    setIsModalVisible(false);
                    setActiveTab("single");
                    setExcelFile(null);
                }}
                okText={editingParam ? "Update Parameter" : (activeTab === "single" ? "Create Parameter" : "Import Parameters")}
                destroyOnClose
                centered
                maskClosable={false}
                width={650}
                className="parameter-modal"
                okButtonProps={{
                    className: "bg-blue-600 rounded-lg font-medium shadow-sm h-10 px-6",
                    loading: activeTab === "bulk" && bulkUploading,
                    disabled: activeTab === "bulk" && !excelFile
                }}
                cancelButtonProps={{ className: "rounded-lg h-10 px-6" }}
            >
                {editingParam ? (
                    <Form
                        form={form}
                        layout="vertical"
                        className="mt-6"
                        requiredMark={false}
                    >
                        <Form.Item
                            name="parameter"
                            label={<span className="font-medium text-gray-700">Parameter Name</span>}
                            rules={[{ required: true, message: "Please enter parameter name" }]}
                        >
                            <Input placeholder="e.g. Credit Score Requirements" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                        </Form.Item>

                        <div className="grid grid-cols-2 gap-5 mt-2">
                            <Form.Item
                                name="category"
                                label={<span className="font-medium text-gray-700">Category</span>}
                                rules={[{ required: true, message: "Please enter category" }]}
                            >
                                <Input placeholder="e.g. Credit / Housing" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                            </Form.Item>

                            <Form.Item
                                name="subcategory"
                                label={<span className="font-medium text-gray-700">Subcategory</span>}
                                initialValue="Feature Eligibility"
                            >
                                <Input placeholder="Optional" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                            </Form.Item>
                        </div>

                        <Form.Item
                            name="guideline_type"
                            label={<span className="font-medium text-gray-700">Guideline Compatibility</span>}
                            rules={[{ required: true, message: "Please select at least one guideline type" }]}
                            className="mt-2 mb-0"
                        >
                            <Checkbox.Group
                                onChange={handleGuidelineTypeChange}
                                className="w-full bg-gray-50 p-4 rounded-xl border border-gray-100"
                            >
                                <div className="flex gap-6 flex-wrap">
                                    {guidelineTypes.map(type => (
                                        <Checkbox key={type.id} value={type.name}>
                                            <span className="text-gray-700 font-medium ml-1">{type.name}</span>
                                        </Checkbox>
                                    ))}
                                </div>
                            </Checkbox.Group>
                        </Form.Item>
                    </Form>
                ) : (
                    <Tabs
                        activeKey={activeTab}
                        onChange={(key) => setActiveTab(key)}
                        className="mt-2"
                        items={[
                            {
                                key: "single",
                                label: (
                                    <span className="font-semibold px-2">Single Parameter</span>
                                ),
                                children: (
                                    <Form
                                        form={form}
                                        layout="vertical"
                                        className="mt-4"
                                        requiredMark={false}
                                    >
                                        <Form.Item
                                            name="parameter"
                                            label={<span className="font-medium text-gray-700">Parameter Name</span>}
                                            rules={[{ required: true, message: "Please enter parameter name" }]}
                                        >
                                            <Input placeholder="e.g. Credit Score Requirements" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                                        </Form.Item>

                                        <div className="grid grid-cols-2 gap-5 mt-2">
                                            <Form.Item
                                                name="category"
                                                label={<span className="font-medium text-gray-700">Category</span>}
                                                rules={[{ required: true, message: "Please enter category" }]}
                                            >
                                                <Input placeholder="e.g. Credit / Housing" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                                            </Form.Item>

                                            <Form.Item
                                                name="subcategory"
                                                label={<span className="font-medium text-gray-700">Subcategory</span>}
                                                initialValue="Feature Eligibility"
                                            >
                                                <Input placeholder="Optional" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                                            </Form.Item>
                                        </div>

                                        <Form.Item
                                            name="guideline_type"
                                            label={<span className="font-medium text-gray-700">Guideline Compatibility</span>}
                                            rules={[{ required: true, message: "Please select at least one guideline type" }]}
                                            className="mt-2 mb-0"
                                        >
                                            <Checkbox.Group
                                                onChange={handleGuidelineTypeChange}
                                                className="w-full bg-gray-50 p-4 rounded-xl border border-gray-100"
                                            >
                                                <div className="flex gap-6 flex-wrap">
                                                    {guidelineTypes.map(type => (
                                                        <Checkbox key={type.id} value={type.name}>
                                                            <span className="text-gray-700 font-medium ml-1">{type.name}</span>
                                                        </Checkbox>
                                                    ))}
                                                </div>
                                            </Checkbox.Group>
                                        </Form.Item>
                                    </Form>
                                )
                            },
                            {
                                key: "bulk",
                                label: (
                                    <span className="font-semibold px-2">Bulk Import</span>
                                ),
                                children: (
                                    <div className="mt-4 flex flex-col gap-5">
                                        <div className="bg-blue-50/60 p-4 rounded-2xl border border-blue-100 text-slate-700">
                                            <h4 className="font-bold text-blue-800 text-sm mb-2 flex items-center gap-1.5">
                                                <FileExcelOutlined className="text-base" /> File Requirements
                                            </h4>
                                            <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-600 font-medium">
                                                <li>File format must be <strong>.xlsx</strong> or <strong>.xls</strong>.</li>
                                                <li>The first 4 columns must follow this exact order:</li>
                                                <div className="flex gap-2 my-2 flex-wrap">
                                                    {["parameters", "Category", "sub-Catagories", "guideline type"].map((h, i) => (
                                                        <Tag key={h} className="bg-white border-slate-200 px-2 py-0.5 rounded text-xs font-semibold text-slate-700">
                                                            Col {i + 1}: {h}
                                                        </Tag>
                                                    ))}
                                                </div>
                                                <li>Empty rows or rows missing parameters/category values will be skipped automatically.</li>
                                            </ul>
                                        </div>

                                        <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-2xl p-8 bg-slate-50 hover:bg-slate-50/50 transition-all cursor-pointer relative group min-h-[180px]">
                                            <input
                                                type="file"
                                                accept=".xlsx, .xls"
                                                onChange={handleExcelFileChange}
                                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                            />
                                            <div className="text-center flex flex-col items-center gap-3">
                                                {excelFile ? (
                                                    <>
                                                        <FileExcelOutlined className="text-5xl text-green-500 animate-bounce" />
                                                        <div className="flex flex-col items-center">
                                                            <span className="font-bold text-slate-800 text-sm">{excelFile.name}</span>
                                                            <span className="text-xs text-slate-400 mt-0.5">{(excelFile.size / 1024).toFixed(1)} KB</span>
                                                            <Button
                                                                type="text"
                                                                danger
                                                                size="small"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setExcelFile(null);
                                                                }}
                                                                className="mt-3 font-semibold hover:bg-red-50 px-3 rounded-lg z-20"
                                                            >
                                                                Remove File
                                                            </Button>
                                                        </div>
                                                    </>
                                                ) : (
                                                    <>
                                                        <InboxOutlined className="text-5xl text-slate-400 group-hover:text-blue-500 transition-colors" />
                                                        <div className="flex flex-col">
                                                            <span className="font-bold text-slate-700 text-sm">Click or drag Excel file here</span>
                                                            <span className="text-xs text-slate-400 mt-1 font-medium">Supports .xlsx, .xls up to 10MB</span>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )
                            }
                        ]}
                    />
                )}
            </Modal>

            {/* Import from General Parameters Modal */}
            <ImportGeneralParamsModal
                open={isImportModalVisible}
                onClose={() => setIsImportModalVisible(false)}
                investorId={selectedInvestorId}
                investorName={activeContextName}
                onSuccess={() => {
                    setIsImportModalVisible(false);
                    fetchParameters();
                }}
                guidelineTypes={guidelineTypes}
                guidelineTypeColorMap={guidelineTypeColorMap}
            />


            <Modal
                title={
                    <div className="flex items-center gap-2 text-gray-800 text-lg font-semibold">
                        <TeamOutlined className="text-blue-500" />
                        Manage Investors & Types
                    </div>
                }
                open={isManageInvestorsVisible}
                onCancel={handleManageInvestorsClose}
                footer={null}
                width={550}
                destroyOnClose
                centered
            >
                <Tabs
                    defaultActiveKey="investors"
                    className="manage-tabs"
                    items={[
                        {
                            key: "investors",
                            label: (
                                <span className="flex items-center gap-2">
                                    <TeamOutlined /> Investors
                                </span>
                            ),
                            children: (
                                <>
                                    <div className="mb-6 mt-4">
                                        <div className="bg-blue-50/50 p-5 rounded-xl border border-blue-100">
                                            <span className="text-sm tracking-wide uppercase text-blue-600 font-bold mb-3 block">
                                                {editingInvestor ? "Edit Investor" : "Add New Investor"}
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
                                                    <Input placeholder="e.g. Rocket Mortgage" className="h-10 rounded-lg" />
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
                                        <span className="text-sm tracking-wide uppercase text-gray-500 font-bold">Existing Contexts</span>
                                        <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs font-semibold">{investors.length} Total</span>
                                    </div>

                                    <div className="max-h-72 overflow-y-auto border border-gray-100 rounded-xl">
                                        {investors.length === 0 ? (
                                            <div className="text-center py-10 bg-gray-50">
                                                <DatabaseOutlined className="text-3xl text-gray-300 mb-2 block mx-auto" />
                                                <div className="text-gray-400 font-medium">No contexts added yet</div>
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
                                                        render: (text) => <span className="font-semibold text-gray-700">{text}</span>
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
                                </>
                            )
                        },
                        {
                            key: "types",
                            label: (
                                <span className="flex items-center gap-2">
                                    <TagsOutlined /> Guideline Types
                                </span>
                            ),
                            children: (
                                <>
                                    <div className="mb-6 mt-4">
                                        <div className="bg-blue-50/50 p-5 rounded-xl border border-blue-100">
                                            <span className="text-sm tracking-wide uppercase text-blue-600 font-bold mb-3 block">
                                                {editingGType ? "Edit Guideline Type" : "Add New Guideline Type"}
                                            </span>
                                            <Form
                                                form={gTypeForm}
                                                layout="inline"
                                                onFinish={handleGTypeSubmit}
                                                className="flex items-start w-full gap-2"
                                            >
                                                <Form.Item
                                                    name="name"
                                                    rules={[{ required: true, message: 'Name is required' }]}
                                                    className="flex-grow m-0"
                                                >
                                                    <Input placeholder="Type Name (e.g. DSCR)" className="h-10 rounded-lg" />
                                                </Form.Item>
                                                <div className="flex gap-2">
                                                    <Button type="primary" htmlType="submit" loading={gTypeSubmitting} className="h-10 px-6 rounded-lg font-medium shadow-sm bg-purple-600 hover:bg-purple-700 border-none">
                                                        {editingGType ? "Update" : "Add"}
                                                    </Button>
                                                    {editingGType && (
                                                        <Button onClick={handleGTypeFormCancel} className="h-10 px-4 rounded-lg">
                                                            Cancel
                                                        </Button>
                                                    )}
                                                </div>
                                            </Form>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between mb-3 mt-8">
                                        <span className="text-sm tracking-wide uppercase text-gray-500 font-bold">Existing Types</span>
                                        <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs font-semibold">{guidelineTypes.length} Total</span>
                                    </div>

                                    <div className="max-h-72 overflow-y-auto border border-gray-100 rounded-xl">
                                        <Table
                                            size="middle"
                                            dataSource={guidelineTypes}
                                            rowKey="id"
                                            pagination={false}
                                            className="border-0"
                                            loading={guidelineTypesLoading}
                                            columns={[
                                                {
                                                    title: "Type",
                                                    key: "name",
                                                    render: (_, record) => (
                                                        <Space>
                                                            <Tag color={record.color || "blue"} className="rounded-full px-3">{record.name}</Tag>
                                                        </Space>
                                                    )
                                                },
                                                {
                                                    title: "Actions",
                                                    key: "actions",
                                                    width: 120,
                                                    align: 'right',
                                                    render: (_, record) => (
                                                        <Space size="small">
                                                            <Tooltip title="Edit Type">
                                                                <Button
                                                                    type="text"
                                                                    icon={<EditOutlined className="text-gray-400 hover:text-blue-500" />}
                                                                    onClick={() => handleGTypeEdit(record)}
                                                                />
                                                            </Tooltip>
                                                            <Tooltip title="Delete Type">
                                                                <Popconfirm
                                                                    title="Delete type?"
                                                                    description="Cannot delete if types are linked to parameters."
                                                                    onConfirm={() => handleGTypeDelete(record.id)}
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
                                    </div>
                                </>
                            )
                        }
                    ]}
                />
            </Modal>
        </div>
    );
};

// Sub-component to isolate search state and prevent re-rendering the whole page on every keystroke
const ImportGeneralParamsModal = memo(({ open, onClose, investorId, investorName, onSuccess, guidelineTypes, guidelineTypeColorMap }) => {
    const [generalParams, setGeneralParams] = useState([]);
    const [generalTotal, setGeneralTotal] = useState(0);
    const [generalTableParams, setGeneralTableParams] = useState({
        pagination: { current: 1, pageSize: 12 },
        filters: null,
        sortField: null,
        sortOrder: null,
    });
    const [selectedParamIds, setSelectedParamIds] = useState([]);
    const [importLoading, setImportLoading] = useState(false);
    const [importSearchText, setImportSearchText] = useState("");
    const [debouncedImportSearchText, setDebouncedImportSearchText] = useState("");
    const [generalParamsLoading, setGeneralParamsLoading] = useState(false);
    const [fetchingIds, setFetchingIds] = useState(false);
    const [isAddGeneralModalVisible, setIsAddGeneralModalVisible] = useState(false);
    const [generalForm] = Form.useForm();

    const [activeTab, setActiveTab] = useState("single");
    const [excelFile, setExcelFile] = useState(null);
    const [bulkUploading, setBulkUploading] = useState(false);

    const handleExcelFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (ext !== 'xlsx' && ext !== 'xls') {
                showToast.error("Only Excel files (.xlsx, .xls) are allowed");
                setExcelFile(null);
                return;
            }
            setExcelFile(file);
        }
    };

    const handleBulkUploadSubmit = async () => {
        if (!excelFile) {
            showToast.warning("Please upload an Excel file first");
            return;
        }

        const formData = new FormData();
        formData.append("file", excelFile);

        setBulkUploading(true);
        try {
            const response = await dscrAPI.bulkUploadGeneralParameters(formData);
            showToast.success(response.data.message || "Excel file uploaded and imported successfully");

            // Clean up states
            setExcelFile(null);
            setActiveTab("single");
            setIsAddGeneralModalVisible(false);

            // Refresh list
            fetchGeneralParameters();
        } catch (error) {
            console.error("Bulk upload failed:", error);
        } finally {
            setBulkUploading(false);
        }
    };

    // Responsive height calculation
    const [scrollY, setScrollY] = useState(450);

    useEffect(() => {
        const updateHeight = () => {
            const h = window.innerHeight;
            // 100vh - (Header + Control Bar + Pagination + Modal Padding)
            setScrollY(Math.max(300, h - 420));
        };
        updateHeight();
        window.addEventListener('resize', updateHeight);
        return () => window.removeEventListener('resize', updateHeight);
    }, []);

    // Debounce search text
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedImportSearchText(importSearchText);
        }, 500);
        return () => clearTimeout(timer);
    }, [importSearchText]);

    // Reset selection and params when modal opens
    useEffect(() => {
        if (open) {
            setSelectedParamIds([]);
            setImportSearchText("");
            setGeneralTableParams({
                pagination: { current: 1, pageSize: 10 },
                filters: null,
                sortField: null,
                sortOrder: null,
            });
        }
    }, [open]);

    const fetchGeneralParameters = useCallback(async () => {
        if (!open) return;

        setGeneralParamsLoading(true);
        try {
            const params = {
                page: generalTableParams.pagination.current,
                pageSize: generalTableParams.pagination.pageSize,
                search: debouncedImportSearchText,
                sortField: generalTableParams.sortField,
                sortOrder: generalTableParams.sortOrder,
                filters: generalTableParams.filters ? JSON.stringify(generalTableParams.filters) : undefined
            };
            const response = await dscrAPI.listParameters("null", params);
            setGeneralParams(response.data.items || []);
            setGeneralTotal(response.data.total || 0);
        } catch (error) {
            console.error("Failed to fetch general parameters:", error);
            showToast.error("Failed to load general parameters");
        } finally {
            setGeneralParamsLoading(false);
        }
    }, [open, generalTableParams, debouncedImportSearchText]);

    useEffect(() => {
        // Delay fetch slightly to allow modal animation to complete smoothly
        const timer = setTimeout(() => {
            fetchGeneralParameters();
        }, 100);
        return () => clearTimeout(timer);
    }, [fetchGeneralParameters]);

    const handleImportParams = async () => {
        if (selectedParamIds.length === 0) {
            showToast.warning("Please select at least one parameter to import.");
            return;
        }
        setImportLoading(true);
        try {
            await dscrAPI.importFromGeneral({
                parameter_ids: selectedParamIds,
                target_investor_id: investorId
            });
            showToast.success(`${selectedParamIds.length} parameter(s) imported successfully.`);
            onSuccess();
        } catch (error) {
            console.error("Failed to import parameters:", error);
        } finally {
            setImportLoading(false);
        }
    };

    const handleOpenAddGeneral = () => {
        generalForm.resetFields();
        const defaultType = guidelineTypes.map(t => t.name);
        generalForm.setFieldsValue({ guideline_type: defaultType });
        setIsAddGeneralModalVisible(true);
    };

    const handleAddGeneralOk = async () => {
        try {
            const values = await generalForm.validateFields();
            // No investor_id means it's a general parameter
            await dscrAPI.createParameter(values);
            showToast.success("General parameter created successfully");
            setIsAddGeneralModalVisible(false);
            fetchGeneralParameters(); // Refresh the list
        } catch (error) {
            console.error("Failed to save general parameter:", error);
        }
    };

    const handleSelectAll = async (checked) => {
        if (checked) {
            setFetchingIds(true);
            try {
                const params = {
                    search: debouncedImportSearchText,
                    filters: generalTableParams.filters ? JSON.stringify(generalTableParams.filters) : undefined
                };
                const response = await dscrAPI.getParameterIds(params);
                setSelectedParamIds(response.data || []);
            } catch (error) {
                console.error("Failed to fetch all parameter IDs:", error);
                showToast.error("Failed to select all records");
            } finally {
                setFetchingIds(false);
            }
        } else {
            setSelectedParamIds([]);
        }
    };

    const handleTableChange = (pagination, filters, sorter) => {
        setGeneralTableParams({
            pagination,
            filters,
            sortField: sorter.field,
            sortOrder: sorter.order,
        });
    };

    const categoryFilters = useMemo(() => {
        const categories = [...new Set(generalParams.map(p => p.category))].filter(Boolean);
        return categories.sort().map(cat => ({ text: cat, value: cat }));
    }, [generalParams]);

    const subcategoryFilters = useMemo(() => {
        const subcats = [...new Set(generalParams.map(p => p.subcategory))].filter(Boolean);
        return subcats.sort().map(sub => ({ text: sub, value: sub }));
    }, [generalParams]);

    const parameterFilters = useMemo(() => {
        const parms = [...new Set(generalParams.map(p => p.parameter))].filter(Boolean);
        return parms.sort().map(p => ({ text: p, value: p }));
    }, [generalParams]);

    const importColumns = useMemo(() => [
        {
            title: "Parameter Name",
            dataIndex: "parameter",
            key: "parameter",
            sorter: true,
            filters: parameterFilters,
            filterSearch: true,
            render: (text) => <span className="font-semibold text-gray-800 text-sm">{text}</span>
        },
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            sorter: true,
            filters: categoryFilters,
            filterSearch: true,
            render: (text) => (
                <Tag color="processing" className="text-[11px] px-2 rounded-full border-transparent bg-blue-50 text-blue-600">
                    {text}
                </Tag>
            )
        },
        {
            title: "Sub Category",
            dataIndex: "subcategory",
            key: "subcategory",
            sorter: true,
            filters: subcategoryFilters,
            filterSearch: true,
            render: (text) => <span className="text-[11px] text-gray-500">{text || "—"}</span>
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 180,
            sorter: true,
            filters: guidelineTypes.map(t => ({ text: t.name, value: t.name })),
            render: (types) => {
                let displayTypes = types || guidelineTypes.map(t => t.name);
                if (displayTypes.includes("All")) {
                    displayTypes = guidelineTypes.map(t => t.name);
                }
                return (
                    <Space size={[0, 4]} wrap>
                        {displayTypes.map(t => (
                            <Tag
                                key={t}
                                color={guidelineTypeColorMap[t] || "default"}
                                className="text-[10px] px-2 rounded-full border-transparent m-0"
                            >
                                {t}
                            </Tag>
                        ))}
                    </Space>
                );
            }
        }
    ], [categoryFilters, subcategoryFilters, parameterFilters, guidelineTypes, guidelineTypeColorMap]);

    return (
        <Modal
            title={
                <div className="relative overflow-hidden -mx-6 -mt-5 mb-4 px-6 py-5 bg-gradient-to-r from-slate-50 to-blue-50/30 border-b border-gray-100">
                    <div className="relative z-10">
                        <div className="flex items-center gap-3 text-slate-800 text-xl font-bold tracking-tight">
                            <div className="flex flex-col">
                                <span>Import from General Parameters</span>
                                <span className="text-slate-400 text-xs font-medium uppercase tracking-widest mt-0.5">
                                    Selected Investor: <span className="text-blue-600 font-bold">{investorName}</span>
                                </span>
                            </div>
                        </div>
                    </div>
                    {/* Decorative element */}
                    <div className="absolute top-[-20px] right-[-20px] w-32 h-32 bg-blue-100/20 rounded-full blur-3xl"></div>
                </div>
            }
            open={open}
            onCancel={onClose}
            onOk={handleImportParams}
            okText={`Import ${selectedParamIds.length} Selected`}
            okButtonProps={{
                className: "bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-xl font-bold shadow-lg shadow-blue-100 h-12 px-10 border-none transition-all",
                loading: importLoading,
                disabled: selectedParamIds.length === 0,
            }}
            cancelButtonProps={{
                className: "rounded-xl h-12 px-8 border-gray-200 font-semibold hover:border-blue-300 hover:text-blue-600 transition-all"
            }}
            centered
            destroyOnClose
            maskClosable={false}
            width="92vw"
            className="premium-modal"
            style={{ maxWidth: '1600px', top: 20 }}
            styles={{ body: { padding: '0 24px 20px 24px' } }}
        >
            <div className="flex flex-col gap-6">
                {/* Search and Selection Control Bar */}
                <div className="bg-white p-2 rounded-2xl border border-gray-100 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4 transition-all hover:shadow-md">
                    <div className="flex-1 w-full md:max-w-md">
                        <SearchInput
                            placeholder="Find parameters to import..."
                            onSearch={setImportSearchText}
                            className="h-12 rounded-xl bg-slate-50 border-transparent focus:bg-white hover:bg-slate-100/50 transition-all pl-5 w-full font-medium"
                        />
                    </div>

                    <div className="flex items-center gap-3 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
                        <Button
                            icon={<PlusOutlined />}
                            onClick={handleOpenAddGeneral}
                            className="h-11 rounded-xl bg-blue-50 text-blue-600 border-blue-100 hover:bg-blue-100 font-bold px-5 transition-all"
                        >
                            General Parameter
                        </Button>

                        <div className="flex items-center bg-slate-50 px-5 py-2.5 rounded-xl border border-slate-100 shadow-inner group">
                            <Checkbox
                                indeterminate={selectedParamIds.length > 0 && selectedParamIds.length < generalTotal}
                                checked={generalTotal > 0 && selectedParamIds.length === generalTotal}
                                onChange={e => handleSelectAll(e.target.checked)}
                                className="custom-checkbox pointer-events-auto"
                                disabled={fetchingIds}
                            >
                                <span className="text-slate-600 font-bold ml-1 text-sm whitespace-nowrap">
                                    {fetchingIds ? <ReloadOutlined spin className="mr-2 text-blue-500" /> : null}
                                    Select All ({generalTotal})
                                </span>
                            </Checkbox>

                            <Divider type="vertical" className="mx-4 h-6 border-slate-200" />

                            <div className="flex items-baseline gap-1.5 px-1">
                                <span className={`text-xl font-black transition-all ${selectedParamIds.length > 0 ? 'text-blue-600 scale-110' : 'text-slate-300'}`}>
                                    {selectedParamIds.length}
                                </span>
                                <span className="text-slate-400 text-[9px] uppercase font-black tracking-[0.15em]">Selected</span>
                            </div>
                        </div>

                        {selectedParamIds.length > 0 && (
                            <Button
                                type="text"
                                onClick={() => setSelectedParamIds([])}
                                className="text-slate-400 hover:text-red-500 hover:bg-red-50 font-bold px-4 rounded-xl transition-all h-11"
                            >
                                Clear
                            </Button>
                        )}
                    </div>
                </div>

                {/* Parameter list */}
                <div className="relative border border-slate-100 rounded-2xl overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)] bg-white group">
                    <OptimizedTable
                        columns={importColumns}
                        dataSource={generalParams}
                        loading={generalParamsLoading}
                        total={generalTotal}
                        current={generalTableParams.pagination.current}
                        pageSize={generalTableParams.pagination.pageSize}
                        onChange={handleTableChange}
                        rowSelection={{
                            selectedRowKeys: selectedParamIds,
                            onChange: (keys) => setSelectedParamIds(keys),
                            preserveSelectedRowKeys: true,
                            columnWidth: 60
                        }}
                        scroll={{ y: scrollY }}
                        size="middle"
                        rowClassName={(record) => {
                            const isSelected = selectedParamIds.includes(record.id);
                            return `cursor-pointer transition-all duration-200 ${isSelected
                                ? "bg-blue-50/80 hover:bg-blue-100/80"
                                : "hover:bg-slate-50/80"
                                }`;
                        }}
                    />

                    {/* Footer Progress Overlay (for large selections) */}
                    {fetchingIds && (
                        <div className="absolute inset-x-0 bottom-0 top-0 bg-white/40 backdrop-blur-[1px] z-10 flex items-center justify-center">
                            <div className="bg-white p-5 rounded-2xl shadow-xl border border-blue-50 flex items-center gap-4">
                                <ReloadOutlined spin className="text-blue-600 text-xl" />
                                <span className="text-slate-700 font-bold">Synchronizing selection...</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Add General Parameter Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-gray-800 text-lg font-semibold">
                        <PlusOutlined className="text-blue-500" />
                        Add New General Parameter
                    </div>
                }
                open={isAddGeneralModalVisible}
                onOk={activeTab === "single" ? handleAddGeneralOk : handleBulkUploadSubmit}
                onCancel={() => {
                    setIsAddGeneralModalVisible(false);
                    setActiveTab("single");
                    setExcelFile(null);
                }}
                okText={activeTab === "single" ? "Create Parameter" : "Import Parameters"}
                destroyOnClose
                centered
                maskClosable={false}
                width={650}
                className="parameter-modal"
                okButtonProps={{
                    className: "bg-blue-600 rounded-lg font-medium shadow-sm h-10 px-6",
                    loading: activeTab === "bulk" && bulkUploading,
                    disabled: activeTab === "bulk" && !excelFile
                }}
                cancelButtonProps={{ className: "rounded-lg h-10 px-6" }}
            >
                <Tabs
                    activeKey={activeTab}
                    onChange={(key) => setActiveTab(key)}
                    className="mt-2"
                    items={[
                        {
                            key: "single",
                            label: (
                                <span className="font-semibold px-2">Single Parameter</span>
                            ),
                            children: (
                                <Form
                                    form={generalForm}
                                    layout="vertical"
                                    className="mt-4"
                                    requiredMark={false}
                                >
                                    <Form.Item
                                        name="parameter"
                                        label={<span className="font-medium text-gray-700">Parameter Name</span>}
                                        rules={[{ required: true, message: "Please enter parameter name" }]}
                                    >
                                        <Input placeholder="e.g. Credit Score Requirements" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                                    </Form.Item>

                                    <div className="grid grid-cols-2 gap-5 mt-2">
                                        <Form.Item
                                            name="category"
                                            label={<span className="font-medium text-gray-700">Category</span>}
                                            rules={[{ required: true, message: "Please enter category" }]}
                                        >
                                            <Input placeholder="e.g. Credit / Housing" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                                        </Form.Item>

                                        <Form.Item
                                            name="subcategory"
                                            label={<span className="font-medium text-gray-700">Subcategory</span>}
                                            initialValue="Feature Eligibility"
                                        >
                                            <Input placeholder="Optional" className="h-11 rounded-lg bg-gray-50 focus:bg-white hover:bg-white" />
                                        </Form.Item>
                                    </div>

                                    <Form.Item
                                        name="guideline_type"
                                        label={<span className="font-medium text-gray-700">Guideline Compatibility</span>}
                                        rules={[{ required: true, message: "Please select at least one guideline type" }]}
                                        className="mt-2 mb-0"
                                    >
                                        <Checkbox.Group
                                            className="w-full bg-gray-50 p-4 rounded-xl border border-gray-100"
                                        >
                                            <div className="flex gap-6 flex-wrap">
                                                {guidelineTypes.map(type => (
                                                    <Checkbox key={type.id} value={type.name}>
                                                        <span className="text-gray-700 font-medium ml-1">{type.name}</span>
                                                    </Checkbox>
                                                ))}
                                            </div>
                                        </Checkbox.Group>
                                    </Form.Item>
                                </Form>
                            )
                        },
                        {
                            key: "bulk",
                            label: (
                                <span className="font-semibold px-2">Bulk Import</span>
                            ),
                            children: (
                                <div className="mt-4 flex flex-col gap-5">
                                    <div className="bg-blue-50/60 p-4 rounded-2xl border border-blue-100 text-slate-700">
                                        <h4 className="font-bold text-blue-800 text-sm mb-2 flex items-center gap-1.5">
                                            <FileExcelOutlined className="text-base" /> File Requirements
                                        </h4>
                                        <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-600 font-medium">
                                            <li>File format must be <strong>.xlsx</strong> or <strong>.xls</strong>.</li>
                                            <li>The first 4 columns must follow this exact order:</li>
                                            <div className="flex gap-2 my-2 flex-wrap">
                                                {["parameters", "Category", "sub-Catagories", "guideline type"].map((h, i) => (
                                                    <Tag key={h} className="bg-white border-slate-200 px-2 py-0.5 rounded text-xs font-semibold text-slate-700">
                                                        Col {i + 1}: {h}
                                                    </Tag>
                                                ))}
                                            </div>
                                            <li>Empty rows or rows missing parameters/category values will be skipped automatically.</li>
                                        </ul>
                                    </div>

                                    <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-2xl p-8 bg-slate-50 hover:bg-slate-50/50 transition-all cursor-pointer relative group min-h-[180px]">
                                        <input
                                            type="file"
                                            accept=".xlsx, .xls"
                                            onChange={handleExcelFileChange}
                                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                        />
                                        <div className="text-center flex flex-col items-center gap-3">
                                            {excelFile ? (
                                                <>
                                                    <FileExcelOutlined className="text-5xl text-green-500 animate-bounce" />
                                                    <div className="flex flex-col items-center">
                                                        <span className="font-bold text-slate-800 text-sm">{excelFile.name}</span>
                                                        <span className="text-xs text-slate-400 mt-0.5">{(excelFile.size / 1024).toFixed(1)} KB</span>
                                                        <Button
                                                            type="text"
                                                            danger
                                                            size="small"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setExcelFile(null);
                                                            }}
                                                            className="mt-3 font-semibold hover:bg-red-50 px-3 rounded-lg z-20"
                                                        >
                                                            Remove File
                                                        </Button>
                                                    </div>
                                                </>
                                            ) : (
                                                <>
                                                    <InboxOutlined className="text-5xl text-slate-400 group-hover:text-blue-500 transition-colors" />
                                                    <div className="flex flex-col">
                                                        <span className="font-bold text-slate-700 text-sm">Click or drag Excel file here</span>
                                                        <span className="text-xs text-slate-400 mt-1 font-medium">Supports .xlsx, .xls up to 10MB</span>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )
                        }
                    ]}
                />
            </Modal>
        </Modal>
    );
});

// Sub-component to isolate search state and prevent re-rendering the whole page on every keystroke
const SearchInput = memo(({ onSearch, value = "", placeholder = "Search parameters or categories...", className = "h-11 rounded-xl bg-gray-50 border-transparent focus:bg-white hover:bg-white transition-all duration-200 pl-4" }) => {
    const [innerValue, setInnerValue] = useState(value);

    // Sync inner value with external value prop (e.g. for reset)
    useEffect(() => {
        setInnerValue(value);
    }, [value]);

    const handleChange = (e) => {
        const val = e.target.value;
        setInnerValue(val);
        onSearch(val);
    };

    return (
        <Input
            placeholder={placeholder}
            prefix={<SearchOutlined className="text-gray-400 mr-2" />}
            value={innerValue}
            onChange={handleChange}
            allowClear
            className={className}
        />
    );
});

// Memoized Table to prevent re-renders unless data or columns actually change
const OptimizedTable = memo(({
    loading,
    dataSource,
    columns,
    pagination,
    scroll,
    className = "custom-table",
    rowSelection = null,
    size = "large",
    onChange,
    total,
    current,
    pageSize,
    rowClassName = null
}) => {
    const internalPagination = pagination === false ? false : {
        ...(pagination || {}),
        total: total,
        current: current,
        pageSize: pageSize,
        showSizeChanger: true,
        className: (pagination?.className || "px-6 pb-2")
    };

    return (
        <Table
            loading={loading}
            dataSource={dataSource}
            columns={columns}
            rowKey="id"
            pagination={internalPagination}
            onChange={onChange}
            className={className}
            rowClassName={rowClassName || (() => "hover:bg-blue-50/30 transition-colors cursor-pointer")}
            virtual={false}
            scroll={scroll}
            rowSelection={rowSelection}
            size={size}
            locale={{
                emptyText: (
                    <div className="py-12 text-center">
                        <DatabaseOutlined className="text-4xl text-gray-200 mb-3" />
                        <p className="text-gray-400 font-medium">No records found</p>
                    </div>
                )
            }}
        />
    );
});

export default ConfigParametersPage;
