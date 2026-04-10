import React, { useState, useEffect, useRef, useMemo, useCallback, useDeferredValue, memo } from "react";
import { Table, Card, Button, Modal, Form, Input, Select, Space, Typography, Popconfirm, Tag, Checkbox, Divider, Tooltip, Row, Col, Statistic, Skeleton, Tabs } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, SettingOutlined, AppstoreOutlined, DatabaseOutlined, TagsOutlined, TeamOutlined, DownloadOutlined } from "@ant-design/icons";
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
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingParam, setEditingParam] = useState(null);
    const [form] = Form.useForm();
    const [searchText, setSearchText] = useState("");
    const deferredSearchText = useDeferredValue(searchText);
    const prevGuidelineTypeRef = useRef([]);

    // Investor State
    const [investors, setInvestors] = useState([]);
    const [selectedInvestorId, setSelectedInvestorId] = useState(null);

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
    const deferredImportSearchText = useDeferredValue(importSearchText);
    const [generalParamsLoading, setGeneralParamsLoading] = useState(false);
    const [hasFetchedGeneral, setHasFetchedGeneral] = useState(false);

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
            const response = await guidelineTypeAPI.listTypes();
            setGuidelineTypes(response.data || []);
        } catch (error) {
            console.error("Failed to fetch guideline types:", error);
            showToast.error("Failed to load guideline types");
        } finally {
            setGuidelineTypesLoading(false);
        }
    };

    // Re-fetch parameters whenever the selected investor changes (but NOT on initial null)
    useEffect(() => {
        if (selectedInvestorId) {
            fetchParameters();
        }
    }, [selectedInvestorId]);

    const fetchInvestors = async () => {
        try {
            const response = await investorAPI.listInvestors();
            const data = response.data || [];
            setInvestors(data);
            if (data.length > 0) {
                // Set the first investor — this triggers the selectedInvestorId useEffect
                // which will call fetchParameters(). No manual call needed here.
                setSelectedInvestorId(data[0].id);
            } else {
                // No investors exist — nothing to load
                setSelectedInvestorId(null);
                setLoading(false);
            }
        } catch (error) {
            console.error("Failed to fetch investors:", error);
            showToast.error("Failed to fetch investor list.");
            setLoading(false);
        }
    };

    const fetchParameters = async (investorId = selectedInvestorId) => {
        if (!investorId) return;
        setLoading(true);
        try {
            const response = await dscrAPI.listParameters(investorId);
            setParameters(response.data || []);
        } catch (error) {
            console.error("Failed to fetch parameters:", error);
            showToast.error("Failed to load parameters. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingParam(null);
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

    const handleDelete = useCallback(async (id) => {
        try {
            await dscrAPI.deleteParameter(id);
            showToast.success("Parameter deleted successfully");
            fetchParameters();
        } catch (error) {
            console.error("Failed to delete parameter:", error);
        }
    }, [selectedInvestorId]); // Added dependency to ensure fetchParameters is current

    const handleRemoveAll = async () => {
        try {
            // Delete only the parameters for the currently selected investor,
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

    /* === Import from General Parameters Flow === */
    const fetchGeneralParameters = async (force = false) => {
        if (hasFetchedGeneral && !force && generalParams.length > 0) return;

        setGeneralParamsLoading(true);
        try {
            const response = await dscrAPI.listParameters("null");
            setGeneralParams(response.data || []);
            setHasFetchedGeneral(true);
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
            await dscrAPI.importFromGeneral({
                parameter_ids: selectedParamIds,
                target_investor_id: selectedInvestorId
            });
            showToast.success(`${selectedParamIds.length} parameter(s) imported successfully.`);
            setIsImportModalVisible(false);
            fetchParameters();
        } catch (error) {
            console.error("Failed to import parameters:", error);
        } finally {
            setImportLoading(false);
        }
    };

    const handleSelectAll = (checked) => {
        if (checked) {
            // Add all visible IDs to selection, avoiding duplicates
            const visibleIds = filteredGeneralParams.map(p => p.id);
            setSelectedParamIds(prev => [...new Set([...prev, ...visibleIds])]);
        } else {
            // Remove only visible IDs from selection
            const visibleIds = filteredGeneralParams.map(p => p.id);
            setSelectedParamIds(prev => prev.filter(id => !visibleIds.includes(id)));
        }
    };

    const filteredGeneralParams = useMemo(() => {
        if (!deferredImportSearchText) return generalParams;
        const lowerSearch = deferredImportSearchText.toLowerCase();
        return generalParams.filter(p =>
            p.parameter.toLowerCase().includes(lowerSearch) ||
            p.category.toLowerCase().includes(lowerSearch)
        );
    }, [generalParams, deferredImportSearchText]);

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
            sorter: (a, b) => (a.parameter || "").localeCompare(b.parameter || ""),
            filters: parameterFilters,
            filterSearch: true,
            onFilter: (value, record) => record.parameter === value,
            render: (text) => <span className="font-semibold text-gray-800 text-sm">{text}</span>
        },
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            sorter: (a, b) => (a.category || "").localeCompare(b.category || ""),
            filters: categoryFilters,
            filterSearch: true,
            onFilter: (value, record) => record.category === value,
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
            sorter: (a, b) => (a.subcategory || "").localeCompare(b.subcategory || ""),
            filters: subcategoryFilters,
            filterSearch: true,
            onFilter: (value, record) => record.subcategory === value,
            render: (text) => <span className="text-[11px] text-gray-500">{text || "—"}</span>
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 180,
            sorter: (a, b) => {
                const getLen = (item) => {
                    let types = item.guideline_type || ["DSCR", "Full Doc", "Alt Doc"];
                    if (types.includes("All")) return 3;
                    return (Array.isArray(types) ? types.length : 1);
                };
                return getLen(a) - getLen(b);
            },
            filters: guidelineTypes.map(t => ({ text: t.name, value: t.name })),
            onFilter: (value, record) => {
                let types = record.guideline_type || guidelineTypes.map(t => t.name);
                if (types.includes("All")) {
                    types = guidelineTypes.map(t => t.name);
                }
                return types.includes(value);
            },
            render: (types) => {
                let displayTypes = types || guidelineTypes.map(t => t.name);
                if (displayTypes.includes("All")) {
                    displayTypes = guidelineTypes.map(t => t.name);
                }
                return (
                    <Space size={[0, 4]} wrap>
                        {displayTypes.map(t => {
                            const typeObj = guidelineTypes.find(gt => gt.name === t);
                            const color = typeObj?.color || "default";
                            return (
                                <Tag key={t} color={color} className="text-[10px] px-2 rounded-full border-transparent m-0">
                                    {t}
                                </Tag>
                            );
                        })}
                    </Space>
                );
            }
        }
    ], [categoryFilters, subcategoryFilters]);

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

    const filteredParameters = useMemo(() => parameters.filter(p =>
        p.parameter.toLowerCase().includes(deferredSearchText.toLowerCase()) ||
        p.category.toLowerCase().includes(deferredSearchText.toLowerCase())
    ), [parameters, deferredSearchText]);

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

    const guidelineTypeColorMap = useMemo(() => {
        const map = {};
        guidelineTypes.forEach(t => {
            map[t.name] = t.color || "default";
        });
        return map;
    }, [guidelineTypes]);

    const columns = useMemo(() => [
        {
            title: "Parameter Name",
            dataIndex: "parameter",
            key: "parameter",
            sorter: (a, b) => (a.parameter || "").localeCompare(b.parameter || ""),
            filters: mainParameterFilters,
            filterSearch: true,
            onFilter: (value, record) => record.parameter === value,
            render: (text) => <span className="font-semibold text-gray-800">{text}</span>
        },
        {
            title: "Category",
            dataIndex: "category",
            key: "category",
            sorter: (a, b) => (a.category || "").localeCompare(b.category || ""),
            filters: mainCategoryFilters,
            filterSearch: true,
            onFilter: (value, record) => record.category === value,
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
            sorter: (a, b) => (a.subcategory || "").localeCompare(b.subcategory || ""),
            filters: mainSubcategoryFilters,
            filterSearch: true,
            onFilter: (value, record) => record.subcategory === value,
            render: (text) => <span className="text-gray-600">{text || "—"}</span>
        },
        {
            title: "Guideline Type",
            dataIndex: "guideline_type",
            key: "guideline_type",
            width: 250,
            sorter: (a, b) => {
                const getLen = (item) => {
                    let types = item.guideline_type || ["DSCR", "Full Doc", "Alt Doc"];
                    if (types.includes("All")) return 3;
                    return (Array.isArray(types) ? types.length : 1);
                };
                return getLen(a) - getLen(b);
            },
            filters: guidelineTypes.map(t => ({ text: t.name, value: t.name })),
            onFilter: (value, record) => {
                let types = record.guideline_type || guidelineTypes.map(t => t.name);
                if (types.includes("All")) {
                    types = guidelineTypes.map(t => t.name);
                }
                return types.includes(value);
            },
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
    ], [mainCategoryFilters, mainSubcategoryFilters, mainParameterFilters, handleEdit, handleDelete, guidelineTypeColorMap, guidelineTypes]);

    // Calculate stats
    const { totalParams, breakdown } = useMemo(() => {
        return {
            totalParams: parameters.length,
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
    }, [parameters, guidelineTypes]);

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
                        <SearchInput onSearch={setSearchText} />
                    </div>
                    <div className="flex flex-wrap gap-3 items-center">
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
                            title="Delete all parameters?"
                            description={`Are you sure you want to delete ALL parameters for the selected investor?`}
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
                        <OptimizedTable 
                            columns={columns}
                            dataSource={filteredParameters}
                            pagination={{
                                pageSize: 12,
                                showSizeChanger: true,
                                className: "px-6 pb-2"
                            }}
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
            </Modal>

            {/* Import from General Parameters Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-gray-800 text-lg font-semibold">
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
                centered
                destroyOnClose
                maskClosable={false}
            >
                <div className="mt-4 flex flex-col gap-4">
                    {/* Search and Select All section */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <SearchInput 
                            placeholder="Search general parameters..."
                            onSearch={setImportSearchText}
                            className="h-10 rounded-lg bg-gray-50 border-transparent focus:bg-white flex-1"
                        />
                        <div className="px-1 flex items-center gap-4">
                            <Checkbox
                                indeterminate={
                                    filteredGeneralParams.some(p => selectedParamIds.includes(p.id)) &&
                                    !filteredGeneralParams.every(p => selectedParamIds.includes(p.id))
                                }
                                checked={
                                    filteredGeneralParams.length > 0 &&
                                    filteredGeneralParams.every(p => selectedParamIds.includes(p.id))
                                }
                                onChange={e => handleSelectAll(e.target.checked)}
                            >
                                <span className="text-gray-600 font-medium ml-1">
                                    Select All ({filteredGeneralParams.length})
                                </span>
                            </Checkbox>
                            <span className="text-gray-400 text-xs whitespace-nowrap bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
                                {selectedParamIds.length} selected
                            </span>
                        </div>
                    </div>

                    {/* Parameter list */}
                    <div className="border border-gray-100 rounded-xl overflow-hidden shadow-sm">
                        <OptimizedTable
                            columns={importColumns}
                            dataSource={filteredGeneralParams}
                            size="middle"
                            loading={generalParamsLoading}
                            pagination={{
                                pageSize: 8,
                                showSizeChanger: true,
                                showTotal: (total) => `Total ${total} parameters`,
                                className: "px-4"
                            }}
                            rowSelection={{
                                type: 'checkbox',
                                selectedRowKeys: selectedParamIds,
                                onChange: (keys) => setSelectedParamIds(keys),
                                preserveSelectedRowKeys: true,
                            }}
                            scroll={{ y: 500 }}
                            className="import-table"
                        />
                    </div>
                </div>
            </Modal>

            {/* Manage Investors Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2 text-gray-800 text-lg font-semibold">
                        <TeamOutlined className="text-blue-500" />
                        Manage Investors
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
const SearchInput = memo(({ onSearch, placeholder = "Search parameters or categories...", className = "h-11 rounded-xl bg-gray-50 border-transparent focus:bg-white hover:bg-white transition-all duration-200 pl-4" }) => {
    const [innerValue, setInnerValue] = useState("");

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
const OptimizedTable = memo(({ loading, dataSource, columns, pagination, scroll, className = "custom-table", rowSelection = null, size = "large" }) => {
    return (
        <Table
            loading={loading}
            dataSource={dataSource}
            columns={columns}
            rowKey="id"
            pagination={pagination}
            className={className}
            rowClassName={() => "hover:bg-blue-50/30 transition-colors cursor-pointer"}
            virtual
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
