// src/pages/Ingest/IngestPage.jsx

import React, { useState, useEffect } from "react";
import {
  Form,
  Select,
  Button,
  Input,
  message,
  Modal,
  Table,
  Tag,
  Space,
  Spin,
  Upload,
  DatePicker,
  Progress,
} from "antd";
import {
  InboxOutlined,
  FileTextOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  LoadingOutlined,
  DeleteOutlined,
  BankOutlined,
  CheckCircleFilled,
  AppstoreOutlined,
  PlusCircleOutlined,
  FileOutlined,
} from "@ant-design/icons";
import "./IngestPage.css";
import { usePrompts } from "../../context/PromptContext";
import { useAuth } from "../../context/AuthContext";
import { ingestAPI, settingsAPI, promptsAPI, investorAPI, dscrAPI, guidelineTypeAPI } from "../../services/api";
const ExcelPreviewModal = React.lazy(() => import("../../components/ExcelPreviewModal"));
import { showToast, getErrorMessage } from "../../utils/toast";
import { IngestSkeleton } from "../../components/common/SkeletonLoader";

const { Dragger } = Upload;
const { Option } = Select;

const IngestPage = () => {
  const { isAdmin } = useAuth();
  const [form] = Form.useForm();
  const { ingestPrompts } = usePrompts();

  // --- STATE ---
  const [files, setFiles] = useState([]); // ✅ Changed to array for multiple files
  const [guidelineTypes, setGuidelineTypes] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0); // ✅ Progress state
  const [progressMessage, setProgressMessage] = useState(""); // ✅ Progress message state
  const [previewData, setPreviewData] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [supportedModels, setSupportedModels] = useState({
    openai: [],
    gemini: [],
  });
  const [selectedProvider, setSelectedProvider] = useState("openai");
  const [investors, setInvestors] = useState([]);
  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [currentInvestor, setCurrentInvestor] = useState("");
  const [currentVersion, setCurrentVersion] = useState("");

  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    fetchModelsAndSettings();
    fetchInvestors();
    fetchGuidelineTypes();
  }, []);

  const fetchGuidelineTypes = async () => {
    try {
      const response = await guidelineTypeAPI.listTypes();
      const types = response.data || [];
      setGuidelineTypes(types);
      const typeNames = types.map(t => t.name);
      setSelectedCategories(typeNames);
      form.setFieldsValue({ guideline_type: typeNames });
    } catch (error) {
      console.error("Failed to fetch guideline types:", error);
    }
  };

  const fetchInvestors = async () => {
    try {
      const response = await investorAPI.listInvestors();
      setInvestors(response.data);
    } catch (error) {
      console.error("Failed to fetch investors:", error);
    }
  };

  const fetchModelsAndSettings = async () => {
    try {
      setPageLoading(true);
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

  // --- FILE HANDLERS ---
  const handleFileChange = (info) => {
    // ✅ Handle multiple files
    const { fileList } = info;

    // Extract actual file objects
    const actualFiles = fileList.map(f => f.originFileObj || f);
    setFiles(actualFiles);
  };

  const handleRemoveFile = (fileToRemove) => {
    setFiles(prevFiles => prevFiles.filter(f => f !== fileToRemove));
  };

  const handleRemoveAllFiles = () => {
    setFiles([]);
  };

  // --- MAIN SUBMIT ---
  const handleSubmit = async (values) => {
    // if (!files || files.length === 0) return showToast.error("Please upload at least one PDF file");

    try {
      // Validate that the selected investor context has at least one parameter
      const investorIdForCheck = values.guideline_investor_id || "null";
      try {
        const paramsRes = await dscrAPI.listParameters(investorIdForCheck);
        if (!paramsRes.data || paramsRes.data.length === 0) {
          showToast.error("Parameters are empty");
          return;
        }
      } catch (err) {
        console.error("Failed to validate parameters:", err);
        showToast.error("Failed to validate parameters");
        return;
      }

      setProcessing(true);
      setProgress(25); // Set to 25% initially for immediate feedback
      setProgressMessage("Starting ingestion...");
      setProcessingModalVisible(true);

      // ✅ Fetch user's prompts from prompts API
      let systemPrompt = "";
      let userPrompt = "";

      // Determine provider and model (values might be missing if not admin)
      const modelProvider = values.model_provider || selectedProvider || "openai";
      const modelName = values.model_name || form.getFieldValue("model_name") || "gpt-4o";

      try {
        const promptsRes = await promptsAPI.getUserPrompts();

        // Get prompts for the specific model
        const modelPrompts = promptsRes.data.ingest_prompts[modelProvider] || promptsRes.data.ingest_prompts.openai || {};

        systemPrompt = modelPrompts.system_prompt || "";
        userPrompt = modelPrompts.user_prompt || "";
      } catch (err) {
        console.warn("⚠️ Could not fetch prompts from prompts API, using empty strings");
      }

      // Find investor name from selected ID
      let selectedInvestorName = "General";
      const selectedId = values.guideline_investor_id || "null";
      
      if (selectedId !== "null") {
        const inv = investors.find(i => String(i.id) === String(selectedId));
        if (inv) selectedInvestorName = inv.name;
      }

      const formData = new FormData();
      // ✅ Append all files
      files.forEach((file) => {
        formData.append("files", file); // Note: 'files' matches backend List[UploadFile]
      });
      formData.append("investor", selectedInvestorName);
      formData.append("investor_id", selectedId);
      formData.append("version", values.version || "");
      formData.append("model_provider", modelProvider);
      formData.append("model_name", modelName);

      // Attach dates (only if provided)
      if (values.effective_date) {
        formData.append("effective_date", values.effective_date.toISOString());
      }
      if (values.expiry_date) {
        formData.append("expiry_date", values.expiry_date.toISOString());
      }

      // Attach prompts from settings
      formData.append("system_prompt", systemPrompt);
      formData.append("user_prompt", userPrompt);

      // Attach new metadata fields
      if (values.page_range) formData.append("page_range", values.page_range);
      if (values.guideline_type && values.guideline_type.length > 0) {
        // Join array into comma-separated string for backend
        formData.append("guideline_type", values.guideline_type.join(","));
      }
      if (values.program_type) formData.append("program_type", values.program_type);

      const res = await ingestAPI.ingestGuideline(formData);
      const { session_id, status } = res.data;

      setSessionId(session_id);
      setCurrentInvestor(selectedInvestorName);
      setCurrentVersion(values.version || "v1");

      // Start SSE for progress tracking
      const es = ingestAPI.createProgressStream(session_id);

      es.onmessage = async (event) => {
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

            showToast.success("Processing complete!");

            // Store current model selection before clearing
            const currentModelProvider = form.getFieldValue('model_provider');
            const currentModelName = form.getFieldValue('model_name');

            // Clear form and files for next ingestion
            form.resetFields();
            setFiles([]);

            // Restore model selection
            if (currentModelProvider && currentModelName) {
              form.setFieldsValue({
                model_provider: currentModelProvider,
                model_name: currentModelName,
              });
            }

            // Load preview
            await loadPreview(session_id);

          } else if (data.status === "failed") {
            es.close();
            setProcessing(false);
            setProcessingModalVisible(false);
            showToast.error(data.error || "Processing failed");
          }
        } catch (parseError) {
          console.error("Error parsing progress data:", parseError);
        }
      };

      es.onerror = (error) => {
        console.error("SSE error:", error);
        es.close();
        // Don't close modal immediately on SSE error, might be temporary
        // setProcessing(false); 
        // setProcessingModalVisible(false);
        // showToast.error("Connection error. Please check status manually.");
      };


    } catch (err) {
      console.error("Submission error:", err);
      setProcessing(false);
      setProcessingModalVisible(false);

      const errorMessage = getErrorMessage(err);

      if (errorMessage && errorMessage.includes("Duplicate ingestion")) {
        showToast.warning(errorMessage)
      } else {
        showToast.error(errorMessage);
      }
    }
  };


  // --- LOAD PREVIEW ---
  const loadPreview = async (sid) => {
    try {
      const res = await ingestAPI.getPreview(sid);

      // Handle new response format: { data: [...], history_id: "..." }
      const responseData = res.data;
      let previewDataArray;
      let historyId = null;

      if (responseData && typeof responseData === 'object' && 'data' in responseData) {
        // New format: { data: [...], history_id: "..." }
        previewDataArray = responseData.data;
        historyId = responseData.history_id || sid; // Use history_id if available, fallback to sid
      } else {
        // Old format: directly an array (for backward compatibility)
        previewDataArray = responseData;
        historyId = sid;
      }

      const hasData = previewDataArray && (Array.isArray(previewDataArray) ? previewDataArray.length > 0 : Object.keys(previewDataArray).length > 0);

      if (hasData) {
        setPreviewData(previewDataArray);
        setSessionId(historyId);
        if (responseData.investor) setCurrentInvestor(responseData.investor);
        if (responseData.version) setCurrentVersion(responseData.version);
        setPreviewModalVisible(true);
      } else {
        setPreviewData([{ key: 1, content: "No structured data found." }]);
        setSessionId(historyId);
        setPreviewModalVisible(true);
      }
    } catch (error) {
      console.error("Failed to load preview:", error);
      // Toast is handled by API interceptor
    }
  };


  const uploadProps = {
    name: 'files',
    multiple: true, // ✅ Enable multiple file selection
    showUploadList: false,
    beforeUpload: () => false,
    onChange: handleFileChange,
    accept: ".pdf",
    fileList: files.map((f, idx) => ({
      uid: idx,
      name: f.name,
      status: 'done',
      originFileObj: f
    }))
  };

  // Calculate columns for preview, excluding unwanted internal fields
  const previewColumns = React.useMemo(() => {
    // Get data to check for headers (handle both array and object/multi-tab formats)
    const firstTabKey = !Array.isArray(previewData) && previewData ? Object.keys(previewData)[0] : null;
    const dataForKeys = Array.isArray(previewData) ? previewData[0] : (firstTabKey ? previewData[firstTabKey][0] : null);

    if (!dataForKeys) return null;

    // Get all available keys
    const allKeys = Object.keys(dataForKeys);

    // Define columns to hide
    const hiddenColumns = ['Classification', 'Notes', '_verification', 'key', 'PPE_Field_Type'];

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
      return {
        // title: key, // Let ExcelPreviewModal handle formatting
        dataIndex: key,
        key: key,
        render: (text) => text || "-"
      };
    });
  }, [previewData]);

  if (pageLoading) {
    return <IngestSkeleton />;
  }

  return (
    <div className="ingest-container">
      {/* <h1 className="text-2xl font-normal text-gray-700 mb-6">Ingest Guidelines</h1> */}

      <Form
        form={form}
        onFinish={handleSubmit}
        layout="vertical"
        className="w-full"
        initialValues={{ guideline_type: guidelineTypes.map(t => t.name) }}
      >
        {/* Hidden field to sync chip state with form */}
        <Form.Item name="guideline_type" hidden>
          <Input />
        </Form.Item>
        {/* Model Selection Row - Admin Only */}
        {/* {isAdmin && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
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

        {/* Document Details & Date Fields Card */}
        <div className="ingest-card">
          <div className="ingest-card-title">
            <FileTextOutlined /> Document Information
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Form.Item
              name="guideline_investor_id"
              label="Investor"
              className="mb-0"
              rules={[{ required: true, message: "Please select an investor" }]}
            >
              <Select
                size="large"
                className="w-full"
                placeholder="Select investor"
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) => {
                  const label = String(option?.children?.props?.children[2] ?? option?.children ?? '').toLowerCase();
                  return label.includes(input.toLowerCase());
                }}
                allowClear
              >
                {investors.map(inv => (
                  <Option key={inv.id} value={inv.id}>
                    <span className="flex items-center gap-2">
                      <span style={{ color: '#597ef7' }}>●</span> {inv.name}
                    </span>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="version"
              label="Version"
              className="mb-0"
            >
              <Input size="large" placeholder="Enter version (e.g., v1, v2)" />
            </Form.Item>

            <Form.Item
              name="effective_date"
              label="Effective Date"
              className="mb-0"
            >
              <DatePicker
                size="large"
                placeholder="Select date"
                className="w-full"
                format="DD/MM/YYYY"
              />
            </Form.Item>

            <Form.Item
              name="expiry_date"
              label="Expiry Date"
              className="mb-0"
            >
              <DatePicker
                size="large"
                placeholder="Select date"
                className="w-full"
                format="DD/MM/YYYY"
              />
            </Form.Item>
          </div>
        </div>

        {/* ===== Guideline Configuration Card ===== */}
        <div className="ingest-card">
          <div className="ingest-card-title">
            <AppstoreOutlined /> Guideline Configuration
          </div>
          <div className="mb-4">
            <p className="text-gray-500 text-sm mb-6">Select investor context and document categories for extraction</p>
          </div>


          {/* Category Chips */}
          <div>
            <div className="chip-controls">
              <span className="chip-controls__label">Document Categories</span>
              <button
                type="button"
                className="chip-controls__toggle"
                onClick={() => {
                  const allCats = guidelineTypes.map(t => t.name);
                  const next = selectedCategories.length === allCats.length ? [] : allCats;
                  setSelectedCategories(next);
                  form.setFieldsValue({ guideline_type: next });
                }}
              >
                {selectedCategories.length === guidelineTypes.length ? "Deselect All" : "Select All"}
              </button>
            </div>
            <div className="guideline-chips">
              {guidelineTypes.map((cat) => {
                const isActive = selectedCategories.includes(cat.name);
                return (
                  <div
                    key={cat.id}
                    className={`guideline-chip ${isActive ? 'guideline-chip--active' : ""}`}
                    style={isActive ? { borderColor: cat.color || '#3b82f6', background: `${cat.color || '#3b82f6'}15`, color: cat.color || '#3b82f6' } : {}}
                    onClick={() => {
                      const next = isActive
                        ? selectedCategories.filter((c) => c !== cat.name)
                        : [...selectedCategories, cat.name];
                      setSelectedCategories(next);
                      form.setFieldsValue({ guideline_type: next });
                    }}
                  >
                    {isActive ? (
                      <CheckCircleFilled className="chip-icon" />
                    ) : (
                      <PlusCircleOutlined className="chip-icon" />
                    )}
                    {cat.name}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Program Type & Page Range Row */}
        <div className="ingest-card">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Form.Item
              name="program_type"
              label="Program Type"
              className="mb-0"
            >
              <Input size="large" placeholder="e.g., Fixed, ARM" />
            </Form.Item>

            <Form.Item
              name="page_range"
              label="Page Range (e.g., 1-5, 8)"
              className="mb-0"
            >
              <Input size="large" placeholder="Optional" />
            </Form.Item>
          </div>
        </div>

        {/* Attach Documents Section */}
        <div className="ingest-card">
          <div className="ingest-card-title">
            <InboxOutlined /> Attach Documents
          </div>

          {files.length === 0 ? (
            <div className="upload-wrapper">
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
                    Click or drag PDF to this area to upload
                  </p>
                  <p className="text-gray-500 text-xs mt-1">
                    Multiple files supported
                  </p>
                </div>
              </Dragger>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500 font-medium">
                  {files.length} file{files.length !== 1 ? 's' : ''} selected
                </p>
                <Space>
                  <Button
                    onClick={handleRemoveAllFiles}
                  >
                    Remove All
                  </Button>
                  <Button
                    type="primary"
                    size="large"
                    htmlType="submit"
                    loading={processing}
                    disabled={files.length === 0 || processing}
                  >
                    {processing ? "Processing..." : "Extract Guidelines"}
                  </Button>
                </Space>
              </div>

              {files.map((file, index) => (
                <div key={index} className="file-item">
                  <div className="file-info">
                    <div className="file-icon-box">
                      <FileOutlined />
                    </div>
                    <div>
                      <p className="file-name">{file.name}</p>
                      <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <Button
                    danger
                    type="text"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveFile(file)}
                  >
                    Remove
                  </Button>
                </div>
              ))}

              <div className="upload-wrapper">
                <Dragger
                  {...uploadProps}
                  className="!border-none"
                  style={{ background: 'transparent' }}
                >
                  <div className="py-4">
                    <p className="text-sm font-medium text-blue-500">
                      + Add more documents
                    </p>
                  </div>
                </Dragger>
              </div>
            </div>
          )}
        </div>


      </Form>

      {/* Processing Modal - Updated for Progress Bar */}
      <Modal
        open={processingModalVisible}
        footer={null}
        closable={false}
        centered
        title={
          <div className="flex items-center gap-2">
            <LoadingOutlined className="text-blue-500" />
            <span>Processing Guideline...</span>
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
          title="Extraction Results"
          data={previewData}
          columns={previewColumns}
          sessionId={sessionId}
          investor={currentInvestor}
          version={currentVersion}
          onDownload={(type) => {
            if (sessionId) {
              ingestAPI.downloadExcel(sessionId, type);
            }
          }}
        />
      </React.Suspense>
    </div>
  );
};

export default IngestPage;
