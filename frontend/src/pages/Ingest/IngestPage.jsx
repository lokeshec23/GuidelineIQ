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
} from "@ant-design/icons";
import { usePrompts } from "../../context/PromptContext";
import { useAuth } from "../../context/AuthContext";
import { ingestAPI, settingsAPI, promptsAPI } from "../../services/api";
import ExcelPreviewModal from "../../components/ExcelPreviewModal";
import { showToast, getErrorMessage } from "../../utils/toast";

const { Dragger } = Upload;
const { Option } = Select;

const IngestPage = () => {
  const { isAdmin } = useAuth();
  const [form] = Form.useForm();
  const { ingestPrompts } = usePrompts();

  // --- STATE ---
  const [files, setFiles] = useState([]); // ✅ Changed to array for multiple files
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
  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);

  useEffect(() => {
    fetchModelsAndSettings();
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
    console.log("Form submitted with values:", values);
    console.log("Files selected:", files);

    // if (!files || files.length === 0) return showToast.error("Please upload at least one PDF file");

    try {
      setProcessing(true);
      setProgress(0); // Reset progress
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
        console.log(`✅ Fetched ingest prompts for ${modelProvider}`);
      } catch (err) {
        console.warn("⚠️ Could not fetch prompts from prompts API, using empty strings");
      }

      const formData = new FormData();
      // ✅ Append all files
      files.forEach((file) => {
        formData.append("files", file); // Note: 'files' matches backend List[UploadFile]
      });
      formData.append("investor", values.investor);
      formData.append("version", values.version);
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
      if (values.guideline_type) formData.append("guideline_type", values.guideline_type);
      if (values.program_type) formData.append("program_type", values.program_type);

      console.log("Starting ingestion...");
      const res = await ingestAPI.ingestGuideline(formData);
      const { session_id, status } = res.data;

      console.log("Ingestion started with session ID:", session_id);
      setSessionId(session_id);

      // Start SSE for progress tracking
      const es = ingestAPI.createProgressStream(session_id);

      es.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgress(data.progress || 0);
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
            console.log("Loading preview for session:", session_id);
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
    console.log("loadPreview called with session ID:", sid);
    try {
      const res = await ingestAPI.getPreview(sid);
      console.log("Preview response received:", res.data);

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

      if (previewDataArray?.length > 0) {
        setPreviewData(previewDataArray);
        setSessionId(historyId); // Use history_id for PDF viewing
        console.log("Opening preview modal with history_id:", historyId);
        setPreviewModalVisible(true);
      } else {
        console.log("No data found, showing empty state");
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

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      {/* <h1 className="text-2xl font-normal text-gray-700 mb-6">Ingest Guidelines</h1> */}

      <Form
        form={form}
        onFinish={handleSubmit}
        layout="vertical"
        className="w-full"
      >
        {/* Model Selection Row - Admin Only */}
        {isAdmin && (
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
        )}

        {/* Investor & Version Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Form.Item
            name="investor"
            label={<span className="text-gray-600">Investors</span>}
            className="mb-0"
          >
            <Input size="large" placeholder="Enter" className="rounded-md" />
          </Form.Item>

          <Form.Item
            name="version"
            label={<span className="text-gray-600">Version</span>}
            className="mb-0"
          >
            <Input size="large" placeholder="Enter" className="rounded-md" />
          </Form.Item>
        </div>

        {/* Date Fields Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Form.Item
            name="effective_date"
            label={<span className="text-gray-600">Effective Date</span>}
            className="mb-0"
          >
            <DatePicker
              size="large"
              placeholder="Select date"
              className="w-full rounded-md"
              format="DD/MM/YYYY"
            />
          </Form.Item>

          <Form.Item
            name="expiry_date"
            label={<span className="text-gray-600">Expiry Date</span>}
            className="mb-0"
          >
            <DatePicker
              size="large"
              placeholder="Select date"
              className="w-full rounded-md"
              format="DD/MM/YYYY"
            />
          </Form.Item>
        </div>

        {/* New Metadata Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Form.Item
            name="guideline_type"
            label={<span className="text-gray-600">Guideline Type</span>}
            className="mb-0"
          >
            <Input size="large" placeholder="e.g., Agency, Jumbo" className="rounded-md" />
          </Form.Item>

          <Form.Item
            name="program_type"
            label={<span className="text-gray-600">Program Type</span>}
            className="mb-0"
          >
            <Input size="large" placeholder="e.g., Fixed, ARM" className="rounded-md" />
          </Form.Item>

          <Form.Item
            name="page_range"
            label={<span className="text-gray-600">Page Range (e.g., 1-5, 8)</span>}
            className="mb-0"
          >
            <Input size="large" placeholder="Optional" className="rounded-md" />
          </Form.Item>
        </div>

        {/* Attach Documents Section */}
        <div className="mb-8">
          <h2 className="text-base font-medium text-gray-700 mb-3" style={{ fontFamily: 'Jura, sans-serif' }}>
            Attach Documents
          </h2>

          {files.length === 0 ? (
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-dashed border-blue-300 rounded-lg hover:border-blue-500 hover:bg-blue-100 transition-all duration-200">
              <Dragger
                {...uploadProps}
                className="!border-none"
                style={{ padding: '16px', background: 'transparent' }}
              >
                <div className="py-6">
                  <p className="ant-upload-drag-icon mb-2">
                    <InboxOutlined style={{ fontSize: '36px', color: '#3b82f6' }} />
                  </p>
                  <p className="text-base font-medium text-blue-600 mb-1" style={{ fontFamily: 'Jura, sans-serif' }}>
                    Click to upload or drag and drop
                  </p>
                  <p className="text-gray-500 text-xs" style={{ fontFamily: 'Jura, sans-serif' }}>
                    Supported Format: PDF • Multiple files allowed
                  </p>
                </div>
              </Dragger>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Header with file count and remove all button */}
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600 font-medium" style={{ fontFamily: 'Jura, sans-serif' }}>
                  {files.length} file{files.length !== 1 ? 's' : ''} selected
                </p>
                <Button
                  danger
                  type="text"
                  size="small"
                  onClick={handleRemoveAllFiles}
                  className="hover:bg-red-50"
                  style={{ fontFamily: 'Jura, sans-serif' }}
                >
                  Remove All
                </Button>
              </div>

              {/* List of files */}
              {files.map((file, index) => (
                <div
                  key={index}
                  className="border-2 border-green-200 bg-green-50 rounded-lg p-4 flex items-center justify-between transition-all duration-200 hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <div className="bg-green-100 p-2.5 rounded-lg">
                      <FileTextOutlined className="text-green-600 text-lg" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800 text-sm" style={{ fontFamily: 'Jura, sans-serif' }}>
                        {file.name}
                      </p>
                      <p className="text-gray-500 text-xs" style={{ fontFamily: 'Jura, sans-serif' }}>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Button
                    danger
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveFile(file)}
                    className="hover:bg-red-50"
                    style={{ fontFamily: 'Jura, sans-serif' }}
                  >
                    Remove
                  </Button>
                </div>
              ))}

              {/* Add more files button */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all duration-200">
                <Dragger
                  {...uploadProps}
                  className="!border-none"
                  style={{ padding: '12px', background: 'transparent' }}
                >
                  <div className="py-3">
                    <p className="text-sm font-medium text-gray-600" style={{ fontFamily: 'Jura, sans-serif' }}>
                      + Add more PDFs
                    </p>
                  </div>
                </Dragger>
              </div>
            </div>
          )}
        </div>

        {/* Submit Button Area */}
        <div className="flex justify-end">
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            className="px-8 h-12 text-lg bg-blue-600 hover:bg-blue-700"
            loading={processing}
            disabled={files.length === 0 || processing}
          >
            {processing ? "Processing..." : "Extract Guidelines"}
          </Button>
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
      <ExcelPreviewModal
        visible={previewModalVisible}
        onClose={() => setPreviewModalVisible(false)}
        title="Extraction Results"
        data={previewData}
        sessionId={sessionId}
        onDownload={() => {
          if (sessionId) {
            ingestAPI.downloadExcel(sessionId);
          }
        }}
      />
    </div>
  );
};

export default IngestPage;
