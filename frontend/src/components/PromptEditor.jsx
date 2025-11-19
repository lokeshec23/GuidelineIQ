import React, { useState, useEffect } from "react";
import { Card, Tabs, Button, message, Input, Space } from "antd";
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

  // Load correct prompts depending on pageType
  useEffect(() => {
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
  }, [pageType, ingestPrompts, comparePrompts]);

  // Save prompts to PromptContext
  const savePrompts = () => {
    if (pageType === "ingestion") {
      setIngestPrompts({
        user_prompt: userPrompt,
        system_prompt: systemPrompt,
      });
    } else {
      setComparePrompts({
        user_prompt: userPrompt,
        system_prompt: systemPrompt,
      });
    }

    message.success("Prompt saved successfully");
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
