// src/pages/Prompts/PromptsPage.jsx

import React, { useState, useEffect } from "react";
import { Tabs, Form, Input, Button, Spin } from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import { promptsAPI } from "../../services/api";
import { showToast } from "../../utils/toast";

const { TabPane } = Tabs;
const { TextArea } = Input;

const PromptsPage = () => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);
    const [activeTab, setActiveTab] = useState("ingest");

    useEffect(() => {
        fetchPrompts();
    }, []);

    const fetchPrompts = async () => {
        try {
            setFetching(true);
            const res = await promptsAPI.getUserPrompts();
            form.setFieldsValue({
                ingest_system_prompt: res.data.ingest_prompts.system_prompt,
                ingest_user_prompt: res.data.ingest_prompts.user_prompt,
                compare_system_prompt: res.data.compare_prompts.system_prompt,
                compare_user_prompt: res.data.compare_prompts.user_prompt,
            });
        } catch (error) {
            console.error("Failed to fetch prompts:", error);
            // Toast is handled by API interceptor
        } finally {
            setFetching(false);
        }
    };

    const handleSave = async () => {
        try {
            setLoading(true);
            const values = form.getFieldsValue();

            const prompts = {
                ingest_prompts: {
                    system_prompt: values.ingest_system_prompt,
                    user_prompt: values.ingest_user_prompt,
                },
                compare_prompts: {
                    system_prompt: values.compare_system_prompt,
                    user_prompt: values.compare_user_prompt,
                },
            };

            await promptsAPI.saveUserPrompts(prompts);
            showToast.success("Prompts saved successfully!");
        } catch (error) {
            console.error("Failed to save prompts:", error);
            // Toast is handled by API interceptor
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        try {
            setLoading(true);
            const res = await promptsAPI.resetUserPrompts();

            form.setFieldsValue({
                ingest_system_prompt: res.data.ingest_prompts.system_prompt,
                ingest_user_prompt: res.data.ingest_prompts.user_prompt,
                compare_system_prompt: res.data.compare_prompts.system_prompt,
                compare_user_prompt: res.data.compare_prompts.user_prompt,
            });

            showToast.success("Prompts reset to defaults!");
        } catch (error) {
            console.error("Failed to reset prompts:", error);
            // Toast is handled by API interceptor
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

    return (
        <div className="px-8 py-6">
            <div className="mb-6">
                <h1 className="text-2xl font-semibold text-gray-800">Manage Prompts</h1>
                <p className="text-gray-500 mt-1">
                    Customize your LLM prompts for ingestion and comparison tasks
                </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
                <Form form={form} layout="vertical">
                    <Tabs activeKey={activeTab} onChange={setActiveTab}>
                        <TabPane tab="Ingest Prompts" key="ingest">
                            <Form.Item
                                label="System Prompt"
                                name="ingest_system_prompt"
                                tooltip="Defines the role and behavior of the AI"
                            >
                                <TextArea
                                    rows={8}
                                    placeholder="Enter system prompt for ingestion..."
                                    className="font-mono text-sm"
                                />
                            </Form.Item>

                            <Form.Item
                                label="User Prompt"
                                name="ingest_user_prompt"
                                tooltip="Specific instructions for processing guidelines"
                            >
                                <TextArea
                                    rows={12}
                                    placeholder="Enter user prompt for ingestion..."
                                    className="font-mono text-sm"
                                />
                            </Form.Item>
                        </TabPane>

                        <TabPane tab="Compare Prompts" key="compare">
                            <Form.Item
                                label="System Prompt"
                                name="compare_system_prompt"
                                tooltip="Defines the role and behavior of the AI"
                            >
                                <TextArea
                                    rows={8}
                                    placeholder="Enter system prompt for comparison..."
                                    className="font-mono text-sm"
                                />
                            </Form.Item>

                            <Form.Item
                                label="User Prompt"
                                name="compare_user_prompt"
                                tooltip="Specific instructions for comparing guidelines"
                            >
                                <TextArea
                                    rows={12}
                                    placeholder="Enter user prompt for comparison..."
                                    className="font-mono text-sm"
                                />
                            </Form.Item>
                        </TabPane>
                    </Tabs>

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
            </div>
        </div>
    );
};

export default PromptsPage;
