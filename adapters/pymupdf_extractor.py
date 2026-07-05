import fitz
import os
import time
from typing import Dict, Any, List
from .base_extractor import BaseExtractor

class PyMuPDFExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(name="PyMuPDF", version=fitz.__version__)

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        doc = fitz.open(pdf_path)
        meta = doc.metadata
        res = {
            "title": meta.get("title") or "Unknown",
            "author": meta.get("author") or "Unknown",
            "producer": meta.get("producer") or "Unknown",
            "creation_date": meta.get("creationDate") or "Unknown"
        }
        doc.close()
        return res

    def extract_pages_raw(self, pdf_path: str) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        pages_data = []
        for page_num in range(len(doc)):
            start_time = time.time()
            page = doc[page_num]
            width = page.rect.width
            height = page.rect.height
            
            # Extract links
            links = []
            for link in page.get_links():
                if "uri" in link:
                    r = link["from"]
                    links.append({
                        "url": link["uri"],
                        "bbox": (r.x0, r.y0, r.x1, r.y1)
                    })

            # Extract raw images
            images = []
            try:
                for img_info in page.get_image_info(hashes=False):
                    bbox = img_info.get("bbox", (0, 0, 0, 0))
                    images.append({
                        "bbox": bbox,
                        "width": img_info.get("width", 0),
                        "height": img_info.get("height", 0),
                        "resolution": f"{img_info.get('xres', 72)}x{img_info.get('yres', 72)} dpi"
                    })
            except Exception:
                pass

            # Extract text blocks
            blocks_raw = []
            text_instances = page.get_text("blocks")
            for b in text_instances:
                # b = (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5 and isinstance(b[4], str) and b[4].strip():
                    blocks_raw.append({
                        "bbox": (b[0], b[1], b[2], b[3]),
                        "text": b[4].strip(),
                        "type": "text" if b[6] == 0 else "image"
                    })

            # Extract drawings/paths
            drawings = []
            try:
                drawings = page.get_drawings()
            except Exception:
                pass

            pages_data.append({
                "page_number": page_num + 1,
                "width": width,
                "height": height,
                "blocks": blocks_raw,
                "images": images,
                "links": links,
                "drawings_count": len(drawings),
                "raw_text": page.get_text("text") or "",
                "processing_time": time.time() - start_time
            })
        doc.close()
        return pages_data
