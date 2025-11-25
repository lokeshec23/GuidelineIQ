// src/components/ExcelPreviewModal.jsx

import React, { useState, useMemo } from "react";
import { Modal, Table, Button, Space, Tag, Input, Tooltip } from "antd";
import {
    FileExcelOutlined,
    DownloadOutlined,
    SearchOutlined,
    FilterOutlined,
    RobotOutlined,
    CloseOutlined,
} from "@ant-design/icons";
import ChatInterface from "./ChatInterface";

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
    const [chatVisible, setChatVisible] = useState(false);

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
                <FilterOutlined style={{ color: filtered ? "#1890ff" : undefined }} />
            ),
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
                style={{ top: "20px" }}
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
                        scroll={{ y: "calc(90vh - 280px)", x: "max-content" }}
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
                    sessionId={null}
                />
            )}
        </>
    );
};

export default ExcelPreviewModal;
