from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode

class StageMetadata(Stage):
    def __init__(self):
        super().__init__(name="Metadata Extraction & Classification")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        # Find pypdf and pyMuPDF adapters
        pypdf_adapter = next((a for a in adapters if a.name == "pypdf"), None)
        pymupdf_adapter = next((a for a in adapters if a.name == "PyMuPDF"), None)
        
        meta = {}
        if pypdf_adapter:
            meta = pypdf_adapter.extract_metadata(pdf_path)
        elif pymupdf_adapter:
            meta = pymupdf_adapter.extract_metadata(pdf_path)

        # Ensure keys exist
        if "title" not in meta or not meta["title"] or meta["title"] == "Unknown":
            meta["title"] = "Unknown"
        if "author" not in meta or not meta["author"] or meta["author"] == "Unknown":
            meta["author"] = "Unknown"

        # Populate pages baseline (dimensions, etc) using PyMuPDF
        raw_pages = []
        if pymupdf_adapter:
            raw_pages = pymupdf_adapter.extract_pages_raw(pdf_path)
        
        doc_graph.page_count = len(raw_pages)

        # Inferred Metadata from Cover Page (Page 1) text blocks
        if doc_graph.page_count > 0 and raw_pages:
            p1_blocks = raw_pages[0].get("blocks", [])
            text_blocks = [b for b in p1_blocks if b.get("type", "text") == "text"]
            
            # Infer Title if Unknown
            if meta["title"] == "Unknown" and text_blocks:
                # Find first descriptive block that isn't metadata metadata
                for b in text_blocks[:3]:
                    txt = b["text"].replace("\n", " ").strip()
                    if len(txt) > 10 and not any(x in txt.lower() for x in ["http", "issn", "doi", "draft"]):
                        meta["title"] = txt
                        break
            
            # Infer Author if Unknown
            if meta["author"] == "Unknown" and text_blocks:
                for b in text_blocks:
                    txt = b["text"].replace("\n", " ").strip()
                    if any(x in txt.lower() for x in ["united nations", "solutions network", "department of", "commission"]):
                        meta["author"] = txt
                        break
                    elif "by " in txt.lower():
                        meta["author"] = txt.split("by ")[1]
                        break

        doc_graph.metadata = meta
        
        # Run document classification
        doc_classifier = classifiers.get("document")
        if doc_classifier:
            doc_graph.document_type = doc_classifier.classify(raw_pages, meta)
            
        return doc_graph
