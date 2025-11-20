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
  Table,
  Tag,
  Space,
  Spin,
} from "antd";
import {
  PaperClipOutlined,
  SendOutlined,
  FileTextOutlined,
  DownloadOutlined,
  CloseCircleOutlined,
  FileExcelOutlined,
  LoadingOutlined,
  DownOutlined,
} from "@ant-design/icons";
import { usePrompts } from "../../context/PromptContext";
import { ingestAPI, settingsAPI } from "../../services/api";

const { TextArea } = Input;
const { Option } = Select;

const DEFAULT_PROMPT = "SYSTEM-CONTROLLED-PROMPT"; // Backend will handle

const IngestPage = () => {
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
  const [tableColumns, setTableColumns] = useState([]);
  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchModels();
    form.setFieldsValue({
      model_provider: "gemini",
      model_name: "gemini-2.5-pro",
    });
    setSelectedProvider("gemini");
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

  // --- FILE HANDLERS ---
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type !== "application/pdf") {
      message.error("Please upload a valid PDF file");
      return;
    }
    setFile(selectedFile);
  };

  const handleAttachClick = () => fileInputRef.current?.click();
  const handleRemoveFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // --- MAIN SUBMIT ---
  const handleSubmit = async (values) => {
    if (!file) return message.error("Please upload a PDF file");

    try {
      setProcessing(true);
      setProgress(0);
      setProgressMessage("Initializing...");
      setProcessingModalVisible(true);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("investor", values.investor);
      formData.append("version", values.version);
      formData.append("model_provider", values.model_provider);
      formData.append("model_name", values.model_name);

      // NEW: attach prompts from PromptContext
      formData.append("system_prompt", ingestPrompts.system_prompt || "");
      formData.append("user_prompt", ingestPrompts.user_prompt || "");
      debugger;
      const res = await ingestAPI.ingestGuideline(formData);
      const { session_id } = res.data;
      setSessionId(session_id);

      const es = ingestAPI.createProgressStream(session_id);
      es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setProgress(data.progress);
        setProgressMessage(data.message);

        if (data.progress >= 100) {
          es.close();
          setProcessing(false);
          setProcessingModalVisible(false);
          loadPreview(session_id);
          message.success("Processing complete!");
        }
      };

      es.onerror = () => {
        es.close();
        setProcessing(false);
        setProcessingModalVisible(false);
        message.error("Connection error");
      };
    } catch (err) {
      setProcessing(false);
      setProcessingModalVisible(false);
      message.error("Failed to start processing");
    }
  };

  // --- LOAD PREVIEW ---
  const loadPreview = async (sid) => {
    try {
      const res = await ingestAPI.getPreview(sid);
      const data = res.data;

      if (data?.length > 0) {
        const cols = Object.keys(data[0]).map((key) => ({
          title: key.toUpperCase(),
          dataIndex: key,
          key,
          width: 250,
          render: (text) => (
            <div className="whitespace-pre-wrap text-sm">{String(text)}</div>
          ),
        }));
        setTableColumns(cols);
        setPreviewData(data);
      } else {
        setTableColumns([{ title: "Result", dataIndex: "content" }]);
        setPreviewData([{ key: 1, content: "No structured data found." }]);
      }
      setPreviewModalVisible(true);
    } catch {
      message.error("Failed to load preview");
    }
  };

  const convertToTableData = (data) =>
    data?.map((item, idx) => ({ key: idx, ...item })) || [];

  return (
    <div className="flex flex-col min-h-full">
      <Form
        form={form}
        onFinish={handleSubmit}
        initialValues={{ model_provider: "openai", model_name: "gpt-4o" }}
        className="flex flex-col flex-1"
      >
        <div className="flex-1 max-w-[1400px] mx-auto w-full pt-2">
          <h1 className="text-[28px] font-light text-gray-800 mb-1">
            Ingest Guidelines
          </h1>
          <p className="text-gray-500 text-sm mb-6">
            Upload a guideline PDF with investor & version details.
          </p>

          {/* User View Only */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl">
            <Form.Item
              name="investor"
              label={
                <span className="text-gray-700 font-medium">Investor</span>
              }
              rules={[{ required: true, message: "Investor is required" }]}
            >
              <Input size="large" placeholder="Investor name" />
            </Form.Item>

            <Form.Item
              name="version"
              label={<span className="text-gray-700 font-medium">Version</span>}
              rules={[{ required: true, message: "Version is required" }]}
            >
              <Input size="large" placeholder="Version identifier" />
            </Form.Item>
          </div>
        </div>

        {/* Sticky Footer */}
        <div className="sticky bottom-[-32px] -mx-8 -mb-8 px-8 py-4 bg-white border-t border-gray-200 flex justify-between items-center shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <div className="flex items-center gap-4">
            <Form.Item name="model_provider" noStyle>
              <Select
                size="large"
                className="w-40"
                onChange={(v) => {
                  setSelectedProvider(v);
                  const defaultModel =
                    v === "gemini" ? "gemini-2.5-pro" : supportedModels[v]?.[0];
                  form.setFieldsValue({ model_name: defaultModel });
                }}
                suffixIcon={<DownOutlined className="text-gray-400 text-xs" />}
              >
                <Option value="openai">OpenAI</Option>
                <Option value="gemini">Google Gemini</Option>
              </Select>
            </Form.Item>

            <Form.Item name="model_name" noStyle>
              <Select
                size="large"
                className="w-48"
                suffixIcon={<DownOutlined className="text-gray-400 text-xs" />}
              >
                {supportedModels[selectedProvider]?.map((model) => (
                  <Option key={model} value={model}>
                    {model}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </div>

          {/* File Upload + Submit */}
          <div className="flex items-center gap-4">
            {file ? (
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                <FileTextOutlined className="text-blue-600" />
                <span className="text-blue-900 text-sm font-medium truncate max-w-[200px]">
                  {file.name}
                </span>
                <Button
                  type="text"
                  icon={<CloseCircleOutlined />}
                  onClick={handleRemoveFile}
                />
              </div>
            ) : (
              <Button
                size="large"
                onClick={handleAttachClick}
                icon={<PaperClipOutlined />}
              >
                Attach PDF
              </Button>
            )}

            <input
              type="file"
              ref={fileInputRef}
              hidden
              accept="application/pdf"
              onChange={handleFileSelect}
            />

            <Button
              type="primary"
              size="large"
              htmlType="submit"
              loading={processing}
              disabled={!file}
              icon={!processing && <SendOutlined />}
            >
              {processing ? "Processing..." : "Extract"}
            </Button>
          </div>
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
            <Spin
              indicator={<LoadingOutlined spin style={{ fontSize: 26 }} />}
            />
            <span className="text-lg font-semibold">Processing Guideline</span>
          </div>
        }
      >
        <Progress percent={progress} status="active" />
        <p className="text-center mt-3 text-gray-600">{progressMessage}</p>
      </Modal>

      {/* Preview Modal */}
      <Modal
        open={previewModalVisible}
        footer={null}
        width="95vw"
        centered
        closable={false}
        style={{ top: "20px" }}
      >
        <div className="flex justify-between items-center px-6 py-4 border-b bg-white">
          <div className="flex items-center gap-3">
            <div className="bg-green-100 p-2 rounded-full">
              <FileExcelOutlined className="text-green-600 text-xl" />
            </div>
            <h3 className="font-semibold text-lg">Extraction Results</h3>
            <Tag color="blue">
              {convertToTableData(previewData).length} rows
            </Tag>
          </div>

          <Space>
            <Button onClick={() => setPreviewModalVisible(false)}>Close</Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => ingestAPI.downloadExcel(sessionId)}
            >
              Download Excel
            </Button>
          </Space>
        </div>

        <div className="p-4 bg-gray-50">
          <Table
            dataSource={convertToTableData(previewData)}
            columns={tableColumns}
            pagination={{ pageSize: 50 }}
            scroll={{ y: "calc(90vh - 200px)", x: "max-content" }}
            bordered
            size="middle"
          />
        </div>
      </Modal>
    </div>
  );
};

export default IngestPage;
