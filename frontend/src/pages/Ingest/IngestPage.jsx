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
import { ingestAPI, settingsAPI } from "../../services/api";

const { Dragger } = Upload;
const { Option } = Select;

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

  // --- FILE HANDLERS ---
  const handleFileChange = (info) => {
    const { status } = info.file;
    if (status !== 'uploading') {
      // We only want one file
      const selectedFile = info.file.originFileObj || info.file;

      if (selectedFile.type !== "application/pdf") {
        message.error("Please upload a valid PDF file");
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

      // Attach prompts
      formData.append("system_prompt", ingestPrompts.system_prompt || "");
      formData.append("user_prompt", ingestPrompts.user_prompt || "");

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

  const uploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    beforeUpload: () => false, // Prevent auto upload
    onChange: handleFileChange,
    accept: ".pdf"
  };

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <h1 className="text-2xl font-normal text-gray-700 mb-6">Ingest Guidelines</h1>

      <Form
        form={form}
        onFinish={handleSubmit}
        layout="vertical"
        className="w-full"
      >
        {/* Model Selection Row */}
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

        {/* Attach Documents Section */}
        <div className="mb-8">
          <h2 className="text-xl font-normal text-gray-700 mb-4">Attach Documents</h2>

          {!file ? (
            <Dragger {...uploadProps} className="bg-gray-50 border-dashed border-2 border-gray-200 rounded-lg hover:border-blue-400 transition-colors">
              <div className="py-12">
                <p className="ant-upload-drag-icon mb-4">
                  <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                </p>
                <p className="text-lg text-blue-500 mb-2">
                  Upload a file <span className="text-gray-500">or drag and drop</span>
                </p>
                <p className="text-gray-400 text-sm">
                  pdf, csv, xlsc. up to 5MB
                </p>
              </div>
            </Dragger>
          ) : (
            <div className="border border-gray-200 rounded-lg p-6 flex items-center justify-between bg-white shadow-sm">
              <div className="flex items-center gap-4">
                <div className="bg-red-50 p-3 rounded-lg">
                  <FileTextOutlined className="text-red-500 text-xl" />
                </div>
                <div>
                  <p className="font-medium text-gray-800 text-lg">{file.name}</p>
                  <p className="text-gray-500 text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
              <Button
                danger
                type="text"
                icon={<DeleteOutlined />}
                onClick={handleRemoveFile}
                className="hover:bg-red-50"
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
            disabled={!file}
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
            <Tag color="blue">{convertToTableData(previewData).length} rows</Tag>
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
