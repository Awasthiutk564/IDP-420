import pdfplumber
import time
from typing import Dict, Any, List
from .base_extractor import BaseExtractor

class PDFPlumberExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(name="pdfplumber", version=pdfplumber.__version__)

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        res = {"title": "Unknown", "author": "Unknown", "producer": "Unknown", "creation_date": "Unknown"}
        try:
            with pdfplumber.open(pdf_path) as pdf:
                meta = pdf.metadata
                if meta:
                    res["title"] = meta.get("Title") or "Unknown"
                    res["author"] = meta.get("Author") or "Unknown"
                    res["producer"] = meta.get("Producer") or "Unknown"
                    res["creation_date"] = meta.get("CreationDate") or "Unknown"
        except Exception:
            pass
        return res

    def extract_pages_raw(self, pdf_path: str) -> List[Dict[str, Any]]:
        pages_data = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    start_time = time.time()
                    width = float(page.width)
                    height = float(page.height)

                    # Extract tables
                    tables_raw = []
                    try:
                        # Extract table finder objects to get row/col grids
                        tbl_objs = page.find_tables()
                        for tbl in tbl_objs:
                            # tbl.bbox is (x0, top, x1, bottom)
                            tables_raw.append({
                                "bbox": (float(tbl.bbox[0]), float(tbl.bbox[1]), float(tbl.bbox[2]), float(tbl.bbox[3])),
                                "rows": len(tbl.rows),
                                "columns": len(tbl.cols),
                                "cells": tbl.extract()
                            })
                    except Exception:
                        pass

                    # Extract lines / vector graphics
                    lines = []
                    try:
                        for l in page.lines:
                            lines.append({
                                "x0": float(l["x0"]),
                                "y0": float(l["top"]),
                                "x1": float(l["x1"]),
                                "y1": float(l["bottom"])
                            })
                    except Exception:
                        pass

                    # Extract raw text
                    text = ""
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        pass

                    pages_data.append({
                        "page_number": idx + 1,
                        "width": width,
                        "height": height,
                        "tables": tables_raw,
                        "lines": lines,
                        "raw_text": text,
                        "processing_time": time.time() - start_time
                    })
        except Exception:
            pass
        return pages_data
