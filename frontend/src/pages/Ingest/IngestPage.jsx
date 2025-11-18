// src/pages/Ingest/IngestPage.jsx

import React, { useState, useEffect, useRef } from "react";
import {
  Form,
  Select,
  Button,
  Input,
  message,
  Progress,
  Modal,
  Spin,
  Table,
  Tag,
  Space,
} from "antd";
import {
  PaperClipOutlined,
  SendOutlined,
  FileTextOutlined,
  DownloadOutlined,
  CloseCircleOutlined,
  FileExcelOutlined,
  LoadingOutlined,
  ReloadOutlined,
  DownOutlined,
} from "@ant-design/icons";
import { ingestAPI, settingsAPI } from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const { TextArea } = Input;
const { Option } = Select;

const DEFAULT_PROMPT = `You are a specialized AI data extractor for the mortgage industry. Your only function is to extract specific rules from a provided text and structure them into a clean, valid JSON array.

### PRIMARY GOAL
Convert unstructured mortgage guideline text into a structured list of self-contained rules. Each rule must be a complete JSON object.

### OUTPUT SCHEMA (JSON ONLY)
You MUST return a valid JSON array. Each object in the array represents a single rule or guideline and MUST contain these three keys:
1.  "category": The high-level topic (e.g., "Borrower Eligibility", "Credit", "Property Eligibility").
2.  "attribute": The specific rule or policy being defined (e.g., "Minimum Credit Score", "Gift Funds Policy").
3.  "guideline_summary": A DETAILED and COMPLETE summary of the rule.

### CRITICAL EXTRACTION INSTRUCTIONS
1.  **NO REFERENCES:** Your output for "guideline_summary" must NEVER reference another section.
2.  **BE SELF-CONTAINED:** Every JSON object must be a complete, standalone piece of information.
3.  **SUMMARIZE, DON'T COPY:** Do not copy and paste large blocks of text.
4.  **ONE RULE PER OBJECT:** Each distinct rule gets its own JSON object.
5.  **MAINTAIN HIERARCHY:** Use the "category" key to group related attributes.

### FINAL COMMANDS - YOU MUST OBEY
- Your entire response MUST be a single, valid JSON array.
- Start your response immediately with '[' and end it immediately with ']'.`;

const IngestPage = () => {
  const { isAdmin } = useAuth();
  const [form] = Form.useForm();
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [supportedModels, setSupportedModels] = useState({
    openai: [],
    gemini: [],
  });
  const [selectedProvider, setSelectedProvider] = useState("openai");
  const [previewData, setPreviewData] = useState(null);
  const [promptValue, setPromptValue] = useState(DEFAULT_PROMPT);
  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [tableColumns, setTableColumns] = useState([]);

  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchSupportedModels();
    form.setFieldsValue({
      model_provider: "openai",
      model_name: "gpt-4o",
      custom_prompt: DEFAULT_PROMPT,
    });
    setPromptValue(DEFAULT_PROMPT);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchSupportedModels = async () => {
    try {
      const response = await settingsAPI.getSupportedModels();
      setSupportedModels(response.data);
    } catch (error) {
      setSupportedModels({
        openai: ["gpt-4o", "gpt-4-turbo"],
        gemini: ["gemini-1.5-pro", "gemini-ultra"],
      });
    }
  };

  const handleFileSelect = (event) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type !== "application/pdf") {
        message.error("Please select a PDF file");
        return;
      }
      setFile(selectedFile);
      message.success(`${selectedFile.name} selected`);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleAttachClick = () => fileInputRef.current?.click();

  const handleResetPrompt = () => {
    setPromptValue(DEFAULT_PROMPT);
    form.setFieldsValue({ custom_prompt: DEFAULT_PROMPT });
    message.success("Prompt reset to default");
  };

  const handlePromptChange = (e) => setPromptValue(e.target.value);

  const handleSubmit = async (values) => {
    if (!file) return message.error("Please attach a PDF file.");
    const currentPrompt = isAdmin ? promptValue.trim() : DEFAULT_PROMPT;

    try {
      setProcessing(true);
      setProgress(0);
      setProgressMessage("Initializing...");
      setPreviewData(null);
      setProcessingModalVisible(true);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("model_provider", values.model_provider || "openai");
      formData.append("model_name", values.model_name || "gpt-4o");
      formData.append("custom_prompt", currentPrompt);
      if (values.investor) formData.append("investor", values.investor);
      if (values.version) formData.append("version", values.version);

      const response = await ingestAPI.ingestGuideline(formData);
      const { session_id } = response.data;
      setSessionId(session_id);

      const eventSource = ingestAPI.createProgressStream(session_id);
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setProgress(data.progress);
        setProgressMessage(data.message);
        if (data.progress >= 100) {
          eventSource.close();
          setProcessing(false);
          setProcessingModalVisible(false);
          fetchPreviewData(session_id);
          message.success("Processing complete!");
        }
      };
      eventSource.onerror = () => {
        eventSource.close();
        setProcessing(false);
        setProcessingModalVisible(false);
        message.error("Connection error or timeout.");
      };
    } catch (error) {
      setProcessing(false);
      setProcessingModalVisible(false);
      message.error("Failed to start processing.");
    }
  };

  const fetchPreviewData = async (sid) => {
    try {
      const response = await ingestAPI.getPreview(sid);
      const data = response.data;
      if (data && data.length > 0) {
        const firstItemKeys = Object.keys(data[0]);
        const columns = firstItemKeys.map((key) => ({
          title: key.replace(/_/g, " ").toUpperCase(),
          dataIndex: key,
          key: key,
          width: 250,
          render: (text) => (
            <div className="whitespace-pre-wrap text-sm">{String(text)}</div>
          ),
        }));
        setTableColumns(columns);
        setPreviewData(data);
      } else {
        setTableColumns([{ title: "Result", dataIndex: "content" }]);
        setPreviewData([{ key: "1", content: "No structured data found." }]);
      }
      setPreviewModalVisible(true);
    } catch (error) {
      message.error("Failed to load preview data.");
    }
  };

  const convertToTableData = (data) => {
    if (!data || !Array.isArray(data)) return [];
    return data.map((item, idx) => ({ key: idx, ...item }));
  };

  return (
    <div className="flex flex-col min-h-full">
      <Form
        form={form}
        onFinish={handleSubmit}
        className="flex flex-col flex-1 justify-between"
        initialValues={{ model_provider: "openai", model_name: "gpt-4o" }}
      >
        {/* === MAIN SCROLLABLE CONTENT === */}
        <div className="flex-1">
          <div className="max-w-[1400px] mx-auto w-full pt-2">
            {/* Title Section */}
            <div className="mb-8">
              <h1 className="text-[28px] font-light text-gray-800 mb-1">
                Ingest Guidelines
              </h1>
              <p className="text-gray-500 text-sm">
                {isAdmin
                  ? "Upload a PDF, define your desired JSON structure in the prompt, and extract the data."
                  : "Upload a PDF and fill in the details to extract data."}
              </p>
            </div>

            {/* Hidden File Input */}
            {/* <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              className="hidden"
              disabled={processing}
            /> */}

            {/* --- ROLE BASED VIEW --- */}
            {isAdmin ? (
              /* ADMIN VIEW */
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-5 mb-8">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-normal text-gray-700 m-0">
                    Extraction Command Center
                  </h2>
                  <Button
                    type="text"
                    icon={<ReloadOutlined />}
                    onClick={handleResetPrompt}
                    className="text-[#1890ff] hover:text-[#40a9ff] font-medium"
                  >
                    Reset Prompt
                  </Button>
                </div>
                <Form.Item
                  name="custom_prompt"
                  rules={[{ required: true }]}
                  className="mb-0"
                >
                  <TextArea
                    value={promptValue}
                    onChange={handlePromptChange}
                    placeholder="Describe the JSON structure you want..."
                    className="font-mono text-sm text-gray-600 bg-white border border-gray-300 rounded-md"
                    style={{
                      minHeight: "450px",
                      padding: "16px",
                      resize: "none",
                    }}
                    disabled={processing}
                  />
                </Form.Item>
              </div>
            ) : (
              /* USER VIEW */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl">
                <Form.Item
                  name="investor"
                  label={
                    <span className="text-gray-700 font-medium">Investors</span>
                  }
                  className="mb-0"
                >
                  <Input
                    placeholder="Enter"
                    size="large"
                    className="rounded-md border-gray-300"
                  />
                </Form.Item>

                <Form.Item
                  name="version"
                  label={
                    <span className="text-gray-700 font-medium">Version</span>
                  }
                  className="mb-0"
                >
                  <Input
                    placeholder="Enter"
                    size="large"
                    className="rounded-md border-gray-300"
                  />
                </Form.Item>
              </div>
            )}
          </div>
        </div>

        {/* === STICKY FOOTER === */}
        {/* 
            Uses sticky positioning to stick to the bottom of the MainLayout's scrollable Content area.
            Negative margins (-mx-8, -mb-8) compensate for the parent MainLayout padding (p-8).
            This ensures full width without overlapping the sidebar.
        */}
        <div className="sticky bottom-[-32px] -mx-8 -mb-8 px-8 py-4 bg-white border-t border-gray-200 z-20 flex items-center justify-between mt-6 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          {/* Left Side: Models (Admin) */}
          <div className="flex items-center gap-4">
            {isAdmin && (
              <>
                <Form.Item name="model_provider" noStyle>
                  <Select
                    size="large"
                    className="w-40"
                    onChange={(v) => {
                      setSelectedProvider(v);
                      const defaultModel =
                        v === "gemini"
                          ? "gemini-2.5-pro"
                          : supportedModels[v]?.[0];
                      form.setFieldsValue({ model_name: defaultModel });
                    }}
                    disabled={processing}
                    suffixIcon={
                      <DownOutlined className="text-gray-400 text-xs" />
                    }
                  >
                    <Option value="openai">OpenAI</Option>
                    <Option value="gemini">Google Gemini</Option>
                  </Select>
                </Form.Item>

                <Form.Item name="model_name" noStyle>
                  <Select
                    size="large"
                    className="w-48"
                    disabled={processing}
                    suffixIcon={
                      <DownOutlined className="text-gray-400 text-xs" />
                    }
                  >
                    {supportedModels[selectedProvider]?.map((m) => (
                      <Option key={m} value={m}>
                        {m}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </>
            )}
          </div>

          {/* Right Side: Actions */}
          <div className="flex items-center gap-4">
            {file ? (
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                <FileTextOutlined className="text-blue-600" />
                <span className="text-blue-900 text-sm font-medium truncate max-w-[200px]">
                  {file.name}
                </span>
                <Button
                  type="text"
                  size="small"
                  icon={<CloseCircleOutlined />}
                  onClick={handleRemoveFile}
                  className="text-blue-400 hover:text-red-500 flex items-center justify-center"
                />
              </div>
            ) : (
              <Button
                size="large"
                onClick={handleAttachClick}
                icon={<PaperClipOutlined className="text-[#1890ff]" />}
                className="border border-gray-300 text-gray-600 hover:border-blue-400 hover:text-blue-500 rounded-md px-6"
                disabled={processing}
              >
                Attach PDF
              </Button>
            )}

            <Button
              type="primary"
              htmlType="submit"
              size="large"
              loading={processing}
              icon={!processing && <SendOutlined />}
              className="bg-[#1890ff] hover:bg-blue-600 border-none rounded-md px-6 font-medium shadow-sm"
              disabled={!file}
            >
              {processing ? "Processing..." : "Extract Data"}
            </Button>
          </div>
        </div>
      </Form>

      {/* --- MODALS --- */}
      <Modal
        title={
          <div className="flex items-center gap-3 py-2">
            <Spin
              indicator={
                <LoadingOutlined
                  style={{ fontSize: 28, color: "#1890ff" }}
                  spin
                />
              }
            />
            <span className="text-xl font-semibold text-gray-800">
              Processing Guideline
            </span>
          </div>
        }
        open={processingModalVisible}
        footer={null}
        closable={false}
        centered
        width={550}
      >
        <div className="py-8 px-4">
          <Progress
            percent={progress}
            status="active"
            strokeColor="#1890ff"
            strokeWidth={10}
            className="mb-6"
          />
          <p className="text-center text-gray-600 text-lg">{progressMessage}</p>
        </div>
      </Modal>

      <Modal
        open={previewModalVisible}
        footer={null}
        closable={false}
        centered
        width="95vw"
        style={{ top: "20px" }}
        bodyStyle={{
          padding: 0,
          height: "90vh",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b bg-white rounded-t-lg">
          <div className="flex items-center gap-3">
            <div className="bg-green-100 p-2 rounded-full">
              <FileExcelOutlined className="text-green-600 text-xl" />
            </div>
            <div>
              <h3 className="font-semibold text-lg m-0">Extraction Results</h3>
              <span className="text-gray-500 text-xs">
                Review before downloading
              </span>
            </div>
            <Tag color="blue" className="ml-2">
              {convertToTableData(previewData).length} rows
            </Tag>
          </div>
          <Space>
            <Button
              icon={<CloseCircleOutlined />}
              onClick={() => setPreviewModalVisible(false)}
            >
              Close
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => ingestAPI.downloadExcel(sessionId)}
              className="bg-[#1890ff]"
            >
              Download Excel
            </Button>
          </Space>
        </div>
        <div className="flex-1 overflow-hidden bg-gray-50 p-4">
          <Table
            columns={tableColumns}
            dataSource={convertToTableData(previewData)}
            pagination={{ pageSize: 50 }}
            scroll={{ y: "calc(90vh - 140px)", x: "max-content" }}
            size="middle"
            bordered
            className="bg-white shadow-sm rounded-lg"
          />
        </div>
      </Modal>
    </div>
  );
};

export default IngestPage;
