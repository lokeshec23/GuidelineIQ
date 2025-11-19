import React, { useState, useEffect } from "react";
import { Card, Tabs, Button, message, Input, Space } from "antd";

const { TextArea } = Input;

const PromptEditor = ({ pageType, loadAPI, saveAPI }) => {
  const [userPrompt, setUserPrompt] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      const res = await loadAPI(pageType);
      setUserPrompt(res.data.user_prompt || "");
      setSystemPrompt(res.data.system_prompt || "");
    } catch {
      message.error("Failed to load prompts");
    }
  };

  const savePrompts = async () => {
    setLoading(true);
    try {
      await saveAPI(pageType, {
        user_prompt: userPrompt,
        system_prompt: systemPrompt,
      });
      message.success("Prompt saved");
    } catch {
      message.error("Failed to save");
    }
    setLoading(false);
  };

  const clearPrompt = (type) => {
    if (type === "user") setUserPrompt("");
    else setSystemPrompt("");
  };

  return (
    <Card>
      <Tabs
        defaultActiveKey="user"
        items={[
          {
            key: "user",
            label: "User Prompt",
            children: (
              <>
                <TextArea
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  style={{ minHeight: "300px" }}
                  className="font-mono text-sm"
                />
                <Space className="mt-4">
                  <Button danger onClick={() => clearPrompt("user")}>
                    Clear
                  </Button>
                  <Button
                    type="primary"
                    loading={loading}
                    onClick={savePrompts}
                  >
                    Save
                  </Button>
                </Space>
              </>
            ),
          },
          {
            key: "system",
            label: "System Prompt",
            children: (
              <>
                <TextArea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  style={{ minHeight: "300px" }}
                  className="font-mono text-sm"
                />
                <Space className="mt-4">
                  <Button danger onClick={() => clearPrompt("system")}>
                    Clear
                  </Button>
                  <Button
                    type="primary"
                    loading={loading}
                    onClick={savePrompts}
                  >
                    Save
                  </Button>
                </Space>
              </>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default PromptEditor;
