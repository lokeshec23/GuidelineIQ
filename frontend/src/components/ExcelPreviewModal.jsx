// src/components/ExcelPreviewModal.jsx

import React, { useState, useMemo, useRef, useEffect } from "react";
import {
    Modal,
    Table,
    Button,
    Space,
    Input,
    Tooltip,
    Spin,
    Pagination,
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
}) => {
    const [searchText, setSearchText] = useState("");
    const [searchExpanded, setSearchExpanded] = useState(false);
    const [filteredInfo, setFilteredInfo] = useState({});
    const [sortedInfo, setSortedInfo] = useState({});
    const [filterLoading, setFilterLoading] = useState(false);
    const [chatVisible, setChatVisible] = useState(false);
    const [pdfViewerVisible, setPdfViewerVisible] = useState(false);
    const [pdfTargetPage, setPdfTargetPage] = useState(null);
    const [currentPageSize, setCurrentPageSize] = useState(pageSize);
    const [currentPage, setCurrentPage] = useState(1);
    const [columnWidths, setColumnWidths] = useState({});
    const resizingColumn = useRef(null);
    const startX = useRef(0);
    const startWidth = useRef(0);

    const convertToTableData = (data) => {
        if (!Array.isArray(data)) return [];
        return data.map((item, idx) => ({ key: idx, ...item }));
    };

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

    // Reset page on filter/sort change
    useEffect(() => {
        setCurrentPage(1);
    }, [searchText, filteredInfo, sortedInfo]);

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
        if (!data || data.length === 0) return {};

        const widths = {};
        const sampleData = data.slice(0, 100); // Check first 100 rows for performance

        // Initialize with header title widths
        const tempColumns = columns ? columns.map(c => c.dataIndex) : Object.keys(data[0]);

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

    const getColumns = () => {
        const generateColumn = (key, customTitle = null) => {
            // ✅ Use pre-calculated "prefit" width, fallback to default if not available
            const prefitWidth = calculatedWidths[key] || 250;
            const currentWidth = columnWidths[key] || prefitWidth;

            let displayTitle = customTitle;

            if (!displayTitle) {
                if (key === "rule_id") {
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
                // ... same filter logic ...
                render: (text, record, index, key) => {
                    // Special rendering for page_number - make it clickable
                    if (key === "page_number" && sessionId && !isComparisonMode) {
                        return (
                            <div className="whitespace-pre-wrap break-words text-sm">
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
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
                                    className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium bg-transparent border-0 p-0"
                                    title="Click to view this page in PDF"
                                >
                                    {String(text || "")}
                                </button>
                            </div>
                        );
                    }

                    // Default rendering for other columns
                    return (
                        <div className="whitespace-pre-wrap break-words text-sm">
                            {String(text || "")}
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
            dataColumns = columns.map((col) => {
                const generatedCol = generateColumn(col.dataIndex, col.title);
                return {
                    ...generatedCol,
                    render: (text, record, index) => generatedCol.render(text, record, index, col.dataIndex)
                };
            });
        } else if (data?.length > 0) {
            dataColumns = Object.keys(data[0]).map((key) => {
                const generatedCol = generateColumn(key);
                return {
                    ...generatedCol,
                    render: (text, record, index) => generatedCol.render(text, record, index, key)
                };
            });
        } else {
            dataColumns = [
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
        }

        if (isComparisonMode) {
            dataColumns = dataColumns.filter(col =>
                col.dataIndex !== 'S NO' &&
                col.dataIndex !== 's_no' &&
                col.dataIndex !== 'sno' &&
                col.dataIndex !== 'dscr_parameters' &&
                col.dataIndex !== 'ppe_field_type'
            );
        }

        return [serialNumberColumn, ...dataColumns];
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
                {/* Header - fixed */}
                <div className="flex justify-between items-center px-4 py-2 border-b bg-white relative">
                    <div className="flex items-center gap-3">
                        <div className={`${iconBgColor} p-2 rounded-full`}>
                            <IconComponent className={`${iconColor} text-xl`} />
                        </div>
                        <h3 className="font-semibold text-lg">
                            {title}
                            {/* {showRowCount && (
                                <span className="ml-2 text-gray-500 font-normal">
                                    ({data.length} rows)
                                </span>
                            )} */}
                        </h3>
                    </div>
                    <Space>
                        {/* View PDF Button - Only for ingestion mode */}
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

                {/* Search bar - fixed below header */}
                <div className="px-4 py-1.5 bg-gray-50 border-b flex items-center gap-3">
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
                            onBlur={() =>
                                !searchText && setSearchExpanded(false)
                            }
                            allowClear
                            autoFocus
                            style={{ width: 300 }}
                        />
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
                </div>

                {/* Content area - table scrolls, footer fixed */}
                <div
                    className="p-1 bg-gray-50 relative flex flex-col"
                    style={{ flex: 1, overflow: "hidden" }}
                >
                    {/* Scrollable table container */}
                    <div
                        className="flex-1"
                        style={{
                            overflow: "auto",
                            scrollbarWidth: "thin", // For Firefox
                            scrollbarColor: "#888 #f1f1f1", // For Firefox
                        }}
                    >
                        <style>{`
                            /* Custom scrollbar for Webkit browsers (Chrome, Safari, Edge) */
                            .flex-1::-webkit-scrollbar {
                                width: 12px;
                                height: 12px;
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

                            /* Excel-like Table Styles */
                            .antd-excel-table .ant-table-thead > tr > th {
                                background-color: #1F4E78 !important; /* Dark Blue from Excel Export */
                                color: white !important;
                                font-weight: bold !important;
                                border-bottom: 1px solid #d9d9d9 !important;
                                border-right: 1px solid rgba(255, 255, 255, 0.2) !important;
                                text-align: center !important;
                            }
                            
                            .antd-excel-table .ant-table-tbody > tr > td {
                                border-right: 1px solid #f0f0f0 !important;
                                vertical-align: top !important;
                                padding: 4px 8px !important;
                            }

                            .antd-excel-table .ant-table-tbody > tr:hover > td {
                                background-color: #f5faff !important;
                            }

                            .antd-excel-column {
                                min-width: 50px;
                            }
                        `}</style>
                        <Table
                            dataSource={paginatedData}
                            columns={tableColumns}
                            className="antd-excel-table"
                            onChange={(pagination, filters, sorter) => {
                                setFilteredInfo(filters);
                                setSortedInfo(sorter);
                            }}
                            pagination={false}
                            scroll={{ x: "max-content", y: "calc(90vh - 220px)" }}
                            bordered
                            size="small"
                        />
                    </div>

                    {/* Footer - fixed inside modal */}
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

export default ExcelPreviewModal;
