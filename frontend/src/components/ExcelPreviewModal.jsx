// src/components/ExcelPreviewModal.jsx

import React from "react";
import { Modal, Table, Button, Space, Tag } from "antd";
import { FileExcelOutlined, DownloadOutlined } from "@ant-design/icons";

/**
 * Generic Excel Preview Modal Component
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
    // Convert data to table format with keys
    const convertToTableData = (data) =>
        data?.map((item, idx) => ({ key: idx, ...item })) || [];

    // Auto-generate columns from data if not provided
    const getColumns = () => {
        if (columns) return columns;

        if (data?.length > 0) {
            return Object.keys(data[0]).map((key) => ({
                title: key.replace(/_/g, " ").toUpperCase(),
                dataIndex: key,
                key,
                width: 250,
                render: (text) => (
                    <div className="whitespace-pre-wrap text-sm">{String(text)}</div>
                ),
            }));
        }

        return [{ title: "Result", dataIndex: "content" }];
    };

    const tableData = convertToTableData(data);
    const tableColumns = getColumns();

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
                        <Tag color="blue">{tableData.length} rows</Tag>
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

            {/* Table */}
            <div className="p-4 bg-gray-50">
                <Table
                    dataSource={tableData}
                    columns={tableColumns}
                    pagination={{ pageSize }}
                    scroll={{ y: "calc(90vh - 200px)", x: "max-content" }}
                    bordered
                    size="middle"
                />
            </div>
        </Modal>
    );
};

export default ExcelPreviewModal;
