// src/pages/Prompts/IngestionPromptPage.jsx

import React, { useState, useEffect } from "react";
import { Form, Input, Button, Spin, Card, Tabs, Select } from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import { promptsAPI } from "../../services/api";
import { showToast } from "../../utils/toast";

const { TextArea } = Input;

const IngestionPromptPage = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [activeTab, setActiveTab] = useState("system");
  const [selectedModel, setSelectedModel] = useState("openai");

  useEffect(() => {
    fetchPrompts();
  }, [selectedModel]); // Re-fetch when model changes

  const fetchPrompts = async () => {
    try {
      setFetching(true);
      const res = await promptsAPI.getUserPrompts();

      console.log("Full API Response:", res);
      console.log("Response data:", res.data);
      console.log("Ingest prompts:", res.data?.ingest_prompts);
      console.log("Selected model:", selectedModel);

      // Ensure the response has the expected structure
      if (!res.data || !res.data.ingest_prompts) {
        console.error("Invalid response structure:", res);
        throw new Error("Invalid prompts structure");
      }

      // Set form values for the currently selected model
      const modelPrompts = res.data.ingest_prompts[selectedModel] || res.data.ingest_prompts.openai || {};

      console.log("Model prompts for", selectedModel, ":", modelPrompts);

      form.setFieldsValue({
        system_prompt: modelPrompts.system_prompt || "",
        user_prompt: modelPrompts.user_prompt || "",
      });

      console.log("Form values set successfully");
    } catch (error) {
      console.error("Failed to fetch prompts:", error);
      showToast.error("Failed to load prompts");
    } finally {
      setFetching(false);
    }
  };

  // Handle model selection change
  const handleModelChange = (model) => {
    setSelectedModel(model);
    // useEffect will automatically fetch prompts when selectedModel changes
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      const values = form.getFieldsValue();

      // Get current prompts first
      const currentRes = await promptsAPI.getUserPrompts();

      // Update only the selected model's prompts
      const updatedIngestPrompts = {
        ...currentRes.data.ingest_prompts,
        [selectedModel]: {
          system_prompt: values.system_prompt,
          user_prompt: values.user_prompt,
        }
      };

      const prompts = {
        ingest_prompts: updatedIngestPrompts,
        compare_prompts: currentRes.data.compare_prompts,
      };

      await promptsAPI.saveUserPrompts(prompts);
      showToast.success(`Ingestion prompts for ${selectedModel.toUpperCase()} saved successfully!`);
    } catch (error) {
      console.error("Failed to save prompts:", error);
      showToast.error("Failed to save prompts");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      const res = await promptsAPI.resetUserPrompts();

      const modelPrompts = res.data.ingest_prompts[selectedModel] || res.data.ingest_prompts.openai;
      form.setFieldsValue({
        system_prompt: modelPrompts.system_prompt,
        user_prompt: modelPrompts.user_prompt,
      });

      showToast.success(`Prompts reset to defaults for ${selectedModel.toUpperCase()}!`);
    } catch (error) {
      console.error("Failed to reset prompts:", error);
      showToast.error("Failed to reset prompts");
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spin size="large" />
      </div>
    );
  }

  const tabItems = [
    {
      key: "system",
      label: "System Prompt",
      children: (
        <Form.Item
          name="system_prompt"
          tooltip="Defines the role and behavior of the AI for ingestion tasks"
        >
          <TextArea
            rows={20}
            placeholder="Enter system prompt for ingestion..."
            className="font-mono text-sm"
          />
        </Form.Item>
      ),
    },
    {
      key: "user",
      label: "User Prompt",
      children: (
        <Form.Item
          name="user_prompt"
          tooltip="Specific instructions for processing guidelines"
        >
          <TextArea
            rows={20}
            placeholder="Enter user prompt for ingestion..."
            className="font-mono text-sm"
          />
        </Form.Item>
      ),
    },
  ];

  return (
    <div className="px-8 py-6 max-w-5xl mx-auto">
      {/* <h1 className="text-3xl font-bold mb-6 text-gray-800">Ingestion Prompt</h1> */}

      <Card className="shadow-sm">
        <Form form={form} layout="vertical">
          {/* Model Selection Dropdown */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Model
            </label>
            <Select
              value={selectedModel}
              onChange={handleModelChange}
              style={{ width: 200 }}
              options={[
                { value: "openai", label: "OpenAI" },
                { value: "gemini", label: "Gemini" },
              ]}
            />
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
          />

          <div className="flex justify-end gap-3 mt-6">
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              loading={loading}
            >
              Reset to Defaults
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={loading}
            >
              Save Prompts
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default IngestionPromptPage;
