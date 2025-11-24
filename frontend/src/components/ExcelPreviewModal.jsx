// src/components/ExcelPreviewModal.jsx

import React, { useState, useMemo } from "react";
import { Modal, Table, Button, Space, Tag, Input } from "antd";
import {
    FileExcelOutlined,
    DownloadOutlined,
    SearchOutlined,
    FilterOutlined
} from "@ant-design/icons";

/**
 * Generic Excel Preview Modal Component with Modern Table Features
 * 
 * @param {boolean} visible - Controls modal visibility
 * @param {function} onClose - Callback when modal is closed
 * @param {string} title - Modal title (default: "Extraction Results")
 * @param {array} data - Array of data objects to display
 * @param {array} columns - Column definitions (auto-generated if not provided)
 * @param {function} onDownload - Download button callback (optional)
 * @param {string} downloadButtonText - Download button text (default: "Download Excel")
 * @param {boolean} showRowCount - Show row count tag (default: true)
 * @param {number} pageSize - Rows per page (default: 50)
 * @param {string} icon - Icon component (default: FileExcelOutlined)
 * @param {string} iconColor - Icon color class (default: "text-green-600")
 * @param {string} iconBgColor - Icon background color class (default: "bg-green-100")
 */
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
}) => {
    const [searchText, setSearchText] = useState("");
    const [searchExpanded, setSearchExpanded] = useState(false);
    const [filteredInfo, setFilteredInfo] = useState({});
    const [sortedInfo, setSortedInfo] = useState({});

    // Convert data to table format with keys
    const convertToTableData = (data) =>
        data?.map((item, idx) => ({ key: idx, ...item })) || [];

    const tableData = convertToTableData(data);

    // Global search filter
    const searchFilteredData = useMemo(() => {
        if (!searchText) return tableData;

        return tableData.filter(record =>
            Object.values(record).some(value =>
                String(value).toLowerCase().includes(searchText.toLowerCase())
            )
        );
    }, [tableData, searchText]);

    // Apply column filters to get currently filtered data
    const getFilteredDataForFilters = useMemo(() => {
        let filtered = searchFilteredData;

        // Apply each active filter
        Object.keys(filteredInfo).forEach(key => {
            const filterValues = filteredInfo[key];
            if (filterValues && filterValues.length > 0) {
                filtered = filtered.filter(record =>
                    filterValues.includes(record[key])
                );
            }
        });

        return filtered;
    }, [searchFilteredData, filteredInfo]);

    // Get unique values for a column (for filters) - based on currently filtered data
    const getColumnFilters = (dataIndex) => {
        // Use currently filtered data to generate filter options
        const uniqueValues = [...new Set(getFilteredDataForFilters.map(item => item[dataIndex]))];
        return uniqueValues
            .filter(val => val !== null && val !== undefined && val !== "")
            .map(val => ({
                text: String(val).substring(0, 50) + (String(val).length > 50 ? "..." : ""),
                value: val,
            }));
    };

    // Auto-generate columns from data if not provided
    const getColumns = () => {
        if (columns) {
            // Enhance provided columns with search, filter, sort
            return columns.map(col => ({
                ...col,
                sorter: (a, b) => {
                    const aVal = String(a[col.dataIndex] || "");
                    const bVal = String(b[col.dataIndex] || "");
                    return aVal.localeCompare(bVal);
                },
                sortOrder: sortedInfo.columnKey === col.dataIndex ? sortedInfo.order : null,
                filters: getColumnFilters(col.dataIndex),
                filteredValue: filteredInfo[col.dataIndex] || null,
                onFilter: (value, record) => String(record[col.dataIndex]) === String(value),
                filterIcon: (filtered) => (
                    <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
                ),
                ellipsis: false,
                render: (text) => (
                    <div className="whitespace-pre-wrap break-words text-sm max-w-md">
                        {String(text || "")}
                    </div>
                ),
            }));
        }

        if (data?.length > 0) {
            return Object.keys(data[0]).map((key) => ({
                title: key.replace(/_/g, " ").toUpperCase(),
                dataIndex: key,
                key,
                width: 250,
                sorter: (a, b) => {
                    const aVal = String(a[key] || "");
                    const bVal = String(b[key] || "");
                    return aVal.localeCompare(bVal);
                },
                sortOrder: sortedInfo.columnKey === key ? sortedInfo.order : null,
                filters: getColumnFilters(key),
                filteredValue: filteredInfo[key] || null,
                onFilter: (value, record) => String(record[key]) === String(value),
                filterIcon: (filtered) => (
                    <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
                ),
                ellipsis: false,
                render: (text) => (
                    <div className="whitespace-pre-wrap break-words text-sm max-w-md">
                        {String(text || "")}
                    </div>
                ),
            }));
        }

        return [{
            title: "Result",
            dataIndex: "content",
            render: (text) => (
                <div className="whitespace-pre-wrap break-words text-sm">
                    {String(text || "")}
                </div>
            ),
        }];
    };

    const tableColumns = getColumns();

    const handleTableChange = (pagination, filters, sorter) => {
        setFilteredInfo(filters);
        setSortedInfo(sorter);
    };

    const handleSearchChange = (e) => {
        setSearchText(e.target.value);
    };

    const handleSearchIconClick = () => {
        setSearchExpanded(true);
    };

    const handleSearchBlur = () => {
        if (!searchText) {
            setSearchExpanded(false);
        }
    };

    const clearFilters = () => {
        setFilteredInfo({});
        setSortedInfo({});
        setSearchText("");
        setSearchExpanded(false);
    };

    return (
        <Modal
            open={visible}
            footer={null}
            width="95vw"
            centered
            closable={false}
            style={{ top: "20px" }}
            onCancel={onClose}
        >
            {/* Header */}
            <div className="flex justify-between items-center px-6 py-4 border-b bg-white">
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
                    <Button onClick={onClose}>Close</Button>
                    {onDownload && (
                        <Button
                            type="primary"
                            icon={<DownloadOutlined />}
                            onClick={onDownload}
                        >
                            {downloadButtonText}
                        </Button>
                    )}
                </Space>
            </div>

            {/* Search and Filter Controls */}
            <div className="px-6 py-3 bg-gray-50 border-b flex items-center gap-3">
                {/* Collapsible Search */}
                {!searchExpanded ? (
                    <Button
                        icon={<SearchOutlined />}
                        onClick={handleSearchIconClick}
                        size="middle"
                        title="Search"
                    />
                ) : (
                    <Input
                        placeholder="Search across all columns..."
                        prefix={<SearchOutlined />}
                        value={searchText}
                        onChange={handleSearchChange}
                        onBlur={handleSearchBlur}
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
                        `Showing ${getFilteredDataForFilters.length} of ${tableData.length} rows`
                    }
                </span>
            </div>

            {/* Table */}
            <div className="p-4 bg-gray-50">
                <Table
                    dataSource={searchFilteredData}
                    columns={tableColumns}
                    onChange={handleTableChange}
                    pagination={{
                        pageSize,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`,
                        pageSizeOptions: ['10', '20', '50', '100', '200'],
                    }}
                    scroll={{ y: "calc(90vh - 280px)", x: "max-content" }}
                    bordered
                    size="middle"
                />
            </div>
        </Modal>
    );
};

export default ExcelPreviewModal;
