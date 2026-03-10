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
  SearchOutlined,
  FileOutlined,
} from "@ant-design/icons";
import "./ComparePage.css";
import { usePrompts } from "../../context/PromptContext";
import { useAuth } from "../../context/AuthContext";
import { compareAPI, settingsAPI, promptsAPI, historyAPI, ingestAPI } from "../../services/api";
const ExcelPreviewModal = React.lazy(() => import("../../components/ExcelPreviewModal"));
import { showToast } from "../../utils/toast";
import { CompareSkeleton } from "../../components/common/SkeletonLoader";

const { Dragger } = Upload;
const { Option } = Select;

const renderFileNames = (text) => {
  if (!text) return "-";
  const files = typeof text === 'string' ? text.split(',').map(f => f.trim()).filter(Boolean) : [text];
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
      {files.map((file, idx) => (
        <Tag
          key={idx}
          color="blue"
          style={{
            margin: 0,
            whiteSpace: 'normal',
            height: 'auto',
            padding: '2px 8px',
            wordBreak: 'break-word',
            lineHeight: '1.5'
          }}
        >
          {file}
        </Tag>
      ))}
    </div>
  );
};

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
  const [file1Display, setFile1Display] = useState(null);
  const [file2Display, setFile2Display] = useState(null);

  // DB Selection State
  const [historyData, setHistoryData] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedDbRecords, setSelectedDbRecords] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    fetchModelsAndSettings();
    fetchHistory();
  }, []);

  const fetchModelsAndSettings = async () => {
    try {
      // Fetch supported models (available to all users)
      const modelsRes = await settingsAPI.getSupportedModels();
      setSupportedModels(modelsRes.data);

      // Only fetch settings if user is admin
      if (isAdmin) {
        try {
          const settingsRes = await settingsAPI.getSettings();
          const settings = settingsRes.data;

          if (settings.default_model_provider && settings.default_model_name) {
            form.setFieldsValue({
              model_provider: settings.default_model_provider,
              model_name: settings.default_model_name,
            });
            setSelectedProvider(settings.default_model_provider);
            return;
          }
        } catch (settingsError) {
          console.warn("Failed to fetch settings:", settingsError);
        }
      }

      // Fallback defaults for non-admin or if settings fetch fails
      form.setFieldsValue({
        model_provider: "openai",
        model_name: "gpt-4o",
      });
      setSelectedProvider("openai");
    } catch (error) {
      console.error("Failed to fetch models:", error);
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
    } finally {
      setPageLoading(false);
    }
  };

  const handleFileChange = (info) => {
    const { status } = info.file;
    if (status !== 'uploading') {
      const newFile = info.file.originFileObj || info.file;

      // Check if it's an Excel file
      const isExcel = newFile.name.endsWith('.xlsx') || newFile.name.endsWith('.xls');
      if (!isExcel) {
        showToast.error('Please upload Excel files only (XLSX or XLS)');
        return;
      }

      if (files.length >= 2) {
        showToast.warning("You can only compare 2 files. Please remove one to add another.");
        return;
      }

      setFiles((prev) => [...prev, newFile]);
      showToast.success(`${newFile.name} added successfully`);
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
      // Toast is handled by API interceptor
    } finally {
      setLoadingHistory(false);
    }
  };



  const handleDbSelectionChange = (selectedRowKeys, selectedRows) => {
    if (selectedRows.length > 2) {
      showToast.warning("You can only select 2 guidelines to compare.");
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
      showToast.error("Please select exactly 2 records to compare.");
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
      setProgress(25); // Set to 25% initially for immediate feedback
      setProgressMessage("Starting comparison...");
      setProcessingModalVisible(true);

      // Fetch user's prompts
      let systemPrompt = "";
      let userPrompt = "";

      // Ensure model values are present (default to OpenAI if not set/admin)
      const modelProvider = values.model_provider || selectedProvider || "openai";
      const modelName = values.model_name || form.getFieldValue("model_name") || "gpt-4o";

      try {
        const promptsRes = await promptsAPI.getUserPrompts();

        // Get prompts for the specific model
        const modelPrompts = promptsRes.data.compare_prompts[modelProvider] || promptsRes.data.compare_prompts.openai || {};

        systemPrompt = modelPrompts.system_prompt || "";
        userPrompt = modelPrompts.user_prompt || "";
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
          user_prompt: userPrompt,
          investor: values.investor || " - ",
          version: values.version || " - "
        };
        res = await compareAPI.compareFromDB(payload);
      } else {
        // File Upload Comparison
        if (files.length < 2) {
          setProcessing(false);
          setProcessingModalVisible(false);
          return showToast.error("Please upload exactly 2 files to compare");
        }

        const fd = new FormData();
        fd.append("file1", files[0]);
        fd.append("file2", files[1]);

        // Add model provider and model name for LLM comparison
        fd.append("model_provider", modelProvider);
        fd.append("model_name", modelName);

        // Add prompts for LLM comparison
        fd.append("system_prompt", systemPrompt);
        fd.append("user_prompt", userPrompt);

        // Add investor and version
        fd.append("investor", values.investor || " - ");
        fd.append("version", values.version || " - ");

        // Use DSCR template comparison processor (same as DB comparison)
        res = await compareAPI.compareGuidelines(fd);
      }

      const { session_id } = res.data;
      setSessionId(session_id);

      // Start SSE
      const es = compareAPI.createProgressStream(session_id);

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Map server progress (0-100) to UI progress (25-100)
          const serverProgress = data.progress || 0;
          const displayProgress = Math.max(25, 25 + (serverProgress * 0.75));
          setProgress(displayProgress);
          setProgressMessage(data.message || "Processing...");

          if (data.status === "completed" || data.progress >= 100) {
            es.close();
            setProcessing(false);
            setProcessingModalVisible(false);

            // Clear form, files, and DB selections for next comparison
            form.resetFields();
            setFiles([]);
            setSelectedDbRecords([]);

            setTimeout(() => {
              loadPreview(session_id);
            }, 500);

            showToast.success("Comparison complete!");
          } else if (data.status === "failed") {
            es.close();
            setProcessing(false);
            setProcessingModalVisible(false);
            showToast.error(data.error || "Comparison failed");
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
        showToast.error("Connection error. Please try again.");
      };

    } catch (err) {
      console.error("Submission error:", err);
      setProcessing(false);
      setProcessingModalVisible(false);
      // Toast is handled by API interceptor
    }
  };

  const handleSubmit = (values) => {
    startComparison(values, false);
  };

  const loadPreview = async (sid) => {
    try {
      setIsComparePreview(true);
      const res = await compareAPI.getPreview(sid);
      const responseData = res.data;

      let previewDataArray = [];
      if (responseData && typeof responseData === 'object' && 'data' in responseData) {
        previewDataArray = responseData.data;
        if (responseData.file1_name) setFile1Display(responseData.file1_name.replace(/\.xlsx?$/, ''));
        if (responseData.file2_name) setFile2Display(responseData.file2_name.replace(/\.xlsx?$/, ''));
      } else {
        previewDataArray = responseData;
        setFile1Display(null);
        setFile2Display(null);
      }

      if (previewDataArray?.length > 0) {
        setPreviewData(previewDataArray);
        setPreviewModalVisible(true);
      } else {
        setPreviewData([{ key: 1, content: "No structured comparison found" }]);
        setPreviewModalVisible(true);
      }
    } catch (error) {
      // Toast is handled by API interceptor
    }
  };

  const handleViewDetails = async (record) => {
    try {
      setIsComparePreview(false);

      const res = await ingestAPI.getPreview(record.id);

      // Handle new response format: { data: [...], history_id: "..." }
      const responseData = res.data;
      let previewDataArray;
      let historyId = null;

      if (responseData && typeof responseData === 'object' && 'data' in responseData) {
        // New format: { data: [...], history_id: "..." }
        previewDataArray = responseData.data;
        historyId = responseData.history_id || record.id;
      } else {
        // Old format: directly an array (for backward compatibility)
        previewDataArray = responseData;
        historyId = record.id;
      }

      setSessionId(historyId); // Use history_id for PDF viewing
      setPreviewData(previewDataArray || []);
      setPreviewModalVisible(true);

      if (!previewDataArray || previewDataArray.length === 0) {
        showToast.info("No structured preview data found for this file");
      }
    } catch (error) {
      console.error("Failed to load details:", error);
      // Toast is handled by API interceptor
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
      render: (text) => text || " - ",
    },
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
      render: (text) => text || " - ",
    },
    {
      title: "File Name",
      dataIndex: "uploadedFile",
      key: "uploadedFile",
      render: renderFileNames,
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

  // Calculate columns for preview, excluding unwanted internal fields
  const previewColumns = React.useMemo(() => {
    if (!previewData || previewData.length === 0) return null;

    // Get all available keys from the first record
    const allKeys = Object.keys(previewData[0]);

    // Define columns to hide
    const hiddenColumns = ['Classification', 'Notes', '_verification', 'key', 'PPE_Field_Type', 'verification'];

    // If it's comparison mode, we hide some extra internal fields here or inside ExcelPreviewModal. 
    // ExcelPreviewModal handles most, but we can override titles.

    // Filter available keys
    const visibleKeys = allKeys.filter(key => !hiddenColumns.includes(key));

    // Map to column objects expected by ExcelPreviewModal
    return visibleKeys.map(key => {
      // Rename Hard_Soft_Classification to PPE FIELD TYPE
      if (key.toLowerCase() === 'hard_soft_classification') {
        return {
          title: "PPE FIELD TYPE",
          dataIndex: key,
          key: key
        };
      }

      // Override comparison file names
      if (isComparePreview) {
        if (key === 'guideline_1' && file1Display) {
          return { title: file1Display, dataIndex: key, key: key };
        }
        if (key === 'guideline_2' && file2Display) {
          return { title: file2Display, dataIndex: key, key: key };
        }
      }

      return {
        dataIndex: key,
        key: key,
        render: (text) => text || " - "
      };
    });
  }, [previewData, isComparePreview, file1Display, file2Display]);

  if (pageLoading) {
    return <CompareSkeleton />;
  }

  return (
    <div className="compare-container">
      {/* <h1 className="text-2xl font-normal text-gray-700 mb-6">Compare Guidelines</h1> */}

      <Form
        form={form}
        onFinish={handleSubmit}
        layout="vertical"
        className="w-full"
      >
        {/* Model Selection Row - Admin Only */}
        {/* {isAdmin && (
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
        )} */}

        {/* Document Context Card */}
        <div className="compare-card">
          <div className="compare-card-title">
            <FileTextOutlined /> Document Context
          </div>
          <p className="compare-card-subtitle">Provide details for the final comparison document</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Form.Item
              name="investor"
              label="Investor"
              className="mb-0"
            >
              <Input
                placeholder="Enter investor name"
                size="large"
              />
            </Form.Item>

            <Form.Item
              name="version"
              label="Version"
              className="mb-0"
            >
              <Input
                placeholder="Enter version (e.g., v1, v2)"
                size="large"
              />
            </Form.Item>
          </div>
        </div>

        {/* Database Selection Section */}
        {/* Database Selection Card */}
        <div className="compare-card">
          <div className="compare-card-title">
            <CloudUploadOutlined /> Access the stored information
          </div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-gray-500 text-sm">Select exactly 2 guidelines to compare</p>
            <Input
              placeholder="Search history..."
              prefix={<SearchOutlined className="text-gray-400" />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="w-80"
              size="large"
              allowClear
            />
          </div>

          <div className="compare-table-wrapper mb-6">
            <Table
              dataSource={filteredHistoryData}
              columns={dbColumns}
              rowKey="id"
              loading={loadingHistory}
              pagination={{
                pageSize: 3,
                showSizeChanger: true,
                pageSizeOptions: ["3", "5", "10"],
                showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`,
                position: ["bottomRight"],
              }}
              rowSelection={{
                type: "checkbox",
                selectedRowKeys: selectedDbRecords.map((r) => r.id),
                onChange: (keys, rows) => handleDbSelectionChange(keys, rows),
                getCheckboxProps: (record) => ({
                  disabled: selectedDbRecords.length >= 2 && !selectedDbRecords.find((r) => r.id === record.id),
                }),
              }}
              scroll={{ x: 800 }}
            />
          </div>

          {selectedDbRecords.length === 2 && (
            <div className="flex justify-center">
              <Button
                type="primary"
                size="large"
                icon={<SwapOutlined />}
                onClick={handleDbCompare}
                className="db-compare-btn"
              >
                Compare Selected Pair
              </Button>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="compare-divider">
          <span className="compare-divider-text">OR</span>
        </div>

        {/* Local File Upload Section */}
        <div className="compare-card">
          <div className="compare-card-title">
            <InboxOutlined /> Upload Local Files
          </div>
          <p className="compare-card-subtitle">Select exactly 2 Excel files from your device</p>

          {files.length < 2 ? (
            <div className="compare-upload-wrapper mb-6">
              <Dragger
                {...uploadProps}
                className="!border-none"
                style={{ background: 'transparent' }}
              >
                <div className="py-8">
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined style={{ fontSize: '40px', color: '#3b82f6' }} />
                  </p>
                  <p className="text-base font-semibold text-gray-700">
                    Click or drag Excel files to upload
                  </p>
                  <p className="text-gray-500 text-xs mt-1">
                    {files.length}/2 files selected
                  </p>
                </div>
              </Dragger>
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-6">
              <p className="text-green-600 text-sm font-semibold text-center m-0">
                ✓ Ready to compare local files
              </p>
            </div>
          )}

          {/* File Cards */}
          {files.length > 0 && (
            <div className="compare-files-grid mb-6">
              {files.map((f, index) => (
                <div key={index} className="compare-file-item">
                  <div className="compare-file-info">
                    <div className="compare-file-icon-box">
                      <FileOutlined />
                    </div>
                    <div>
                      <p className="compare-file-name truncate">{f.name}</p>
                      <p className="compare-file-size">{(f.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <Button
                    danger
                    type="text"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveFile(index)}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Submit Button for Local Files */}
          {files.length === 2 && (
            <div className="flex justify-center">
              <Button
                type="primary"
                size="large"
                htmlType="submit"
                loading={processing}
                className="compare-submit-btn"
              >
                {processing ? "Processing..." : "Compare Selected Pair"}
              </Button>
            </div>
          )}
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
      <React.Suspense fallback={<Modal open={previewModalVisible} footer={null} closable={false} centered><div className="p-10 text-center"><Spin size="large" tip="Loading preview..." /></div></Modal>}>
        <ExcelPreviewModal
          visible={previewModalVisible}
          onClose={() => setPreviewModalVisible(false)}
          title={isComparePreview ? "Comparison Results" : "Extraction Results"}
          data={previewData}
          columns={previewColumns}
          onDownload={() => {
            if (isComparePreview) {
              compareAPI.downloadExcel(sessionId);
            } else {
              ingestAPI.downloadExcel(sessionId);
            }
          }}
          sessionId={sessionId}
          isComparisonMode={isComparePreview}
        />
      </React.Suspense>
    </div>
  );
};

export default ComparePage;
