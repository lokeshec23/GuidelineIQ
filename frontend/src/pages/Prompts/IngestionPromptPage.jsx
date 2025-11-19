import PromptEditor from "../../components/PromptEditor";

const IngestionPromptPage = () => {
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Ingestion Prompt</h1>
      <PromptEditor pageType="ingestion" />
    </div>
  );
};

export default IngestionPromptPage;
