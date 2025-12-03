import React, { useState, useEffect } from "react";
import { Card, Tabs, Button, Input, Space } from "antd";
import { showToast } from "../utils/toast";
import {
  DEFAULT_INGEST_PROMPT_USER,
  DEFAULT_COMPARISON_PROMPT_USER,
  DEFAULT_INGEST_PROMPT_SYSTEM,
  DEFAULT_COMPARISON_PROMPT_SYSTEM,
} from "../constants/prompts";

import { usePrompts } from "../context/PromptContext";

const { TextArea } = Input;

const PromptEditor = ({ pageType }) => {
  const { ingestPrompts, setIngestPrompts, comparePrompts, setComparePrompts } =
    usePrompts();

  const [userPrompt, setUserPrompt] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");

  const storageKey = `prompt_${pageType}`;

  // Load prompts from sessionStorage OR context OR defaults
  useEffect(() => {
    const saved = sessionStorage.getItem(storageKey);

    if (saved) {
      const parsed = JSON.parse(saved);

      setUserPrompt(parsed.user_prompt || "");
      setSystemPrompt(parsed.system_prompt || "");
      return;
    }

    if (pageType === "ingestion") {
      setUserPrompt(ingestPrompts.user_prompt || DEFAULT_INGEST_PROMPT_USER);
      setSystemPrompt(
        ingestPrompts.system_prompt || DEFAULT_INGEST_PROMPT_SYSTEM
      );
    } else if (pageType === "comparison") {
      setUserPrompt(
        comparePrompts.user_prompt || DEFAULT_COMPARISON_PROMPT_USER
      );
      setSystemPrompt(
        comparePrompts.system_prompt || DEFAULT_COMPARISON_PROMPT_SYSTEM
      );
    }
  }, [pageType]);

  // Save to context + sessionStorage
  const savePrompts = () => {
    const data = { user_prompt: userPrompt, system_prompt: systemPrompt };

    sessionStorage.setItem(storageKey, JSON.stringify(data));

    if (pageType === "ingestion") {
      setIngestPrompts(data);
    } else {
      setComparePrompts(data);
    }

    showToast.success("Prompt saved");
  };

  // Reset to defaults
  const resetPrompts = () => {
    let defaultUser = "";
    let defaultSystem = "";

    if (pageType === "ingestion") {
      defaultUser = DEFAULT_INGEST_PROMPT_USER;
      defaultSystem = DEFAULT_INGEST_PROMPT_SYSTEM;
    } else {
      defaultUser = DEFAULT_COMPARISON_PROMPT_USER;
      defaultSystem = DEFAULT_COMPARISON_PROMPT_SYSTEM;
    }

    setUserPrompt(defaultUser);
    setSystemPrompt(defaultSystem);

    const data = { user_prompt: defaultUser, system_prompt: defaultSystem };

    sessionStorage.setItem(storageKey, JSON.stringify(data));

    if (pageType === "ingestion") {
      setIngestPrompts(data);
    } else {
      setComparePrompts(data);
    }

    showToast.success("Reset to default prompts");
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
                  <Button onClick={resetPrompts}>Reset</Button>
                  <Button danger onClick={() => setUserPrompt("")}>
                    Clear
                  </Button>
                  <Button type="primary" onClick={savePrompts}>
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
                  <Button onClick={resetPrompts}>Reset</Button>
                  <Button danger onClick={() => setSystemPrompt("")}>
                    Clear
                  </Button>
                  <Button type="primary" onClick={savePrompts}>
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
