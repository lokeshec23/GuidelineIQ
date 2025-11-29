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
  Tooltip,
  Input
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
  EyeOutlined,
  SearchOutlined
} from "@ant-design/icons";
import { usePrompts } from "../../context/PromptContext";
import { useAuth } from "../../context/AuthContext";
import { compareAPI, settingsAPI, promptsAPI, historyAPI, ingestAPI } from "../../services/api";
import ExcelPreviewModal from "../../components/ExcelPreviewModal";

const { Dragger } = Upload;
const { Option } = Select;

const ComparePage = () => {
  const { isAdmin } = useAuth();
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
  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [isComparePreview, setIsComparePreview] = useState(false);

  // DB Selection State
  const [historyData, setHistoryData] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedDbRecords, setSelectedDbRecords] = useState([]);
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    fetchModelsAndSettings();
    fetchHistory();
  }, []);

  const fetchModelsAndSettings = async () => {
    try {
      const [modelsRes, settingsRes] = await Promise.all([
        settingsAPI.getSupportedModels(),
        settingsAPI.getSettings(),
      ]);

      setSupportedModels(modelsRes.data);

      const settings = settingsRes.data;
      if (settings.default_model_provider && settings.default_model_name) {
        form.setFieldsValue({
          model_provider: settings.default_model_provider,
          model_name: settings.default_model_name,
        });
        setSelectedProvider(settings.default_model_provider);
      } else {
        // Fallback defaults
        form.setFieldsValue({
          model_provider: "openai",
          model_name: "gpt-4o",
        });
        setSelectedProvider("openai");
      }
    } catch (error) {
      console.error("Failed to fetch models or settings:", error);
      // Fallback if API fails
      setSupportedModels({
        openai: ["gpt-4o"],
        gemini: ["gemini-2.5-pro"],
      });
      form.setFieldsValue({
        model_provider: "openai",
        model_name: "gpt-4o",
      });
      setSelectedProvider("openai");
    }
  };

  const handleFileChange = (info) => {
    const { status } = info.file;
    if (status !== 'uploading') {
      const newFile = info.file.originFileObj || info.file;

      // Check if it's an Excel file
      const isExcel = newFile.name.endsWith('.xlsx') || newFile.name.endsWith('.xls');
      if (!isExcel) {
        message.error('Please upload Excel files only (XLSX or XLS)');
        return;
      }

      if (files.length >= 2) {
        message.warning("You can only compare 2 files. Please remove one to add another.");
        return;
      }

      setFiles((prev) => [...prev, newFile]);
      message.success(`${newFile.name} added successfully`);
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



  const handleDbSelectionChange = (selectedRowKeys, selectedRows) => {
    if (selectedRows.length > 2) {
      message.warning("You can only select 2 guidelines to compare.");
      return;
    }
    setSelectedDbRecords(selectedRows);
  };

  // Filter history data based on search text
  const filteredHistoryData = historyData.filter((record) => {
    const searchLower = searchText.toLowerCase();
    return (
      record.investor?.toLowerCase().includes(searchLower) ||
      record.version?.toLowerCase().includes(searchLower) ||
      record.uploadedFile?.toLowerCase().includes(searchLower)
    );
  });

  const handleDbCompare = async () => {
    if (selectedDbRecords.length !== 2) {
      message.error("Please select exactly 2 records to compare.");
      return;
    }

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

      // Ensure model values are present (default to OpenAI if not set/admin)
      const modelProvider = values.model_provider || selectedProvider || "openai";
      const modelName = values.model_name || "gpt-4o";

      try {
        const promptsRes = await promptsAPI.getUserPrompts();

        // Get prompts for the specific model
        const modelPrompts = promptsRes.data.compare_prompts[modelProvider] || promptsRes.data.compare_prompts.openai || {};

        systemPrompt = modelPrompts.system_prompt || "";
        userPrompt = modelPrompts.user_prompt || "";
        console.log(`✅ Fetched compare prompts for ${modelProvider}`);
      } catch (err) {
        console.warn("Could not fetch prompts from prompts API");
      }



      let res;
      if (isFromDb) {
        // DB Comparison
        const payload = {
          ingest_ids: selectedDbRecords.map(r => r.id),
          model_provider: modelProvider,
          model_name: modelName,
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
        fd.append("model_provider", modelProvider);
        fd.append("model_name", modelName);
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
      setIsComparePreview(true);
      const res = await compareAPI.getPreview(sid);
      const data = res.data;

      if (data?.length > 0) {
        setPreviewData(data);
        setPreviewModalVisible(true);
      } else {
        setPreviewData([{ key: 1, content: "No structured comparison found" }]);
        setPreviewModalVisible(true);
      }
    } catch (error) {
      message.error("Failed to load preview: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleViewDetails = async (record) => {
    try {
      setIsComparePreview(false);
      setSessionId(record.id);

      const res = await ingestAPI.getPreview(record.id);

      setPreviewData(res.data || []);
      setPreviewModalVisible(true);

      if (!res.data || res.data.length === 0) {
        message.info("No structured preview data found for this file");
      }
    } catch (error) {
      console.error("Failed to load details:", error);
      message.error("Failed to load details: " + (error.response?.data?.detail || error.message));
    }
  };

  const uploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    beforeUpload: () => false,
    onChange: handleFileChange,
    accept: ".xlsx,.xls"
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
        <div onClick={(e) => e.stopPropagation()}>
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                handleViewDetails(record);
              }}
            />
          </Tooltip>
        </div>
      ),
    },
  ];

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      {/* <h1 className="text-2xl font-normal text-gray-700 mb-6">Compare Guidelines</h1> */}

      <Form
        form={form}
        onFinish={handleSubmit}
        layout="vertical"
        className="w-full"
      >
        {/* Model Selection Row - Admin Only */}
        {isAdmin && (
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
        )}

        {/* Database Selection Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {/* <h2 className="text-base font-medium text-gray-700" style={{ fontFamily: 'Jura, sans-serif' }}>
              Select from Database <span className="text-sm text-gray-500 font-normal">(Select exactly 2 guidelines)</span>
            </h2> */}
            <Input
              placeholder="Search by investor, version, or file name..."
              prefix={<SearchOutlined className="text-gray-400" />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="w-80"
              size="large"
              allowClear
            />
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
            <Table
              dataSource={filteredHistoryData}
              columns={dbColumns}
              rowKey="id"
              loading={loadingHistory}
              pagination={{
                pageSize: 3,
                showSizeChanger: true,
                pageSizeOptions: ['3', '5', '10'],
                showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`
              }}
              rowSelection={{
                type: "checkbox",
                selectedRowKeys: selectedDbRecords.map(r => r.id),
                onChange: (keys, rows) => handleDbSelectionChange(keys, rows),
                getCheckboxProps: (record) => ({
                  disabled: selectedDbRecords.length >= 2 && !selectedDbRecords.find(r => r.id === record.id),
                }),
              }}
              scroll={{ x: 800 }}
            />
          </div>

          {selectedDbRecords.length === 2 && (
            <div className="flex justify-center mb-4">
              <Button
                type="primary"
                icon={<SwapOutlined />}
                onClick={handleDbCompare}
                size="large"
                className="px-8 bg-green-600 hover:bg-green-700"
              >
                Compare Selected Guidelines
              </Button>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="relative mb-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-gray-50 text-gray-500 font-medium" style={{ fontFamily: 'Jura, sans-serif' }}>OR</span>
          </div>
        </div>

        {/* Local File Upload Section */}
        <div className="mb-8">
          <h2 className="text-base font-medium text-gray-700 mb-3" style={{ fontFamily: 'Jura, sans-serif' }}>
            Upload Local Files <span className="text-sm text-gray-500 font-normal">(Select exactly 2 Excel files)</span>
          </h2>

          {files.length < 2 ? (
            <Dragger
              {...uploadProps}
              className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-dashed border-blue-300 rounded-lg hover:border-blue-500 hover:bg-blue-100 transition-all duration-200 mb-4"
              style={{ padding: '16px' }}
            >
              <div className="py-6">
                <p className="ant-upload-drag-icon mb-2">
                  <InboxOutlined style={{ fontSize: '36px', color: '#3b82f6' }} />
                </p>
                <p className="text-base font-medium text-blue-600 mb-1" style={{ fontFamily: 'Jura, sans-serif' }}>
                  Click to upload or drag and drop
                </p>
                <p className="text-gray-500 text-xs mb-1" style={{ fontFamily: 'Jura, sans-serif' }}>
                  Excel files only
                </p>
                <p className="text-blue-500 text-xs font-medium" style={{ fontFamily: 'Jura, sans-serif' }}>
                  {files.length}/2 files selected
                </p>
              </div>
            </Dragger>
          ) : (
            <div className="bg-green-50 border-2 border-green-300 rounded-lg p-4 mb-4">
              <p className="text-green-700 text-sm font-medium text-center" style={{ fontFamily: 'Jura, sans-serif' }}>
                ✓ Both files selected. Ready to compare!
              </p>
            </div>
          )}

          {/* File Cards */}
          {files.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {files.map((f, index) => (
                <div
                  key={index}
                  className="border-2 border-blue-200 bg-blue-50 rounded-lg p-3 flex items-center justify-between transition-all duration-200 hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <div className="bg-blue-100 p-2 rounded-lg">
                      <FileTextOutlined className="text-blue-600 text-base" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 text-sm truncate" style={{ fontFamily: 'Jura, sans-serif' }}>
                        {f.name}
                      </p>
                      <p className="text-gray-500 text-xs" style={{ fontFamily: 'Jura, sans-serif' }}>
                        {(f.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Button
                    danger
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveFile(index)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit Button for Local Files */}
        {files.length === 2 && (
          <div className="flex justify-center">
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              className="px-8 h-12 text-lg bg-blue-600 hover:bg-blue-700"
              loading={processing}
            >
              {processing ? "Processing..." : "Compare Local Files"}
            </Button>
          </div>
        )}
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
      <ExcelPreviewModal
        visible={previewModalVisible}
        onClose={() => setPreviewModalVisible(false)}
        title="Comparison Results"
        data={previewData}
        onDownload={() => {
          if (isComparePreview) {
            compareAPI.downloadExcel(sessionId);
          } else {
            ingestAPI.downloadExcel(sessionId);
          }
        }}
        sessionId={sessionId}
      />
    </div>
  );
};

export default ComparePage;
