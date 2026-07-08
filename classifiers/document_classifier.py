from typing import Dict, Any, List

class DocumentClassifier:
    """
    Classifies a PDF into document types (Research Paper, Invoice, Book, Magazine, Patent, etc.)
    to dynamically prioritize different extraction strategies.
    """
    @staticmethod
    def classify(pages_data: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        # Heuristics based on text keywords, tables count, layout characteristics
        title = str(metadata.get("title", "")).lower()
        author = str(metadata.get("author", "")).lower()
        
        # Merge all page texts to run keyword diagnostics
        all_text = ""
        total_tables = 0
        total_images = 0
        for p in pages_data:
            all_text += p.get("raw_text", "") + "\n"
            total_tables += len(p.get("tables", []))
            total_images += p.get("images_count", len(p.get("images", [])))

        all_text_lower = all_text.lower()
        
        # Check heuristics
        if "invoice" in title or "invoice" in all_text_lower or "bill to" in all_text_lower or "total due" in all_text_lower:
            return "Invoice"
        if ("abstract" in all_text_lower or "introduction" in all_text_lower) and "references" in all_text_lower:
            if "formula" in all_text_lower or "equation" in all_text_lower or "theorem" in all_text_lower:
                return "Scientific Paper"
            return "Research Paper"
        if "patent application" in all_text_lower or ("patent" in all_text_lower and "inventor" in all_text_lower) or ("claims" in all_text_lower and "patent" in all_text_lower):
            return "Patent"
        if "court" in all_text_lower or "plaintiff" in all_text_lower or "defendant" in all_text_lower or "hereby agree" in all_text_lower:
            return "Legal Document"
        if "report" in title or "report" in all_text_lower or "development goals" in all_text_lower:
            return "Report"
        if total_images > len(pages_data) * 2 and total_tables == 0:
            return "Magazine"
        if len(pages_data) > 50:
            return "Book"
        
        return "Normal Document"
