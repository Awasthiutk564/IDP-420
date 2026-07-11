import time
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import (
    DocumentNode, PageNode, SectionNode, BlockNode, LineNode, WordNode, CharacterNode
)

class StageText(Stage):
    def __init__(self):
        super().__init__(name="Character & Text Extraction")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        pymupdf_adapter = next((a for a in adapters if a.name == "PyMuPDF"), None)
        pdfminer_adapter = next((a for a in adapters if a.name == "pdfminer.six"), None)
        
        # Extract raw page contents
        pymupdf_pages = pymupdf_adapter.extract_pages_raw(pdf_path) if pymupdf_adapter else []
        pdfminer_pages = pdfminer_adapter.extract_pages_raw(pdf_path) if pdfminer_adapter else []
        
        page_classifier = classifiers.get("page")
        
        for idx in range(doc_graph.page_count):
            start_time = time.time()
            pm_page = pymupdf_pages[idx] if idx < len(pymupdf_pages) else {}
            min_page = pdfminer_pages[idx] if idx < len(pdfminer_pages) else {}
            
            width = pm_page.get("width", min_page.get("width", 612.0))
            height = pm_page.get("height", min_page.get("height", 792.0))
            
            # Determine page classification (TOC, Cover Page, Normal, etc.)
            p_type = "Normal Page"
            if page_classifier:
                p_type = page_classifier.classify_page(pm_page, idx + 1, doc_graph.page_count)
                
            page_node = PageNode(page_number=idx + 1, width=width, height=height, page_type=p_type)
            page_node.hyperlinks = pm_page.get("links", [])
            
            # Build word and line nodes from line runs (resolving multi-column overlapping text bugs)
            lines_runs = min_page.get("lines_runs", [])
            line_nodes = []
            
            # Unicode ligature normalization mapper
            def clean_text_ligatures(t: str) -> str:
                ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "œ": "oe", "æ": "ae"}
                for lig, repl in ligatures.items():
                    t = t.replace(lig, repl)
                return t
            
            for line_run in lines_runs:
                char_list = line_run.get("characters", [])
                if not char_list:
                    continue
                
                # Sort line characters horizontally to ensure optical order
                char_list = sorted(char_list, key=lambda c: c["bbox"][0])
                
                word_nodes = []
                curr_word_chars = []
                
                UNICODE_SUPERSCRIPTS = {
                    '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
                    '⁺': '+', '⁻': '-', '⁼': '=', '⁽': '(', '⁾': ')', 'ⁿ': 'n'
                }
                UNICODE_SUBSCRIPTS = {
                    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
                    '₊': '+', '₋': '-', '₌': '=', '₍': '(', '₎': ')'
                }

                for char_idx, char_data in enumerate(char_list):
                    is_superscript = False
                    is_subscript = False
                    
                    raw_c = char_data["char"]
                    unicode_super = UNICODE_SUPERSCRIPTS.get(raw_c)
                    unicode_sub = UNICODE_SUBSCRIPTS.get(raw_c)
                    
                    if unicode_super:
                        is_superscript = True
                        norm_char = unicode_super
                    elif unicode_sub:
                        is_subscript = True
                        norm_char = unicode_sub
                    else:
                        norm_char = clean_text_ligatures(raw_c)
                        
                    if char_idx > 0 and not is_superscript and not is_subscript:
                        prev_char_data = char_list[char_idx - 1]
                        prev_char_text = prev_char_data["char"]
                        
                        if prev_char_text.strip() and norm_char.strip() and prev_char_text not in [" ", "\n"] and norm_char not in [" ", "\n"]:
                            curr_bbox = char_data["bbox"]
                            prev_bbox = prev_char_data["bbox"]
                            
                            prev_origin_y = prev_bbox[3]
                            curr_origin_y = curr_bbox[3]
                            baseline_offset = prev_origin_y - curr_origin_y
                            
                            prev_font_size = prev_char_data["font_size"]
                            curr_font_size = char_data["font_size"]
                            
                            if curr_font_size < prev_font_size:
                                if baseline_offset > prev_font_size * 0.1:
                                    is_superscript = True
                                elif baseline_offset < -prev_font_size * 0.05:
                                    is_subscript = True

                    if is_superscript:
                        super_node = CharacterNode(
                            char="^",
                            bbox=(char_data["bbox"][0] - 0.5, char_data["bbox"][1], char_data["bbox"][0], char_data["bbox"][3]),
                            font_name=char_data["font_name"],
                            font_size=char_data["font_size"],
                            font_style=char_data["font_style"],
                            color=char_data["color"],
                            confidence=0.99,
                            provenance={"library": "StageText/SuperscriptPreserver", "version": "1.0", "confidence": 0.99, "fallback": True}
                        )
                        curr_word_chars.append(super_node)
                    elif is_subscript:
                        sub_node = CharacterNode(
                            char="_",
                            bbox=(char_data["bbox"][0] - 0.5, char_data["bbox"][1], char_data["bbox"][0], char_data["bbox"][3]),
                            font_name=char_data["font_name"],
                            font_size=char_data["font_size"],
                            font_style=char_data["font_style"],
                            color=char_data["color"],
                            confidence=0.99,
                            provenance={"library": "StageText/SubscriptPreserver", "version": "1.0", "confidence": 0.99, "fallback": True}
                        )
                        curr_word_chars.append(sub_node)

                    char_node = CharacterNode(
                        char=norm_char,
                        bbox=char_data["bbox"],
                        font_name=char_data["font_name"],
                        font_size=char_data["font_size"],
                        font_style=char_data["font_style"],
                        color=char_data["color"],
                        confidence=0.99,
                        provenance={
                            "library": "pdfminer.six",
                            "version": "20221105",
                            "confidence": 0.99,
                            "fallback": False
                        }
                    )
                    
                    is_space = char_data["char"] == " "
                    # If it's a space, we don't append the space glyph to the word characters, but trigger a word split
                    if is_space:
                        if curr_word_chars:
                            # Commit word
                            w_text = "".join(c.char for c in curr_word_chars).strip()
                            if w_text:
                                w_x0 = min(c.bbox[0] for c in curr_word_chars)
                                w_y0 = min(c.bbox[1] for c in curr_word_chars)
                                w_x1 = max(c.bbox[2] for c in curr_word_chars)
                                w_y1 = max(c.bbox[3] for c in curr_word_chars)
                                word_nodes.append(WordNode(
                                    text=w_text,
                                    bbox=(w_x0, w_y0, w_x1, w_y1),
                                    confidence=0.99,
                                    provenance={"library": "pdfminer.six", "version": "20221105", "confidence": 0.99, "fallback": False},
                                    characters=list(curr_word_chars)
                                ))
                            curr_word_chars = []
                        continue
                    
                    curr_word_chars.append(char_node)
                    is_last = char_idx == len(char_list) - 1
                    
                    is_gap = False
                    if not is_last:
                        next_char = char_list[char_idx + 1]
                        # Space detection: if next character starts further than current character width plus a threshold
                        # Typically width of space is ~2.5 - 3.5pt depending on font size
                        char_width = char_data["bbox"][2] - char_data["bbox"][0]
                        threshold = max(2.0, char_width * 0.25)
                        if next_char["bbox"][0] - char_data["bbox"][2] > threshold:
                            is_gap = True
                            
                    if is_gap or is_last:
                        if curr_word_chars:
                            w_text = "".join(c.char for c in curr_word_chars).strip()
                            if w_text:
                                w_x0 = min(c.bbox[0] for c in curr_word_chars)
                                w_y0 = min(c.bbox[1] for c in curr_word_chars)
                                w_x1 = max(c.bbox[2] for c in curr_word_chars)
                                w_y1 = max(c.bbox[3] for c in curr_word_chars)
                                word_nodes.append(WordNode(
                                    text=w_text,
                                    bbox=(w_x0, w_y0, w_x1, w_y1),
                                    confidence=0.99,
                                    provenance={"library": "pdfminer.six", "version": "20221105", "confidence": 0.99, "fallback": False},
                                    characters=list(curr_word_chars)
                                ))
                            curr_word_chars = []
                
                if word_nodes:
                    word_nodes = sorted(word_nodes, key=lambda w: w.bbox[0])
                    lx0 = min(w.bbox[0] for w in word_nodes)
                    ly0 = min(w.bbox[1] for w in word_nodes)
                    lx1 = max(w.bbox[2] for w in word_nodes)
                    ly1 = max(w.bbox[3] for w in word_nodes)
                    
                    line_nodes.append(LineNode(
                        text=" ".join(w.text for w in word_nodes),
                        bbox=(lx0, ly0, lx1, ly1),
                        confidence=0.99,
                        provenance={"library": "pdfminer.six", "version": "20221105", "confidence": 0.99, "fallback": False},
                        words=word_nodes
                    ))
            
            # Sort page lines vertically
            line_nodes = sorted(line_nodes, key=lambda l: (l.bbox[1], l.bbox[0]))
            
            page_node.statistics["temp_lines"] = line_nodes
            page_node.statistics["processing_time"] = time.time() - start_time
            doc_graph.pages.append(page_node)
            
        return doc_graph
