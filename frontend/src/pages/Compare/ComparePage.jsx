// src/pages/Compare/ComparePage.jsx

import React, { useState, useEffect } from "react";
import {
  Form,
  Select,
  Button,
  message,
  Progress,
  Modal,
  Table,
  Upload,
  Space,
  Tag,
  Spin,
  Tooltip
} from "antd";
import {
  InboxOutlined,
  FileTextOutlined,
  DownloadOutlined,
  DeleteOutlined,
  SwapOutlined,
  LoadingOutlined,
  DownOutlined,
  CloudUploadOutlined,
  EyeOutlined
} from "@ant-design/icons";
import { usePrompts } from "../../context/PromptContext";
import { compareAPI, settingsAPI, promptsAPI, historyAPI } from "../../services/api";

const { Dragger } = Upload;
const { Option } = Select;

const ComparePage = () => {
  const [form] = Form.useForm();
  const { comparePrompts } = usePrompts();

  // State
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [previewData, setPreviewData] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [supportedModels, setSupportedModels] = useState({
    openai: [],
    gemini: [],
  });
  const [selectedProvider, setSelectedProvider] = useState("openai");
  const [tableColumns, setTableColumns] = useState([]);
  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);

  // DB Selection State
  const [dbModalVisible, setDbModalVisible] = useState(false);
  const [historyData, setHistoryData] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedDbRecords, setSelectedDbRecords] = useState([]);

  useEffect(() => {
    fetchModels();
    form.setFieldsValue({
      model_provider: "openai",
      model_name: "gpt-4o",
    });
    setSelectedProvider("openai");
  }, []);

  const fetchModels = async () => {
    try {
      const res = await settingsAPI.getSupportedModels();
      setSupportedModels(res.data);
    } catch {
      setSupportedModels({
        openai: ["gpt-4o"],
        gemini: ["gemini-2.5-pro"],
      });
    }
  };

  const handleFileChange = (info) => {
    const { status } = info.file;
    if (status !== 'uploading') {
      const newFile = info.file.originFileObj || info.file;

      if (files.length >= 2) {
        message.warning("You can only compare 2 files. Please remove one to add another.");
        return;
      }

      setFiles((prev) => [...prev, newFile]);
    }
  };

  const handleRemoveFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // --- DB Selection Logic ---
  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await historyAPI.getIngestHistory();
      setHistoryData(res.data);
    } catch (error) {
      message.error("Failed to fetch history");
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleDbModalOpen = () => {
    setDbModalVisible(true);
    fetchHistory();
    setSelectedDbRecords([]);
  };

  const handleDbSelectionChange = (selectedRowKeys, selectedRows) => {
    if (selectedRows.length > 2) {
      message.warning("You can only select 2 guidelines to compare.");
      return;
    }
    setSelectedDbRecords(selectedRows);
  };

  const handleDbCompare = async () => {
    if (selectedDbRecords.length !== 2) {
      message.error("Please select exactly 2 records to compare.");
      return;
    }

    setDbModalVisible(false);

    // Start comparison with DB records
    const values = form.getFieldsValue();
    await startComparison(values, true);
  };

  // --- Comparison Logic ---
  const startComparison = async (values, isFromDb = false) => {
    try {
      setProcessing(true);
      setProgress(0);
      setProgressMessage("Starting comparison...");
      setProcessingModalVisible(true);

      // Fetch user's prompts
      let systemPrompt = "";
      let userPrompt = "";

      try {
        const promptsRes = await promptsAPI.getUserPrompts();
        systemPrompt = promptsRes.data.compare_prompts.system_prompt || "";
        userPrompt = promptsRes.data.compare_prompts.user_prompt || "";
      } catch (err) {
        console.warn("Could not fetch prompts from prompts API");
      }

      let res;
      if (isFromDb) {
        // DB Comparison
        const payload = {
          ingest_ids: selectedDbRecords.map(r => r.id),
          model_provider: values.model_provider,
          model_name: values.model_name,
          system_prompt: systemPrompt,
          user_prompt: userPrompt
        };
        res = await compareAPI.compareFromDB(payload);
      } else {
        // File Upload Comparison
        if (files.length < 2) {
          setProcessing(false);
          setProcessingModalVisible(false);
          return message.error("Please upload exactly 2 files to compare");
        }

        const fd = new FormData();
        fd.append("file1", files[0]);
        fd.append("file2", files[1]);
        fd.append("model_provider", values.model_provider);
        fd.append("model_name", values.model_name);
        fd.append("system_prompt", systemPrompt);
        fd.append("user_prompt", userPrompt);

        res = await compareAPI.compareGuidelines(fd);
      }

      const { session_id } = res.data;
      setSessionId(session_id);

      // Start SSE
      const es = compareAPI.createProgressStream(session_id);

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgress(data.progress || 0);
          setProgressMessage(data.message || "Processing...");

          if (data.status === "completed" || data.progress >= 100) {
            es.close();
            setProcessing(false);
            setProcessingModalVisible(false);

            setTimeout(() => {
              loadPreview(session_id);
            }, 500);

            message.success("Comparison complete!");
          } else if (data.status === "failed") {
            es.close();
            setProcessing(false);
            setProcessingModalVisible(false);
            message.error(data.error || "Comparison failed");
          }
        } catch (parseError) {
          console.error("Error parsing progress data:", parseError);
        }
      };

      es.onerror = (error) => {
        console.error("SSE error:", error);
        es.close();
        setProcessing(false);
        setProcessingModalVisible(false);
        message.error("Connection error. Please try again.");
      };

    } catch (err) {
      console.error("Submission error:", err);
      setProcessing(false);
      setProcessingModalVisible(false);
      message.error(err.response?.data?.detail || "Failed to start comparison");
    }
  };

  const handleSubmit = (values) => {
    startComparison(values, false);
  };

  const loadPreview = async (sid) => {
    try {
      const res = await compareAPI.getPreview(sid);
      const data = res.data;

      if (data?.length > 0) {
        const cols = Object.keys(data[0]).map((key) => ({
          title: key.replace(/_/g, " ").toUpperCase(),
          dataIndex: key,
          key,
          width: 250,
          render: (text) => (
            <div className="whitespace-pre-wrap text-sm">{String(text)}</div>
          ),
        }));
        setTableColumns(cols);
        setPreviewData(data);
        setPreviewModalVisible(true);
      } else {
        setTableColumns([{ title: "Result", dataIndex: "content" }]);
        setPreviewData([{ key: 1, content: "No structured comparison found" }]);
        setPreviewModalVisible(true);
      }
    } catch (error) {
      message.error("Failed to load preview: " + (error.response?.data?.detail || error.message));
    }
  };

  const convertRows = (data) =>
    (data || []).map((row, i) => ({ key: i, ...row }));

  const uploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    beforeUpload: () => false,
    onChange: handleFileChange,
    accept: ".pdf,.xlsx,.xls,.csv"
  };

  // Columns for DB Selection Modal
  const dbColumns = [
    {
      title: "S.no",
      key: "sno",
      width: 60,
      render: (_, __, index) => index + 1,
    },
    {
      title: "Investor",
      dataIndex: "investor",
      key: "investor",
    },
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
    },
    {
      title: "File Name",
      dataIndex: "uploadedFile",
      key: "uploadedFile",
    },
    {
      title: "Actions",
      key: "actions",
      width: 80,
      render: (_, record) => (
        <Tooltip title="View Details">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              // Could implement view details logic here if needed
            }}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <h1 className="text-2xl font-normal text-gray-700 mb-6">Compare Guidelines</h1>

      <Form
        form={form}
        onFinish={handleSubmit}
        layout="vertical"
        className="w-full"
      >
        {/* Model Selection Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Form.Item
            name="model_provider"
            className="mb-0"
          >
            <Select
              size="large"
              className="w-full"
              onChange={(v) => {
                setSelectedProvider(v);
                const defaultModel =
                  v === "gemini" ? "gemini-2.5-pro" : supportedModels[v]?.[0];
                form.setFieldsValue({ model_name: defaultModel });
              }}
            >
              <Option value="openai">OpenAI</Option>
              <Option value="gemini">Google Gemini</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="model_name"
            className="mb-0"
          >
            <Select size="large" className="w-full">
              {supportedModels[selectedProvider]?.map((model) => (
                <Option key={model} value={model}>
                  {model}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </div>

        {/* Attach Documents Section */}
        <div className="mb-8">
          <h2 className="text-xl font-normal text-gray-700 mb-4">Attach Documents</h2>

          <Dragger {...uploadProps} className="bg-gray-50 border-dashed border-2 border-gray-200 rounded-lg hover:border-blue-400 transition-colors mb-6">
            <div className="py-12">
              <p className="ant-upload-drag-icon mb-4">
                <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
              </p>
              <p className="text-lg text-blue-500 mb-2">
                Upload a file <span className="text-gray-500">or drag and drop</span>
              </p>
              <p className="text-gray-400 text-sm">
                pdf, csv, xlsx. up to 5MB
              </p>
            </div>
          </Dragger>

          {/* File Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {files.map((f, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 flex items-center justify-between bg-white shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <FileTextOutlined className="text-blue-500 text-xl" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-800 text-base truncate max-w-[200px]">{f.name}</p>
                    <p className="text-gray-500 text-xs">{(f.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
                <Button
                  danger
                  type="text"
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemoveFile(index)}
                  className="hover:bg-red-50"
                />
              </div>
            ))}

            {/* Empty placeholders if less than 2 files */}
            {Array.from({ length: Math.max(0, 2 - files.length) }).map((_, i) => (
              <div key={`empty-${i}`} className="border border-dashed border-gray-200 rounded-lg p-4 flex items-center justify-center bg-gray-50 h-[88px]">
                <span className="text-gray-400 text-sm">Upload a file to see it here</span>
              </div>
            ))}
          </div>
        </div>

        {/* Attach From DB Section */}
        <div className="mb-8">
          <h2 className="text-xl font-normal text-gray-700 mb-4">Attach From DB</h2>
          <div
            className="border border-dashed border-gray-200 rounded-lg p-6 bg-gray-50 flex items-center gap-4 cursor-pointer hover:border-blue-400 transition-colors"
            onClick={handleDbModalOpen}
          >
            <div className="bg-blue-50 p-2 rounded-lg">
              <CloudUploadOutlined className="text-blue-500 text-xl" />
            </div>
            <div>
              <p className="text-blue-500 font-medium">Upload</p>
              <p className="text-gray-400 text-sm">Select a file from DB</p>
            </div>
          </div>
        </div>

        {/* Submit Button Area */}
        <div className="flex justify-end">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="px-8 h-12 text-lg bg-blue-600 hover:bg-blue-700"
            loading={processing}
            disabled={files.length !== 2}
          >
            {processing ? "Processing..." : "Compare Guidelines"}
          </Button>
        </div>
      </Form>

      {/* Processing Modal */}
      <Modal
        open={processingModalVisible}
        footer={null}
        closable={false}
        centered
        title={
          <div className="flex items-center gap-2">
            <LoadingOutlined className="text-blue-500" />
            <span>Processing Comparison...</span>
          </div>
        }
      >
        <div className="py-6">
          <Progress
            percent={Math.round(progress)}
            status={progress >= 100 ? "success" : "active"}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          <p className="mt-4 text-gray-600 text-center">{progressMessage}</p>
        </div>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title="Comparison Results"
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        width="90%"
        footer={[
          <Button key="close" onClick={() => setPreviewModalVisible(false)}>
            Close
          </Button>,
          <Button
            key="download"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => compareAPI.downloadExcel(sessionId)}
          >
            Download Excel
          </Button>,
        ]}
      >
        <div className="max-h-[70vh] overflow-auto">
          <Table
            dataSource={convertRows(previewData)}
            columns={tableColumns}
            pagination={{ pageSize: 50 }}
            scroll={{ y: "calc(90vh - 200px)", x: "max-content" }}
            bordered
            size="middle"
          />
        </div>
      </Modal>

      {/* Attach From DB Modal */}
      <Modal
        title="Attach From DB"
        open={dbModalVisible}
        onCancel={() => setDbModalVisible(false)}
        width={1000}
        footer={[
          <Button key="cancel" onClick={() => setDbModalVisible(false)}>
            Cancel
          </Button>,
          <Button
            key="compare"
            type="primary"
            icon={<SwapOutlined />}
            disabled={selectedDbRecords.length !== 2}
            onClick={handleDbCompare}
          >
            Compare
          </Button>,
        ]}
      >
        <Table
          dataSource={historyData}
          columns={dbColumns}
          rowKey="id"
          loading={loadingHistory}
          pagination={{ pageSize: 10 }}
          rowSelection={{
            type: "checkbox",
            selectedRowKeys: selectedDbRecords.map(r => r.id),
            onChange: (keys, rows) => handleDbSelectionChange(keys, rows),
            getCheckboxProps: (record) => ({
              disabled: selectedDbRecords.length >= 2 && !selectedDbRecords.find(r => r.id === record.id),
            }),
          }}
        />
      </Modal>
    </div>
  );
};

export default ComparePage;
