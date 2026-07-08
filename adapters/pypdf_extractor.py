import pypdf
import time
from typing import Dict, Any, List
from .base_extractor import BaseExtractor

class PyPDFExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(name="pypdf", version=pypdf.__version__)

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        res = {
            "title": "Unknown",
            "author": "Unknown",
            "producer": "Unknown",
            "creation_date": "Unknown",
            "is_encrypted": False,
            "form_fields": {}
        }
        try:
            with open(pdf_path, "rb") as fp:
                reader = pypdf.PdfReader(fp)
                res["is_encrypted"] = reader.is_encrypted
                meta = reader.metadata
                if meta:
                    res["title"] = meta.title or "Unknown"
                    res["author"] = meta.author or "Unknown"
                    res["producer"] = meta.producer or "Unknown"
                    res["creation_date"] = meta.creation_date or "Unknown"
                
                # Try getting interactive form fields (AcroForm)
                try:
                    fields = reader.get_fields()
                    if fields:
                        for k, v in fields.items():
                            res["form_fields"][k] = str(v.get("/V", ""))
                except Exception:
                    pass
        except Exception:
            pass
        return res

    def extract_pages_raw(self, pdf_path: str) -> List[Dict[str, Any]]:
        pages_data = []
        try:
            with open(pdf_path, "rb") as fp:
                reader = pypdf.PdfReader(fp)
                for idx, page in enumerate(reader.pages):
                    start_time = time.time()
                    try:
                        mediabox = page.mediabox
                        width = float(mediabox.width)
                        height = float(mediabox.height)
                    except Exception:
                        width, height = 612.0, 792.0

                    text = ""
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        pass

                    pages_data.append({
                        "page_number": idx + 1,
                        "width": width,
                        "height": height,
                        "raw_text": text,
                        "processing_time": time.time() - start_time
                    })
        except Exception:
            pass
        return pages_data
