// src/components/ExcelPreviewModal.jsx

import React, { useState, useMemo, useRef, useEffect, useDeferredValue, memo, useCallback } from "react";
import {
    Modal,
    Table,
    Button,
    Space,
    Input,
    Tooltip,
    Pagination,
    Tabs,
    Spin,
} from "antd";
import {
    FileExcelOutlined,
    DownloadOutlined,
    SearchOutlined,
    FilterOutlined,
    RobotOutlined,
    CloseOutlined,
    LoadingOutlined,
    FilePdfOutlined,
} from "@ant-design/icons";
const ChatInterface = React.lazy(() => import("./ChatInterface"));
const PdfViewerModal = React.lazy(() => import("./PdfViewerModal"));
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
    sessionId = null,
    isComparisonMode = false,
    investor = "",
    version = "",
}) => {
    const [searchText, setSearchText] = useState("");
    const deferredSearchText = useDeferredValue(searchText);
    const [searchExpanded, setSearchExpanded] = useState(false);
    const [filteredInfo, setFilteredInfo] = useState({});
    const [sortedInfo, setSortedInfo] = useState({});
    const [filterLoading, setFilterLoading] = useState(false);
    const [chatVisible, setChatVisible] = useState(false);
    const [pdfViewerVisible, setPdfViewerVisible] = useState(false);
    const [pdfTargetPage, setPdfTargetPage] = useState(null);
    const [activeTab, setActiveTab] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [currentPageSize, setCurrentPageSize] = useState(pageSize || 50);
    const [columnWidths, setColumnWidths] = useState({});

    // Refs for column resizing
    const resizingColumn = useRef(null);
    const startX = useRef(null);
    const startWidth = useRef(null);

    // Determine if we have multiple tabs
    const isMultiTab = useMemo(() => {
        return !Array.isArray(data) && data !== null && typeof data === 'object';
    }, [data]);

    // Get list of tab keys
    const tabKeys = useMemo(() => {
        if (isMultiTab) return Object.keys(data);
        return [];
    }, [isMultiTab, data]);

    // Set initial active tab
    useEffect(() => {
        if (isMultiTab && tabKeys.length > 0 && !activeTab) {
            setActiveTab(tabKeys[0]);
        }
    }, [isMultiTab, tabKeys, activeTab]);

    // Current data to display
    const currentData = useMemo(() => {
        if (isMultiTab) {
            return data[activeTab] || [];
        }
        return data || [];
    }, [isMultiTab, data, activeTab]);

    const convertToTableData = (rawData) => {
        if (!Array.isArray(rawData)) return [];
        return rawData.map((item, idx) => ({ key: idx, ...item }));
    };

    const tableData = convertToTableData(currentData);

    // Search
    const searchFilteredData = useMemo(() => {
        if (!deferredSearchText) return tableData;
        const lowerSearch = deferredSearchText.toLowerCase();
        return tableData.filter((record) =>
            Object.values(record).some((value) =>
                String(value).toLowerCase().includes(lowerSearch)
            )
        );
    }, [tableData, deferredSearchText]);

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

    // Sort
    const getSortedData = useMemo(() => {
        let sorted = [...getFilteredDataForFilters];
        if (sortedInfo.columnKey && sortedInfo.order) {
            sorted.sort((a, b) => {
                const valA = a[sortedInfo.columnKey] || "";
                const valB = b[sortedInfo.columnKey] || "";
                const sortResult = String(valA).localeCompare(String(valB));
                return sortedInfo.order === "ascend" ? sortResult : -sortResult;
            });
        }
        return sorted;
    }, [getFilteredDataForFilters, sortedInfo]);

    // Pagination
    const paginatedData = useMemo(() => {
        const startIndex = (currentPage - 1) * currentPageSize;
        return getSortedData.slice(startIndex, startIndex + currentPageSize);
    }, [getSortedData, currentPage, currentPageSize]);

    // Reset page on filter/sort change or tab change
    useEffect(() => {
        setCurrentPage(1);
    }, [searchText, filteredInfo, sortedInfo, activeTab]);

    const getColumnFilters = (dataIndex) => {
        const uniqueValues = [
            ...new Set(getFilteredDataForFilters.map((item) => item[dataIndex])),
        ];
        return uniqueValues
            .filter((val) => val !== null && val !== undefined && val !== "")
            .map((val) => ({
                text:
                    String(val).substring(0, 50) +
                    (String(val).length > 50 ? "..." : ""),
                value: val,
            }));
    };

    // Column resize handlers
    const handleMouseDown = (key, currentWidth) => (e) => {
        e.preventDefault();
        resizingColumn.current = key;
        startX.current = e.clientX;
        startWidth.current = currentWidth;

        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    };

    const handleMouseMove = (e) => {
        if (!resizingColumn.current) return;

        const diff = e.clientX - startX.current;
        const newWidth = Math.max(50, startWidth.current + diff);

        setColumnWidths((prev) => ({
            ...prev,
            [resizingColumn.current]: newWidth,
        }));
    };

    const handleMouseUp = () => {
        resizingColumn.current = null;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
    };

    // ✅ Dynamic "Prefit" Width Calculation
    const calculatedWidths = useMemo(() => {
        if (!currentData || currentData.length === 0) return {};

        const widths = {};
        const sampleData = currentData.slice(0, 100); // Check first 100 rows for performance

        // Initialize with header title widths
        const tempColumns = columns ? columns.map(c => c.dataIndex) : (currentData[0] ? Object.keys(currentData[0]) : []);

        tempColumns.forEach(key => {
            // Start with a base width for the header text
            const displayTitle = key.replace(/_/g, " ").toUpperCase();
            widths[key] = Math.max(100, displayTitle.length * 10 + 40);
        });

        // Update based on content
        sampleData.forEach(row => {
            tempColumns.forEach(key => {
                const val = String(row[key] || "");
                // Estimation: 8px per character for average font size, capped at 500
                const contentWidth = Math.min(500, val.length * 8 + 30);
                if (contentWidth > widths[key]) {
                    widths[key] = contentWidth;
                }
            });
        });

        // Specific overrides for consistency
        if (widths.page_number) widths.page_number = 120;
        if (widths.s_no || widths.sno) widths.s_no = widths.sno = 80;

        return widths;
    }, [data, columns]);

    const columnsMemo = useMemo(() => {
        const generateColumn = (key, customTitle = null, customWidth = null) => {
            const prefitWidth = calculatedWidths[key] || 250;
            const currentWidth = customWidth || columnWidths[key] || prefitWidth;

            let displayTitle = customTitle;
            if (!displayTitle) {
                if (key === "rule_id" || key.trim().toLowerCase() === "dscr_parameters" || key.trim().toLowerCase() === "dscr parameters") {
                    displayTitle = "PARAMETERS";
                } else {
                    displayTitle = key.replace(/_/g, " ").toUpperCase();
                }
            }

            return {
                title: (
                    <div
                        style={{
                            position: "relative",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            width: "100%",
                            paddingRight: 10
                        }}
                    >
                        <span className="font-bold">{displayTitle}</span>
                        <div
                            onMouseDown={handleMouseDown(key, currentWidth)}
                            style={{
                                position: "absolute",
                                right: -8,
                                top: -16,
                                bottom: -16,
                                width: "16px",
                                cursor: "col-resize",
                                zIndex: 1,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                            }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div
                                style={{
                                    width: "1px",
                                    height: "100%",
                                    backgroundColor: "rgba(255, 255, 255, 0.3)",
                                    transition: "background-color 0.2s",
                                }}
                                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#fff")}
                                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.3)")}
                            />
                        </div>
                    </div>
                ),
                dataIndex: key,
                key,
                width: currentWidth,
                className: "antd-excel-column",
                sorter: (a, b) =>
                    String(a[key] || "").localeCompare(String(b[key] || "")),
                sortOrder:
                    sortedInfo.columnKey === key ? sortedInfo.order : null,
                filters: getColumnFilters(key),
                filteredValue: filteredInfo[key] || null,
                onFilter: (value, record) =>
                    String(record[key]) === String(value),
                filterIcon: (filtered) =>
                    filterLoading ? (
                        <LoadingOutlined style={{ color: "#fff" }} />
                    ) : (
                        <FilterOutlined
                            style={{ color: filtered ? "#fffc00" : "#fff" }}
                        />
                    ),
                render: (text, record) => {
                    const isPdfLink = key === "pdf_link" || (typeof text === 'string' && text.includes(".pdf"));
                    const isPageNumber = key === "page_number";

                    if (isPdfLink && text) {
                        return (
                            <Button
                                type="link"
                                icon={<FilePdfOutlined />}
                                onClick={() => {
                                    setPdfTargetPage(record.page_number || 1);
                                    setPdfViewerVisible(true);
                                }}
                                className="p-0 h-auto text-red-500 hover:text-red-600"
                            >
                                View Evidence
                            </Button>
                        );
                    }

                    if (isPageNumber && text) {
                        return (
                            <span
                                className="cursor-pointer text-blue-500 hover:text-blue-600 hover:underline font-medium"
                                onClick={() => {
                                    const pageStr = String(text || "");
                                    let pageNum = null;
                                    if (pageStr && pageStr !== "N/A") {
                                        if (pageStr.includes("-")) {
                                            pageNum = parseInt(pageStr.split("-")[0]);
                                        } else {
                                            pageNum = parseInt(pageStr);
                                        }
                                    }
                                    if (pageNum && !isNaN(pageNum)) {
                                        setPdfTargetPage(pageNum);
                                        setPdfViewerVisible(true);
                                    }
                                }}
                            >
                                Page {text}
                            </span>
                        );
                    }

                    return (
                        <div className="antd-cell-content" title={String(text || "")}>
                            {text || "-"}
                        </div>
                    );
                },
            };
        };

        // Serial number column
        const serialNumberColumn = {
            title: <span className="font-bold">S.NO</span>,
            dataIndex: "sno",
            key: "sno",
            width: 80,
            align: "center",
            fixed: "left",
            render: (text, record, index) => {
                const rowNumber = (currentPage - 1) * currentPageSize + index + 1;
                return (
                    <div className="text-center font-medium">
                        {rowNumber}
                    </div>
                );
            },
        };

        let dataColumns = [];
        if (columns) {
            dataColumns = columns.map((col) => generateColumn(col.dataIndex, col.title, col.width));
        } else if (currentData.length > 0) {
            dataColumns = Object.keys(currentData[0]).map((key) => generateColumn(key));
        }

        return [serialNumberColumn, ...dataColumns];
    }, [currentData, columns, sortedInfo, filteredInfo, columnWidths, calculatedWidths, currentPage, currentPageSize]);

    const handleTableChange = (pagination, filters, sorter) => {
        setFilteredInfo(filters);
        setSortedInfo(sorter);
    };

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
                style={{
                    paddingBottom: 0,
                    maxWidth: "calc(100vw - 40px)",
                }}
                bodyStyle={{
                    height: "90vh",
                    padding: 0,
                    display: "flex",
                    flexDirection: "column",
                }}
                onCancel={onClose}
            >
                <div className="flex justify-between items-center px-4 py-2 border-b bg-white relative">
                    <div className="flex items-center gap-3">
                        <div className={`${iconBgColor} p-2 rounded-full`}>
                            <IconComponent className={`${iconColor} text-xl`} />
                        </div>
                        <h3 className="font-semibold text-lg">
                            {title}
                        </h3>
                    </div>
                    <Space>
                        {sessionId && !isComparisonMode && (
                            <Button
                                icon={<FilePdfOutlined />}
                                onClick={() => setPdfViewerVisible(true)}
                            >
                                View PDF
                            </Button>
                        )}
                        {onDownload && (
                            <Button
                                type="primary"
                                icon={<DownloadOutlined />}
                                onClick={() => {
                                    if (isMultiTab) {
                                        onDownload(activeTab);
                                    } else {
                                        onDownload();
                                    }
                                }}
                            >
                                {isMultiTab ? `Download ${activeTab}` : downloadButtonText}
                            </Button>
                        )}
                        <Button onClick={onClose} icon={<CloseOutlined />}>
                            Close
                        </Button>
                    </Space>
                </div>

                <div className="px-4 py-1.5 bg-gray-50 border-b flex items-center gap-3">
                    {!searchExpanded ? (
                        <Button
                            icon={<SearchOutlined />}
                            onClick={() => setSearchExpanded(true)}
                            size="middle"
                            title="Search"
                        />
                    ) : (
                        <SearchInput onSearch={setSearchText} />
                    )}
                    <Button onClick={clearFilters} size="small">
                        Clear Filters
                    </Button>
                    <span className="text-sm text-gray-500">
                        {(getFilteredDataForFilters.length !==
                            tableData.length ||
                            searchText) &&
                            `Showing ${getFilteredDataForFilters.length} of ${tableData.length} rows`}
                    </span>
                    {isMultiTab && (
                        <div className="ml-auto" style={{ marginBottom: '-6px' }}>
                            <Tabs
                                activeKey={activeTab}
                                onChange={setActiveTab}
                                size="small"
                                className="excel-preview-tabs"
                                items={tabKeys.map(key => ({
                                    key: key,
                                    label: (
                                        <span className="flex items-center gap-1.5 px-2">
                                            <FileExcelOutlined style={{ color: '#1d6f42' }} />
                                            <span className="font-medium">
                                                {`${investor.replace(/ /g, '_')}_${version.replace(/ /g, '_')}_${key.replace(/ /g, '')}`}
                                            </span>
                                            <span className="text-[10px] bg-gray-200 text-gray-600 px-1.5 rounded-full">
                                                {data[key]?.length || 0}
                                            </span>
                                        </span>
                                    )
                                }))}
                            />
                        </div>
                    )}
                </div>

                <div
                    className="p-1 bg-gray-50 relative flex flex-col"
                    style={{ flex: 1, overflow: "hidden" }}
                >
                    <div
                        className="flex-1"
                        style={{
                            overflow: "auto",
                            scrollbarWidth: "thin",
                            scrollbarColor: "#888 #f1f1f1",
                        }}
                    >
                        <style>{`
                            .flex-1::-webkit-scrollbar {
                                width: 8px;
                                height: 8px;
                            }
                            .flex-1::-webkit-scrollbar-track {
                                background: #f1f1f1;
                                border-radius: 10px;
                            }
                            .flex-1::-webkit-scrollbar-thumb {
                                background: #888;
                                border-radius: 10px;
                            }
                            .flex-1::-webkit-scrollbar-thumb:hover {
                                background: #555;
                            }

                            /* Ensure Ant Design table internal scrollbars are also styled and visible */
                            .antd-excel-preview-table .ant-table-body::-webkit-scrollbar,
                            .antd-excel-preview-table .ant-table-content::-webkit-scrollbar {
                                width: 8px;
                                height: 8px;
                                display: block !important;
                            }
                            .antd-excel-preview-table .ant-table-body::-webkit-scrollbar-track,
                            .antd-excel-preview-table .ant-table-content::-webkit-scrollbar-track {
                                background: #f1f1f1;
                                border-radius: 10px;
                            }
                            .antd-excel-preview-table .ant-table-body::-webkit-scrollbar-thumb,
                            .antd-excel-preview-table .ant-table-content::-webkit-scrollbar-thumb {
                                background: #888;
                                border-radius: 10px;
                            }

                            .antd-excel-preview-table .ant-table-thead > tr > th {
                                background-color: #1F4E78 !important;
                                color: white !important;
                                font-weight: bold !important;
                                border-bottom: 1px solid #d9d9d9 !important;
                                border-right: 1px solid #d9d9d9 !important;
                                border-left: 1px solid #d9d9d9 !important;
                                text-align: center !important;
                            }
                            
                            .antd-excel-preview-table .ant-table-tbody > tr > td {
                                border-right: 1px solid #d9d9d9 !important;
                                border-left: 1px solid #d9d9d9 !important;
                                vertical-align: top !important;
                                padding: 4px 8px !important;
                            }

                            .antd-excel-preview-table .ant-table-tbody > tr:hover > td {
                                background-color: #f5faff !important;
                            }

                            .antd-excel-column {
                                min-width: 50px;
                            }

                            /* Ensure the table itself has a clean outer border */
                            .antd-excel-preview-table {
                                border: 1px solid #d9d9d9 !important;
                            }
                        `}</style>
                        <OptimizedTable
                            columns={columnsMemo}
                            dataSource={paginatedData}
                            onChange={handleTableChange}
                            loading={filterLoading}
                        />
                    </div>

                    <div className="flex justify-end items-center mt-4 gap-4">
                        <Pagination
                            current={currentPage}
                            pageSize={currentPageSize}
                            total={getFilteredDataForFilters.length}
                            showSizeChanger
                            pageSizeOptions={["10", "20", "50", "100", "200"]}
                            locale={{ items_per_page: "" }}
                            onChange={(page, size) => {
                                setCurrentPage(page);
                                setCurrentPageSize(size);
                            }}
                        />

                        <Tooltip title="Ask AI about this data">
                            <Button
                                type="primary"
                                shape="circle"
                                icon={<RobotOutlined />}
                                size="large"
                                onClick={() => setChatVisible(true)}
                                className="shadow-lg"
                                style={{
                                    backgroundColor: "#0EA5E9",
                                    borderColor: "#0EA5E9",
                                }}
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
                <React.Suspense fallback={<div className="fixed bottom-6 right-6 z-[1050]"><Spin tip="Loading chat..." /></div>}>
                    <ChatInterface
                        visible={true}
                        onClose={() => setChatVisible(false)}
                        data={data}
                        sessionId={sessionId}
                        isComparisonMode={isComparisonMode}
                        onOpenPdf={() => setPdfViewerVisible(true)}
                    />
                </React.Suspense>
            )}

            {/* PDF Viewer Modal */}
            {sessionId && (
                <React.Suspense fallback={<Modal open={pdfViewerVisible} footer={null} closable={false} centered><div className="p-10 text-center"><Spin size="large" tip="Loading PDF Viewer..." /></div></Modal>}>
                    <PdfViewerModal
                        visible={pdfViewerVisible}
                        onClose={() => {
                            setPdfViewerVisible(false);
                            setPdfTargetPage(null);
                        }}
                        sessionId={sessionId}
                        title="PDF Document"
                        initialPage={pdfTargetPage}
                        initialFileIndex={0}
                    />
                </React.Suspense>
            )}
        </>
    );
};

// Sub-component to isolate search state and prevent re-rendering the whole Modal on every keystroke
const SearchInput = memo(({ onSearch }) => {
    const [innerValue, setInnerValue] = useState("");

    const handleChange = (e) => {
        const val = e.target.value;
        setInnerValue(val);
        onSearch(val);
    };

    return (
        <Input
            placeholder="Search in results..."
            prefix={<SearchOutlined className="text-gray-400" />}
            value={innerValue}
            onChange={handleChange}
            className="bg-gray-50 border-none rounded-lg h-10 w-64"
            allowClear
        />
    );
});

// Memoized Table to prevent re-renders unless data or columns actually change
const OptimizedTable = memo(({ loading, dataSource, columns, onChange }) => {
    return (
        <Table
            columns={columns}
            dataSource={dataSource}
            pagination={false}
            onChange={onChange}
            loading={loading}
            scroll={{ x: "max-content", y: "calc(90vh - 220px)" }}
            className="antd-excel-preview-table"
            rowClassName="antd-excel-row"
            size="small"
            bordered
        />
    );
});

export default ExcelPreviewModal;
