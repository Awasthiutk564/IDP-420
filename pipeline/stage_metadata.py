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

        # Check if title looks like a filename (contains underscores, hyphens, file extensions, or no spaces with camelCase)
        import re
        looks_like_filename = False
        title_str = meta.get("title", "")
        if title_str and title_str != "Unknown":
            if "_" in title_str or "-" in title_str or re.search(r'\.[a-zA-Z]{3,4}$', title_str):
                looks_like_filename = True
            elif " " not in title_str and re.search(r'[a-z][A-Z]', title_str):
                looks_like_filename = True
            elif any(x in title_str.lower() for x in ["ats", "optimized", "resume", "cv", "portfolio"]):
                looks_like_filename = True

        if looks_like_filename:
            meta["original_embedded_title"] = title_str
            # Inferred visible title from first text block (processed further down)

        # Populate pages baseline (dimensions, etc) using PyMuPDF
        raw_pages = []
        if pymupdf_adapter:
            raw_pages = pymupdf_adapter.extract_pages_raw(pdf_path)
        
        doc_graph.page_count = len(raw_pages)

        # Inferred Metadata from Cover Page (Page 1) text blocks
        if doc_graph.page_count > 0 and raw_pages:
            p1_blocks = raw_pages[0].get("blocks", [])
            text_blocks = [b for b in p1_blocks if b.get("type", "text") == "text"]
            
            # Infer Title if Unknown or looks like a filename
            if (meta["title"] == "Unknown" or "original_embedded_title" in meta) and text_blocks:
                # Find first descriptive block that isn't metadata metadata
                for b in text_blocks[:3]:
                    txt = b["text"].replace("\n", " ").strip()
                    if len(txt) > 3 and not any(x in txt.lower() for x in ["http", "issn", "doi", "draft"]):
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
        
        # Scan raw page blocks for contact details (email, phone, urls, github, linkedin)
        import re
        
        def is_contact_info_line(text: str) -> bool:
            t = text.strip()
            if not t:
                return False
            # Check for email and short length
            if re.search(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', t):
                if len(t) < 100:
                    return True
            # Matches contact prefixes followed by text
            contact_prefixes = r'^(email|phone|mobile|linkedin|github|portfolio|website|address|contact)\b'
            if re.match(contact_prefixes, t, re.IGNORECASE) and len(t) < 120:
                return True
            # Phone numbers check
            phone_pattern = r'^\+?[\d\-\(\)\s]{7,20}$'
            if re.match(phone_pattern, t.replace("Phone:", "").replace("Mobile:", "").strip()) and len(t) < 30:
                return True
            # Pure LinkedIn or GitHub URLs
            if re.match(r'^(https?://)?(www\.)?(linkedin\.com|github\.com|twitter\.com)/[a-zA-Z0-9_\-\./]+$', t.lower()):
                return True
            # Embedded phone number check
            if re.search(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', t) and len(t) < 60:
                return True
            return False

        contact_lines = []
        for p_idx, page in enumerate(raw_pages):
            for block in page.get("blocks", []):
                text = block.get("text", "")
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                for line in lines:
                    if is_contact_info_line(line):
                        contact_lines.append(line)
        doc_graph.metadata["contact_lines"] = list(set(contact_lines))
        
        # Run document classification
        doc_classifier = classifiers.get("document")
        if doc_classifier:
            doc_graph.document_type = doc_classifier.classify(raw_pages, meta)
            
        return doc_graph
