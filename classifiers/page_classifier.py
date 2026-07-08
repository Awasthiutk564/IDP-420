import re
from typing import Dict, Any

class PageClassifier:
    """
    Classifies page types (Cover Page, Table of Contents, References,Normal Page, Index, Appendix)
    to enable dynamic page extraction pipelines.
    """
    @staticmethod
    def classify_page(page_data: Dict[str, Any], page_num: int, total_pages: int) -> str:
        text = page_data.get("raw_text", "").strip()
        text_lower = text.lower()
        
        if page_num == 1 and len(text) < 300:
            return "Cover Page"
        if "table of contents" in text_lower or "contents" in text_lower or re.search(r'\.{5,}', text):
            if page_num <= 3:
                return "Table of Contents"
        if "references" in text_lower or "bibliography" in text_lower:
            if page_num >= total_pages - 2 or len(text_lower) > 500:
                return "References"
        if "appendix" in text_lower and page_num >= total_pages - 3:
            return "Appendix"
        if "index" in text_lower and page_num == total_pages:
            return "Index"
            
        return "Normal Page"
