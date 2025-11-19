import PromptEditor from "../../components/PromptEditor";
import { settingsAPI } from "../../services/api";

const ComparisonPromptPage = () => {
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Comparison Prompt</h1>

      <PromptEditor
        pageType="comparison"
        loadAPI={settingsAPI.getSettings}
        saveAPI={settingsAPI.updateSettings}
      />
    </div>
  );
};

export default ComparisonPromptPage;
