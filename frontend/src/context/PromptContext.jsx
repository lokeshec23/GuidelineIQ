import React, { createContext, useContext, useState } from "react";

const PromptContext = createContext(null);

export const PromptProvider = ({ children }) => {
  const [ingestPrompts, setIngestPrompts] = useState({
    system_prompt: "",
    user_prompt: "",
  });

  const [comparePrompts, setComparePrompts] = useState({
    system_prompt: "",
    user_prompt: "",
  });

  return (
    <PromptContext.Provider
      value={{
        ingestPrompts,
        setIngestPrompts,
        comparePrompts,
        setComparePrompts,
      }}
    >
      {children}
    </PromptContext.Provider>
  );
};

export const usePrompts = () => useContext(PromptContext);
