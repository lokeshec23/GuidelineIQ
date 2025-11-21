// src/pages/Prompts/ComparisonPromptPage.jsx

import React, { useState, useEffect } from "react";
import { Form, Input, Button, message, Spin, Card, Tabs } from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import { promptsAPI } from "../../services/api";

const { TextArea } = Input;

const ComparisonPromptPage = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [activeTab, setActiveTab] = useState("system");

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      setFetching(true);
      const res = await promptsAPI.getUserPrompts();
      form.setFieldsValue({
        system_prompt: res.data.compare_prompts.system_prompt,
        user_prompt: res.data.compare_prompts.user_prompt,
      });
    } catch (error) {
      console.error("Failed to fetch prompts:", error);
      message.error("Failed to load prompts");
    } finally {
      setFetching(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      const values = form.getFieldsValue();

      // Get current prompts first
      const currentRes = await promptsAPI.getUserPrompts();

      const prompts = {
        ingest_prompts: currentRes.data.ingest_prompts,
        compare_prompts: {
          system_prompt: values.system_prompt,
          user_prompt: values.user_prompt,
        },
      };

      await promptsAPI.saveUserPrompts(prompts);
      message.success("Comparison prompts saved successfully!");
    } catch (error) {
      console.error("Failed to save prompts:", error);
      message.error("Failed to save prompts");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      const res = await promptsAPI.resetUserPrompts();

      form.setFieldsValue({
        system_prompt: res.data.compare_prompts.system_prompt,
        user_prompt: res.data.compare_prompts.user_prompt,
      });

      message.success("Prompts reset to defaults!");
    } catch (error) {
      console.error("Failed to reset prompts:", error);
      message.error("Failed to reset prompts");
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
          tooltip="Defines the role and behavior of the AI for comparison tasks"
        >
          <TextArea
            rows={20}
            placeholder="Enter system prompt for comparison..."
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
          tooltip="Specific instructions for comparing guidelines"
        >
          <TextArea
            rows={20}
            placeholder="Enter user prompt for comparison..."
            className="font-mono text-sm"
          />
        </Form.Item>
      ),
    },
  ];

  return (
    <div className="px-8 py-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Comparison Prompt</h1>

      <Card className="shadow-sm">
        <Form form={form} layout="vertical">
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

export default ComparisonPromptPage;
