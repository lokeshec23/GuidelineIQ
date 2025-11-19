// src/pages/Compare/ComparePage.jsx

import React, { useState, useEffect, useRef } from "react";
import {
  Card,
  Form,
  Select,
  Button,
  message,
  Progress,
  Space,
  Table,
  Modal,
} from "antd";
import {
  PaperClipOutlined,
  SendOutlined,
  DownloadOutlined,
  CloseCircleOutlined,
  SwapOutlined,
  FileExcelOutlined,
  LoadingOutlined,
  DownOutlined,
} from "@ant-design/icons";
import { usePrompts } from "../../context/PromptContext";
import { compareAPI, settingsAPI } from "../../services/api";

const { Option } = Select;

const ComparePage = () => {
  const [form] = Form.useForm();
  const { comparePrompts } = usePrompts();

  const [file1, setFile1] = useState(null);
  const [file2, setFile2] = useState(null);

  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");

  const [supportedModels, setSupportedModels] = useState({
    openai: [],
    gemini: [],
  });

  const [selectedProvider, setSelectedProvider] = useState("openai");

  const [previewData, setPreviewData] = useState(null);
  const [tableColumns, setTableColumns] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const [processingModalVisible, setProcessingModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);

  const file1InputRef = useRef(null);
  const file2InputRef = useRef(null);

  useEffect(() => {
    fetchModels();
    form.setFieldsValue({
      model_provider: "openai",
      model_name: "gpt-4o",
    });
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

  // FILE HANDLING
  const selectFile1 = () => file1InputRef.current.click();
  const selectFile2 = () => file2InputRef.current.click();

  const handleFile1Select = (e) => setFile1(e.target.files?.[0]);
  const handleFile2Select = (e) => setFile2(e.target.files?.[0]);

  // MAIN SUBMIT
  const handleSubmit = async (values) => {
    if (!file1 || !file2)
      return message.error("Please attach both guideline files");

    try {
      setProcessing(true);
      setProgress(0);
      setProgressMessage("Starting comparison...");
      setProcessingModalVisible(true);

      const fd = new FormData();
      fd.append("file1", file1);
      fd.append("file2", file2);
      fd.append("model_provider", values.model_provider);
      fd.append("model_name", values.model_name);
      fd.append("system_prompt", comparePrompts.system_prompt || "");
      fd.append("user_prompt", comparePrompts.user_prompt || "");

      const res = await compareAPI.compareGuidelines(fd);
      const { session_id } = res.data;
      setSessionId(session_id);

      const es = compareAPI.createProgressStream(session_id);

      es.onmessage = (event) => {
        const data = JSON.parse(event.data);

        setProgress(data.progress);
        setProgressMessage(data.message);

        if (data.progress >= 100) {
          es.close();
          setProcessing(false);
          setProcessingModalVisible(false);
          loadPreview(session_id);
          message.success("Comparison complete!");
        }
      };

      es.onerror = () => {
        es.close();
        setProcessing(false);
        setProcessingModalVisible(false);
        message.error("Comparison failed");
      };
    } catch {
      setProcessing(false);
      setProcessingModalVisible(false);
      message.error("Failed to start comparison");
    }
  };

  // PREVIEW LOAD
  const loadPreview = async (sid) => {
    try {
      const res = await compareAPI.getPreview(sid);
      const data = res.data;

      if (data && data.length > 0) {
        const cols = Object.keys(data[0]).map((key) => ({
          title: key.replace(/_/g, " ").toUpperCase(),
          dataIndex: key,
          key,
          width: 250,
          render: (text) => (
            <div className="whitespace-pre-wrap">{String(text)}</div>
          ),
        }));

        setTableColumns(cols);
        setPreviewData(data);
      } else {
        setTableColumns([{ title: "Result", dataIndex: "content" }]);
        setPreviewData([{ key: 1, content: "No structured comparison found" }]);
      }

      setPreviewModalVisible(true);
    } catch {
      message.error("Failed to load preview");
    }
  };

  const convertRows = (data) =>
    (data || []).map((row, i) => ({ key: i, ...row }));

  return (
    <div className="flex flex-col min-h-full">
      <Form
        form={form}
        onFinish={handleSubmit}
        initialValues={{
          model_provider: "openai",
          model_name: "gpt-4o",
        }}
        className="flex flex-col flex-1"
      >
        {/* TOP CONTENT */}
        <div className="flex-1 max-w-[1400px] mx-auto w-full pt-2">
          <h1 className="text-[28px] font-light text-gray-800 mb-1 flex items-center gap-2">
            <SwapOutlined /> Compare Guidelines
          </h1>

          <p className="text-gray-500 text-sm mb-6">
            Upload two Excel guideline files to compare them.
          </p>
        </div>

        {/* STICKY FOOTER (MATCHES INGEST PAGE STYLE) */}
        <div className="sticky bottom-[-32px] -mx-8 -mb-8 px-8 py-4 bg-white border-t border-gray-200 flex justify-between items-center shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          {/* LEFT SIDE — MODEL SELECTORS */}
          <div className="flex items-center gap-4">
            {/* Provider */}
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

            {/* Model */}
            <Form.Item name="model_name" noStyle>
              <Select
                size="large"
                className="w-48"
                suffixIcon={<DownOutlined className="text-gray-400 text-xs" />}
              >
                {supportedModels[selectedProvider]?.map((m) => (
                  <Option key={m} value={m}>
                    {m}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </div>

          {/* RIGHT SIDE — FILE 1, FILE 2, COMPARE BUTTON */}
          <div className="flex items-center gap-4">
            {/* File 1 */}
            <input
              type="file"
              accept=".xlsx,.xls"
              hidden
              ref={file1InputRef}
              onChange={handleFile1Select}
            />

            <Button
              icon={<PaperClipOutlined />}
              size="large"
              onClick={selectFile1}
              disabled={processing}
            >
              {file1 ? file1.name : "Attach Guideline 1"}
            </Button>

            {/* File 2 */}
            <input
              type="file"
              accept=".xlsx,.xls"
              hidden
              ref={file2InputRef}
              onChange={handleFile2Select}
            />

            <Button
              icon={<PaperClipOutlined />}
              size="large"
              onClick={selectFile2}
              disabled={processing}
            >
              {file2 ? file2.name : "Attach Guideline 2"}
            </Button>

            {/* Compare */}
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              icon={<SendOutlined />}
              disabled={!file1 || !file2 || processing}
              loading={processing}
            >
              Compare
            </Button>
          </div>
        </div>
      </Form>

      {/* PROCESSING MODAL */}
      <Modal
        open={processingModalVisible}
        footer={null}
        closable={false}
        centered
        width={550}
        title={
          <div className="flex items-center gap-3">
            <LoadingOutlined spin className="text-xl text-blue-600" />
            <span className="text-lg font-semibold">Comparing Guidelines</span>
          </div>
        }
      >
        <Progress percent={progress} status="active" />
        <p className="text-center mt-3 text-gray-600 text-lg">
          {progressMessage}
        </p>
      </Modal>

      {/* PREVIEW MODAL */}
      <Modal
        open={previewModalVisible}
        footer={null}
        closable={false}
        centered
        width="95vw"
        style={{ top: "20px" }}
      >
        <div className="flex justify-between items-center px-6 py-4 border-b bg-white">
          <div className="flex items-center gap-3">
            <div className="bg-purple-100 p-2 rounded-full">
              <SwapOutlined className="text-purple-600 text-xl" />
            </div>
            <h3 className="font-semibold text-lg">Comparison Results</h3>
            <Space>
              <span className="text-gray-500">
                {convertRows(previewData).length} rows
              </span>
            </Space>
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
              onClick={() => compareAPI.downloadExcel(sessionId)}
            >
              Download Excel
            </Button>
          </Space>
        </div>

        <div className="p-4 bg-gray-50">
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
    </div>
  );
};

export default ComparePage;
