// src/pages/Ingest/IngestPage.jsx

import React, { useState, useEffect } from "react";
import {
  Form,
  Select,
  Button,
  Input,
  message,
  Progress,
  Modal,
  Table,
  Tag,
  Space,
  Spin,
  Upload,
  DatePicker,
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
import { showToast } from "../../utils/toast";

const { Dragger } = Upload;
const { Option } = Select;

const IngestPage = () => {
  const { isAdmin } = useAuth();
  const [form] = Form.useForm();
  const { ingestPrompts } = usePrompts();

  // --- STATE ---
  const [file, setFile] = useState(null);
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

  useEffect(() => {
    fetchModelsAndSettings();
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

  // --- FILE HANDLERS ---
  const handleFileChange = (info) => {
    const { status } = info.file;
    if (status !== 'uploading') {
      const selectedFile = info.file.originFileObj || info.file;

      if (selectedFile.type !== "application/pdf") {
        showToast.error("Please upload a valid PDF file");
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleRemoveFile = (e) => {
    e.stopPropagation();
    setFile(null);
  };

  // --- MAIN SUBMIT ---
  const handleSubmit = async (values) => {
    if (!file) return showToast.error("Please upload a PDF file");

    try {
      setProcessing(true);
      setProgress(0);
      setProgressMessage("Initializing...");
      setProcessingModalVisible(true);

      // ✅ Fetch user's prompts from prompts API
      let systemPrompt = "";
      let userPrompt = "";

      try {
        const promptsRes = await promptsAPI.getUserPrompts();

        // Determine provider (values.model_provider might be missing if not admin)
        const provider = values.model_provider || selectedProvider || "openai";

        // Get prompts for the specific model
        const modelPrompts = promptsRes.data.ingest_prompts[provider] || promptsRes.data.ingest_prompts.openai || {};

        systemPrompt = modelPrompts.system_prompt || "";
        userPrompt = modelPrompts.user_prompt || "";
        console.log(`✅ Fetched ingest prompts for ${provider}`);
      } catch (err) {
        console.warn("⚠️ Could not fetch prompts from prompts API, using empty strings");
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("investor", values.investor);
      formData.append("version", values.version);
      formData.append("model_provider", values.model_provider);
      formData.append("model_name", values.model_name);

      // Attach dates
      formData.append("effective_date", values.effective_date.toISOString());
      if (values.expiry_date) {
        formData.append("expiry_date", values.expiry_date.toISOString());
      }

      // Attach prompts from settings
      formData.append("system_prompt", systemPrompt);
      formData.append("user_prompt", userPrompt);

      console.log("Starting ingestion...");
      const res = await ingestAPI.ingestGuideline(formData);
      const { session_id } = res.data;
      setSessionId(session_id);
      console.log("Session ID:", session_id);

      // Create progress stream
      const es = ingestAPI.createProgressStream(session_id);

      es.onmessage = (event) => {
        console.log("Progress event received:", event.data);
        try {
          const data = JSON.parse(event.data);
          console.log("Parsed progress data:", data);

          setProgress(data.progress || 0);
          setProgressMessage(data.message || "Processing...");

          // Check for completion
          if (data.status === "completed" || data.progress >= 100) {
            console.log("Processing completed, closing stream");
            es.close();
            setProcessing(false);
            setProcessingModalVisible(false);

            // Load preview
            setTimeout(() => {
              console.log("Loading preview for session:", session_id);
              loadPreview(session_id);
            }, 500);

            showToast.success("Processing complete!");
          } else if (data.status === "failed") {
            console.error("Processing failed:", data.error);
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
        setProcessing(false);
        setProcessingModalVisible(false);
        showToast.error("Connection error. Please try again.");
      };

      es.onopen = () => {
        console.log("SSE connection opened");
      };

    } catch (err) {
      console.error("Submission error:", err);
      setProcessing(false);
      setProcessingModalVisible(false);

      const errorMessage = err.response?.data?.detail || "Failed to start processing";

      if (errorMessage && errorMessage.includes("Duplicate ingestion")) {
        // Modal.warning({
        //   title: "Duplicate Ingestion",
        //   content: errorMessage,
        //   okText: "Got it",
        // });
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
      console.log("Preview data received:", res.data);
      const data = res.data;

      if (data?.length > 0) {
        setPreviewData(data);
        console.log("Opening preview modal...");
        setPreviewModalVisible(true);
      } else {
        console.log("No data found, showing empty state");
        setPreviewData([{ key: 1, content: "No structured data found." }]);
        setPreviewModalVisible(true);
      }
    } catch (error) {
      console.error("Failed to load preview:", error);
      showToast.error("Failed to load preview: " + (error.response?.data?.detail || error.message));
    }
  };


  const uploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    beforeUpload: () => false,
    onChange: handleFileChange,
    accept: ".pdf"
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
            rules={[{ required: true, message: "Investor is required" }]}
            className="mb-0"
          >
            <Input size="large" placeholder="Enter" className="rounded-md" />
          </Form.Item>

          <Form.Item
            name="version"
            label={<span className="text-gray-600">Version</span>}
            rules={[{ required: true, message: "Version is required" }]}
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
            rules={[{ required: true, message: "Effective date is required" }]}
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
            label={<span className="text-gray-600">Expiry Date (Optional)</span>}
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

        {/* Attach Documents Section */}
        <div className="mb-8">
          <h2 className="text-base font-medium text-gray-700 mb-3" style={{ fontFamily: 'Jura, sans-serif' }}>
            Attach Document
          </h2>

          {!file ? (
            <Dragger
              {...uploadProps}
              className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-dashed border-blue-300 rounded-lg hover:border-blue-500 hover:bg-blue-100 transition-all duration-200"
              style={{ padding: '16px' }}
            >
              <div className="py-6">
                <p className="ant-upload-drag-icon mb-2">
                  <InboxOutlined style={{ fontSize: '36px', color: '#3b82f6' }} />
                </p>
                <p className="text-base font-medium text-blue-600 mb-1" style={{ fontFamily: 'Jura, sans-serif' }}>
                  Click to upload or drag and drop
                </p>
                <p className="text-gray-500 text-xs" style={{ fontFamily: 'Jura, sans-serif' }}>
                  Supported Format: PDF
                </p>
              </div>
            </Dragger>
          ) : (
            <div className="border-2 border-green-200 bg-green-50 rounded-lg p-4 flex items-center justify-between transition-all duration-200 hover:shadow-md">
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
                onClick={handleRemoveFile}
                className="hover:bg-red-50"
                style={{ fontFamily: 'Jura, sans-serif' }}
              >
                Remove
              </Button>
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
            disabled={!file || processing}
          >
            {processing ? "Processing..." : "Extract Guidelines"}
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
          <div className="flex items-center gap-3">
            <Spin indicator={<LoadingOutlined spin style={{ fontSize: 26 }} />} />
            <span className="text-lg font-semibold">Processing Guideline</span>
          </div>
        }
      >
        <Progress percent={Math.round(progress)} status="active" strokeColor="#1890ff" />
        <p className="text-center mt-3 text-gray-600">{progressMessage}</p>
        {/* <p className="text-center mt-2 text-gray-400 text-xs">Session: {sessionId?.substring(0, 8)}</p> */}
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
