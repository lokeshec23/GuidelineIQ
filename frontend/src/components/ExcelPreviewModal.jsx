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
    const [currentPageSize, setCurrentPageSize] = useState(pageSize);
    const [currentPage, setCurrentPage] = useState(1);
    const [columnWidths, setColumnWidths] = useState({});
    const resizingColumn = useRef(null);
    const startX = useRef(0);
    const startWidth = useRef(0);

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

    const getColumns = () => {
        const generateColumn = (key) => {
            const currentWidth = columnWidths[key] || 250;
            return {
                title: (
                    <div
                        style={{
                            position: "relative",
                            display: "flex",
                            alignItems: "center",
                        }}
                    >
                        <span>{key.replace(/_/g, " ").toUpperCase()}</span>
                        <div
                            onMouseDown={handleMouseDown(key, currentWidth)}
                            style={{
                                position: "absolute",
                                right: -8,
                                top: 0,
                                bottom: 0,
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
                                    width: "2px",
                                    height: "60%",
                                    backgroundColor: "#d9d9d9",
                                    transition: "background-color 0.2s",
                                }}
                                onMouseEnter={(e) =>
                                (e.currentTarget.style.backgroundColor =
                                    "#1890ff")
                                }
                                onMouseLeave={(e) =>
                                (e.currentTarget.style.backgroundColor =
                                    "#d9d9d9")
                                }
                            />
                        </div>
                    </div>
                ),
                dataIndex: key,
                key,
                width: currentWidth,
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
                        <LoadingOutlined style={{ color: "#1890ff" }} />
                    ) : (
                        <FilterOutlined
                            style={{ color: filtered ? "#1890ff" : undefined }}
                        />
                    ),
                onFilterDropdownOpenChange: (visible) => {
                    if (visible) {
                        setFilterLoading(true);
                        setTimeout(() => {
                            setFilterLoading(false);
                        }, 100);
                    }
                },
                filterDropdown: (props) => {
                    const {
                        setSelectedKeys,
                        selectedKeys,
                        confirm,
                        clearFilters,
                    } = props;
                    const filterOptions = getColumnFilters(key);

                    if (filterLoading) {
                        return (
                            <div
                                style={{
                                    padding: 40,
                                    textAlign: "center",
                                }}
                            >
                                <Spin
                                    indicator={
                                        <LoadingOutlined
                                            style={{ fontSize: 24 }}
                                            spin
                                        />
                                    }
                                />
                                <div
                                    style={{
                                        marginTop: 8,
                                        color: "#999",
                                    }}
                                >
                                    Loading filters...
                                </div>
                            </div>
                        );
                    }

                    return (
                        <div style={{ padding: 8 }}>
                            <div
                                style={{
                                    marginBottom: 8,
                                    maxHeight: 300,
                                    overflow: "auto",
                                }}
                            >
                                {filterOptions.map((option) => (
                                    <div
                                        key={option.value}
                                        style={{
                                            padding: "4px 8px",
                                            cursor: "pointer",
                                            backgroundColor:
                                                selectedKeys?.includes(
                                                    option.value
                                                )
                                                    ? "#e6f7ff"
                                                    : "transparent",
                                        }}
                                        onClick={() => {
                                            const keys = selectedKeys || [];
                                            if (keys.includes(option.value)) {
                                                setSelectedKeys(
                                                    keys.filter(
                                                        (k) =>
                                                            k !== option.value
                                                    )
                                                );
                                            } else {
                                                setSelectedKeys([
                                                    ...keys,
                                                    option.value,
                                                ]);
                                            }
                                        }}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={selectedKeys?.includes(
                                                option.value
                                            )}
                                            onChange={() => { }}
                                            style={{ marginRight: 8 }}
                                        />
                                        {option.text}
                                    </div>
                                ))}
                            </div>
                            <div
                                style={{
                                    borderTop: "1px solid #f0f0f0",
                                    paddingTop: 8,
                                    display: "flex",
                                    justifyContent: "space-between",
                                }}
                            >
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
            };
        };

        // Serial number column
        const serialNumberColumn = {
            title: "S.NO",
            dataIndex: "sno",
            key: "sno",
            width: 80,
            fixed: "left",
            render: (text, record, index) => {
                // Calculate the actual row number based on current page and page size
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
            dataColumns = columns.map((col) => generateColumn(col.dataIndex));
        } else if (data?.length > 0) {
            dataColumns = Object.keys(data[0]).map(generateColumn);
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

        // Add serial number column at the beginning
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
                width="90vw"
                centered
                closable={false}
                style={{
                    top: 0,
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
                <div className="flex justify-between items-center px-6 py-4 border-b bg-white relative">
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
                    className="p-4 bg-gray-50 relative flex flex-col"
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
                        `}</style>
                        <Table
                            dataSource={paginatedData}
                            columns={tableColumns}
                            onChange={(pagination, filters, sorter) => {
                                setFilteredInfo(filters);
                                setSortedInfo(sorter);
                            }}
                            pagination={false}
                            scroll={{ x: "max-content", y: "calc(90vh - 300px)" }}
                            bordered
                            size="middle"
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
                <ChatInterface
                    visible={true}
                    onClose={() => setChatVisible(false)}
                    data={data}
                    sessionId={sessionId}
                    isComparisonMode={isComparisonMode}
                    onOpenPdf={() => setPdfViewerVisible(true)}
                />
            )}

            {/* PDF Viewer Modal */}
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
