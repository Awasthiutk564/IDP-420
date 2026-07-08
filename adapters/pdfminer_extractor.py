import os
import time
from typing import Dict, Any, List
from .base_extractor import BaseExtractor

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTChar, LTFigure, LTImage, LTCurve, LTLine, LTRect
from pdfminer.pdftypes import resolve1

class PDFMinerExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(name="pdfminer.six", version="20221105")

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        res = {"title": "Unknown", "author": "Unknown", "producer": "Unknown", "creation_date": "Unknown"}
        try:
            with open(pdf_path, "rb") as fp:
                parser = PDFParser(fp)
                doc = PDFDocument(parser)
                info = doc.info
                if info:
                    info_dict = info[0]
                    for k, v in info_dict.items():
                        k_str = k.lower()
                        val_str = "Unknown"
                        if isinstance(v, bytes):
                            val_str = v.decode("utf-8", errors="ignore")
                        elif isinstance(v, str):
                            val_str = v
                        
                        if k_str == "title": res["title"] = val_str
                        elif k_str == "author": res["author"] = val_str
                        elif k_str == "producer": res["producer"] = val_str
                        elif k_str == "creationdate": res["creation_date"] = val_str
        except Exception:
            pass
        return res

    def extract_pages_raw(self, pdf_path: str) -> List[Dict[str, Any]]:
        pages_data = []
        try:
            with open(pdf_path, "rb") as fp:
                rsrcmgr = PDFResourceManager()
                laparams = LAParams()
                device = PDFPageAggregator(rsrcmgr, laparams=laparams)
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                
                for page_idx, page in enumerate(PDFPage.get_pages(fp)):
                    start_time = time.time()
                    try:
                        x0, y0, x1, y1 = page.mediabox
                        width = x1 - x0
                        height = y1 - y0
                    except Exception:
                        width, height = 612.0, 792.0

                    interpreter.process_page(page)
                    layout = device.get_result()

                    lines_runs = []
                    text_blocks = []
                    images_count = 0
                    curves_count = 0

                    for element in layout:
                        if isinstance(element, LTTextBox):
                            text_blocks.append({
                                "bbox": (element.x0, height - element.y1, element.x1, height - element.y0),
                                "text": element.get_text().strip()
                            })
                            for line in element:
                                if hasattr(line, '__iter__'):
                                    line_chars = []
                                    for character in line:
                                        if isinstance(character, LTChar):
                                            f_name = character.fontname or "Unknown"
                                            if "+" in f_name:
                                                f_name = f_name.split("+")[1]
                                            
                                            style = "Regular"
                                            if "bold" in f_name.lower():
                                                style = "Bold"
                                            elif "italic" in f_name.lower() or "oblique" in f_name.lower():
                                                style = "Italic"

                                            line_chars.append({
                                                "char": character.get_text(),
                                                "bbox": (character.x0, height - character.y1, character.x1, height - character.y0),
                                                "font_name": f_name,
                                                "font_size": round(character.size or 10.0, 1),
                                                "font_style": style,
                                                "color": "#000000"
                                            })
                                    if line_chars:
                                        lines_runs.append({
                                            "bbox": (line.x0, height - line.y1, line.x1, height - line.y0),
                                            "characters": line_chars
                                        })
                        elif isinstance(element, (LTImage, LTFigure)):
                            images_count += 1
                        elif isinstance(element, (LTCurve, LTLine, LTRect)):
                            curves_count += 1

                    pages_data.append({
                        "page_number": page_idx + 1,
                        "width": width,
                        "height": height,
                        "lines_runs": lines_runs,
                        "blocks": text_blocks,
                        "images_count": images_count,
                        "curves_count": curves_count,
                        "processing_time": time.time() - start_time
                    })
                device.close()
        except Exception:
            pass
        return pages_data
