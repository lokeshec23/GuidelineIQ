"""Quick syntax check for all modified files"""
import ast
import os
import sys

files = [
    r"rag_pipeline\indexing\qdrant_manager.py",
    r"rag_pipeline\indexing\embedder.py",
    r"rag_pipeline\extraction\llm_verifier.py",
    r"rag_pipeline\extraction\llm_extractor.py",
    r"rag_pipeline\retrieval\bm25_retriever.py",
    r"rag_pipeline\ingestion\pdf_parser.py",
    r"utils\llm_provider.py",
    r"rag_pipeline\pipeline.py",
]

os.chdir(os.path.dirname(os.path.abspath(__file__)))
errors = []

for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            ast.parse(fh.read())
        print(f"OK  {f}")
    except SyntaxError as e:
        print(f"FAIL {f}: {e}")
        errors.append(f)

if errors:
    print(f"\n{len(errors)} file(s) have syntax errors")
    sys.exit(1)
else:
    print(f"\nAll {len(files)} files passed syntax check")
