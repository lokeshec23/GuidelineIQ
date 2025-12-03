// src/components/ExcelPreviewModal.jsx

import React, { useState, useMemo } from "react";
import { Modal, Table, Button, Space, Tag, Input, Tooltip, Spin } from "antd";
import {
    FileExcelOutlined,
    DownloadOutlined,
    SearchOutlined,
    FilterOutlined,
    RobotOutlined,
    CloseOutlined,
    LoadingOutlined,
} from "@ant-design/icons";
import ChatInterface from "./ChatInterface";
import PdfViewerModal from "./PdfViewerModal";
import { API_BASE_URL } from "../services/api";

const ExcelPreviewModal = ({
    visible,
    onClose,
    title = "Extraction Results",
    data = [],
    columns = null,
    onDownload = null,
    downloadButtonText = "Download Excel",
    showRowCount = true,
    pageSize = 50,
    icon: IconComponent = FileExcelOutlined,
    iconColor = "text-green-600",
    iconBgColor = "bg-green-100",
    sessionId = null, // ✅ Add sessionId prop
    isComparisonMode = false, // ✅ Add isComparisonMode prop
}) => {
    const [searchText, setSearchText] = useState("");
    const [searchExpanded, setSearchExpanded] = useState(false);
    const [filteredInfo, setFilteredInfo] = useState({});
    const [sortedInfo, setSortedInfo] = useState({});
    const [filterLoading, setFilterLoading] = useState(false);
    const [chatVisible, setChatVisible] = useState(false);
    const [pdfViewerVisible, setPdfViewerVisible] = useState(false);

    const convertToTableData = (data) =>
        data?.map((item, idx) => ({ key: idx, ...item })) || [];

    const tableData = convertToTableData(data);

    // Search
    const searchFilteredData = useMemo(() => {
        if (!searchText) return tableData;
        return tableData.filter((record) =>
            Object.values(record).some((value) =>
                String(value).toLowerCase().includes(searchText.toLowerCase())
            )
        );
    }, [tableData, searchText]);

    // Filter
    const getFilteredDataForFilters = useMemo(() => {
        let filtered = searchFilteredData;
        Object.keys(filteredInfo).forEach((key) => {
            const filterValues = filteredInfo[key];
            if (filterValues && filterValues.length > 0) {
                filtered = filtered.filter((record) =>
                    filterValues.includes(record[key])
                );
            }
        });
        return filtered;
    }, [searchFilteredData, filteredInfo]);

    const getColumnFilters = (dataIndex) => {
        const uniqueValues = [
            ...new Set(getFilteredDataForFilters.map((item) => item[dataIndex])),
        ];
        return uniqueValues
            .filter((val) => val !== null && val !== undefined && val !== "")
            .map((val) => ({
                text: String(val).substring(0, 50) + (String(val).length > 50 ? "..." : ""),
                value: val,
            }));
    };

    const getColumns = () => {
        const generateColumn = (key) => ({
            title: key.replace(/_/g, " ").toUpperCase(),
            dataIndex: key,
            key,
            width: 250,
            sorter: (a, b) => String(a[key] || "").localeCompare(String(b[key] || "")),
            sortOrder: sortedInfo.columnKey === key ? sortedInfo.order : null,
            filters: getColumnFilters(key),
            filteredValue: filteredInfo[key] || null,
            onFilter: (value, record) => String(record[key]) === String(value),
            filterIcon: (filtered) => (
                filterLoading ? (
                    <LoadingOutlined style={{ color: "#1890ff" }} />
                ) : (
                    <FilterOutlined style={{ color: filtered ? "#1890ff" : undefined }} />
                )
            ),
            filterDropdownOpen: undefined,
            onFilterDropdownOpenChange: (visible) => {
                if (visible) {
                    setFilterLoading(true);
                    // Use setTimeout to allow the loading state to render before computing filters
                    setTimeout(() => {
                        setFilterLoading(false);
                    }, 100);
                }
            },
            filterDropdown: (props) => {
                const { setSelectedKeys, selectedKeys, confirm, clearFilters } = props;
                const filterOptions = getColumnFilters(key);

                if (filterLoading) {
                    return (
                        <div style={{ padding: 40, textAlign: 'center' }}>
                            <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                            <div style={{ marginTop: 8, color: '#999' }}>Loading filters...</div>
                        </div>
                    );
                }

                return (
                    <div style={{ padding: 8 }}>
                        <div style={{ marginBottom: 8, maxHeight: 300, overflow: 'auto' }}>
                            {filterOptions.map((option) => (
                                <div
                                    key={option.value}
                                    style={{
                                        padding: '4px 8px',
                                        cursor: 'pointer',
                                        backgroundColor: selectedKeys?.includes(option.value) ? '#e6f7ff' : 'transparent',
                                    }}
                                    onClick={() => {
                                        const keys = selectedKeys || [];
                                        if (keys.includes(option.value)) {
                                            setSelectedKeys(keys.filter(k => k !== option.value));
                                        } else {
                                            setSelectedKeys([...keys, option.value]);
                                        }
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedKeys?.includes(option.value)}
                                        onChange={() => { }}
                                        style={{ marginRight: 8 }}
                                    />
                                    {option.text}
                                </div>
                            ))}
                        </div>
                        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                            <Button
                                size="small"
                                onClick={() => {
                                    clearFilters();
                                    confirm();
                                }}
                            >
                                Reset
                            </Button>
                            <Button
                                type="primary"
                                size="small"
                                onClick={() => confirm()}
                            >
                                OK
                            </Button>
                        </div>
                    </div>
                );
            },
            render: (text) => (
                <div className="whitespace-pre-wrap break-words text-sm max-w-md">
                    {String(text || "")}
                </div>
            ),
        });

        if (columns) return columns.map((col) => generateColumn(col.dataIndex));
        if (data?.length > 0) return Object.keys(data[0]).map(generateColumn);

        return [
            {
                title: "Result",
                dataIndex: "content",
                render: (text) => (
                    <div className="whitespace-pre-wrap break-words text-sm">
                        {String(text || "")}
                    </div>
                ),
            },
        ];
    };

    const tableColumns = getColumns();

    const clearFilters = () => {
        setFilteredInfo({});
        setSortedInfo({});
        setSearchText("");
        setSearchExpanded(false);
    };

    return (
        <>
            <Modal
                open={visible}
                footer={null}
                width="95vw"
                centered
                closable={false}
                style={{ top: "20px", height: "90dvh" }}
                onCancel={onClose}
            >
                {/* Header */}
                <div className="flex justify-between items-center px-6 py-4 border-b bg-white relative">
                    <div className="flex items-center gap-3">
                        <div className={`${iconBgColor} p-2 rounded-full`}>
                            <IconComponent className={`${iconColor} text-xl`} />
                        </div>
                        <h3 className="font-semibold text-lg">{title}</h3>
                        {showRowCount && (
                            <Tag color="blue">{getFilteredDataForFilters.length} rows</Tag>
                        )}
                    </div>
                    <Space>
                        {onDownload && (
                            <Button
                                type="primary"
                                icon={<DownloadOutlined />}
                                onClick={onDownload}
                            >
                                {downloadButtonText}
                            </Button>
                        )}
                        <Button onClick={onClose} icon={<CloseOutlined />}>
                            Close
                        </Button>
                    </Space>
                </div>

                {/* Search & Clear */}
                <div className="px-6 py-3 bg-gray-50 border-b flex items-center gap-3">
                    {!searchExpanded ? (
                        <Button
                            icon={<SearchOutlined />}
                            onClick={() => setSearchExpanded(true)}
                            size="middle"
                            title="Search"
                        />
                    ) : (
                        <Input
                            placeholder="Search across all columns..."
                            prefix={<SearchOutlined />}
                            value={searchText}
                            onChange={(e) => setSearchText(e.target.value)}
                            onBlur={() => !searchText && setSearchExpanded(false)}
                            allowClear
                            autoFocus
                            style={{ width: 300 }}
                        />
                    )}
                    <Button onClick={clearFilters} size="small">
                        Clear Filters
                    </Button>
                    <span className="text-sm text-gray-500">
                        {(getFilteredDataForFilters.length !== tableData.length || searchText) &&
                            `Showing ${getFilteredDataForFilters.length} of ${tableData.length} rows`}
                    </span>
                </div>

                {/* Table */}
                <div className="p-4 bg-gray-50 relative">
                    <Table
                        dataSource={searchFilteredData}
                        columns={tableColumns}
                        onChange={(pagination, filters, sorter) => {
                            setFilteredInfo(filters);
                            setSortedInfo(sorter);
                        }}
                        pagination={{
                            pageSize,
                            showSizeChanger: true,
                            pageSizeOptions: ["10", "20", "50", "100", "200"],
                        }}
                        scroll={{ y: "calc(90dvh - 280px)", x: "max-content" }}
                        bordered
                        size="middle"
                    />

                    {/* Floating AI Button (Bottom-Right) */}
                    <div className="absolute bottom-4 right-0 z-10">
                        <Tooltip title="Ask AI about this data">
                            <Button
                                type="primary"
                                shape="circle"
                                icon={<RobotOutlined />}
                                size="large"
                                onClick={() => setChatVisible(true)}
                                className="shadow-lg"
                                style={{ backgroundColor: "#0EA5E9", borderColor: "#0EA5E9" }}
                            />
                        </Tooltip>
                    </div>
                </div>
            </Modal>

            {/* Blur when chat is open */}
            {visible && chatVisible && (
                <div
                    className="fixed inset-0 backdrop-blur-sm z-[1040]"
                    onClick={() => setChatVisible(false)}
                />
            )}

            {/* Chat Dialog */}
            {visible && chatVisible && (
                <ChatInterface
                    visible={true}
                    onClose={() => setChatVisible(false)}
                    data={data}
                    sessionId={sessionId}
                    isComparisonMode={isComparisonMode}
                    onOpenPdf={() => setPdfViewerVisible(true)}
                />
            )}

            {/* PDF Viewer Modal - Outside chatbot for higher z-index */}
            {sessionId && (
                <PdfViewerModal
                    visible={pdfViewerVisible}
                    onClose={() => setPdfViewerVisible(false)}
                    pdfUrl={`${API_BASE_URL}/history/ingest/${sessionId}/pdf`}
                    title="PDF Document"
                />
            )}
        </>
    );
};

export default ExcelPreviewModal;
