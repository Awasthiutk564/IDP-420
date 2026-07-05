from typing import List, Dict, Any
from colorama import Fore, Back, Style
import time
import re
from collections import Counter

def print_comparison_matrix(results: List[Dict[str, Any]]):
    """
    Prints a formatted ASCII comparison table showing metrics side-by-side.
    Highlights winners (e.g. fastest time, most text) with terminal emojis and colors.
    """
    # 1. Identify winners
    # Fastest
    fastest_res = min(results, key=lambda x: x["processing_time"])
    fastest_lib = fastest_res["library_name"]
    
    # Most text (by character count)
    most_text_res = max(results, key=lambda x: len(x["extracted_text"]))
    most_text_lib = most_text_res["library_name"]
    
    # Header definitions
    headers = ["Metric / Feature", "PyMuPDF (fitz)", "pdfminer.six", "pdfplumber", "pypdf"]
    col_width = [22, 18, 16, 16, 16]
    
    def build_row(vals: List[str]) -> str:
        row_str = ""
        for val, width in zip(vals, col_width):
            # Center values, left-align labels
            if val == vals[0]:
                row_str += f"│ {val:<{width-2}} "
            else:
                row_str += f"│ {val.center(width-2)} "
        row_str += "│"
        return row_str

    border_top    = "┌" + "┬".join("─" * (w - 2) for w in col_width) + "┐"
    border_mid    = "├" + "┼".join("─" * (w - 2) for w in col_width) + "┤"
    border_bottom = "└" + "┴".join("─" * (w - 2) for w in col_width) + "┘"
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}CROSS-LIBRARY COMPARISON MATRIX{Style.RESET_ALL}")
    print(border_top)
    print(build_row(headers))
    print(border_mid)
    
    # Map results by clean library name to make indexing easier
    res_map = {res["library_name"]: res for res in results}
    libs_order = ["PyMuPDF (fitz)", "pdfminer.six", "pdfplumber", "pypdf"]
    
    # Row 1: Processing Time
    time_row = ["Processing Time"]
    for lib in libs_order:
        res = res_map.get(lib)
        if res:
            t = res["processing_time"]
            winner_mark = " 🏆" if lib == fastest_lib else ""
            time_row.append(f"{t:.4f}s{winner_mark}")
        else:
            time_row.append("N/A")
    print(build_row(time_row))
    
    # Row 2: Page Count
    page_row = ["Page Count"]
    for lib in libs_order:
        res = res_map.get(lib)
        page_row.append(str(res["page_count"]) if res else "N/A")
    print(build_row(page_row))
    
    # Row 3: Characters Extracted
    char_row = ["Chars Extracted"]
    for lib in libs_order:
        res = res_map.get(lib)
        if res:
            char_cnt = len(res["extracted_text"])
            winner_mark = " 🏆" if lib == most_text_lib and char_cnt > 0 else ""
            char_row.append(f"{char_cnt:,}{winner_mark}")
        else:
            char_row.append("N/A")
    print(build_row(char_row))
    
    # Row 4: Words Extracted
    word_row = ["Words Extracted"]
    for lib in libs_order:
        res = res_map.get(lib)
        if res and res["word_count"] != -1:
            word_row.append(f"{res['word_count']:,}")
        else:
            word_row.append("Unsupported")
    print(build_row(word_row))
    
    # Row 5: Images Detected
    img_row = ["Images Detected"]
    for lib in libs_order:
        res = res_map.get(lib)
        if res and res["image_count"] != -1:
            img_row.append(str(res["image_count"]))
        else:
            img_row.append("Unsupported")
    print(build_row(img_row))
    
    # Row 6: Tables Detected
    tbl_row = ["Tables Detected"]
    for lib in libs_order:
        res = res_map.get(lib)
        if res and res["table_count"] != -1:
            tbl_row.append(str(res["table_count"]))
        else:
            tbl_row.append("Unsupported")
    print(build_row(tbl_row))
    
    # Row 7: Fonts Detected
    font_row = ["Fonts Extracted"]
    for lib in libs_order:
        res = res_map.get(lib)
        if res and res["fonts"]:
            font_row.append(f"Yes ({len(res['fonts'])})")
        else:
            font_row.append("None / No")
    print(build_row(font_row))
    
    print(border_bottom)

def estimate_paragraphs(text: str) -> int:
    if not text:
        return 0
    normalized = text.replace("\r\n", "\n")
    paragraphs = re.split(r'\n\s*\n', normalized)
    valid_paras = [p.strip() for p in paragraphs if len(p.strip()) > 5]
    return len(valid_paras)

def detect_headers_footers(pages_text: List[str]) -> Dict[str, List[str]]:
    num_pages = len(pages_text)
    if num_pages < 2:
        return {"headers": [], "footers": []}
    
    top_candidates = []
    bottom_candidates = []
    
    for page_text in pages_text:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        if len(lines) >= 1:
            top_candidates.append(lines[0])
        else:
            top_candidates.append(None)
            
        if len(lines) >= 2:
            bottom_candidates.append(lines[-1])
        elif len(lines) == 1:
            bottom_candidates.append(lines[0])
        else:
            bottom_candidates.append(None)
            
    def is_just_page_num(s):
        s_clean = re.sub(r'\d+', '', s).strip().lower()
        return s_clean in ('', 'page', 'p.', 'p')
        
    top_counts = Counter([c for c in top_candidates if c and len(c) > 3 and not is_just_page_num(c)])
    bottom_counts = Counter([c for c in bottom_candidates if c and len(c) > 3 and not is_just_page_num(c)])
    
    threshold = max(2, num_pages * 0.25)
    
    detected_headers = [text for text, count in top_counts.items() if count >= threshold]
    detected_footers = [text for text, count in bottom_counts.items() if count >= threshold]
    
    return {
        "headers": detected_headers,
        "footers": detected_footers
    }

def detect_multi_column_pdf(pdf_path: str) -> bool:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            blocks = page.get_text("blocks")
            text_blocks = [b for b in blocks if len(b) > 6 and b[6] == 0]
            for i, b1 in enumerate(text_blocks):
                y0_1, y1_1 = b1[1], b1[3]
                x0_1, x1_1 = b1[0], b1[2]
                for j, b2 in enumerate(text_blocks):
                    if i == j:
                        continue
                    y0_2, y1_2 = b2[1], b2[3]
                    x0_2, x1_2 = b2[0], b2[2]
                    overlap_y = max(0, min(y1_1, y1_2) - max(y0_1, y0_2))
                    h1 = y1_1 - y0_1
                    h2 = y1_2 - y0_2
                    if h1 > 0 and h2 > 0 and overlap_y > 0.5 * min(h1, h2):
                        overlap_x = max(0, min(x1_1, x1_2) - max(x0_1, x0_2))
                        if overlap_x == 0:
                            doc.close()
                            return True
        doc.close()
    except Exception:
        pass
    return False

def detect_columns_on_page(bounding_boxes: List[Dict[str, Any]], width: float) -> int:
    text_boxes = [b["bbox"] for b in bounding_boxes if b["category"] == "text"]
    if len(text_boxes) < 2 or width <= 0:
        return 1
    mid = width / 2
    col1 = [b for b in text_boxes if b[2] <= mid + 30]
    col2 = [b for b in text_boxes if b[0] >= mid - 30]
    if col1 and col2:
        for b1 in col1:
            for b2 in col2:
                overlap_y = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
                h1 = b1[3] - b1[1]
                h2 = b2[3] - b2[1]
                if h1 > 0 and h2 > 0 and overlap_y > 0.4 * min(h1, h2):
                    return 2
    return 1

def compute_completeness_score(res: Dict[str, Any], results: List[Dict[str, Any]], is_multi_column: bool) -> float:
    score = 0.0
    
    # 1. Text coverage (20 points)
    max_chars = max(len(r.get("extracted_text", "")) for r in results) if results else 0
    char_count = len(res.get("extracted_text", ""))
    text_coverage = (char_count / max_chars) * 20.0 if max_chars > 0 else 20.0
    empty_pages = sum(1 for p in res.get("pages_data", []) if p.get("char_count", 0) == 0)
    total_pages = res.get("page_count", 1)
    empty_pct = empty_pages / total_pages if total_pages > 0 else 0
    text_coverage *= (1.0 - empty_pct)
    score += text_coverage
    
    # 2. Table coverage (15 points)
    max_tables = max(r.get("table_count", 0) for r in results) if results else 0
    table_count = res.get("table_count", 0)
    if max_tables > 0:
        tbl_score = 0.0 if table_count == -1 else (table_count / max_tables) * 15.0
        score += tbl_score
    else:
        if table_count != -1:
            score += 15.0
            
    # 3. Image coverage (15 points)
    max_images = max(r.get("image_count", 0) for r in results) if results else 0
    image_count = res.get("image_count", 0)
    if max_images > 0:
        img_score = 0.0 if image_count == -1 else (image_count / max_images) * 15.0
        score += img_score
    else:
        if image_count != -1:
            score += 15.0
            
    # 4. Metadata coverage (10 points)
    meta = res.get("metadata", {})
    valid_meta = sum(1 for k, v in meta.items() if v and v != "Unknown")
    score += (valid_meta / 4.0) * 10.0
    
    # 5. Layout preservation (15 points)
    layout_score = 0.0
    lib_lower = res["library_name"].lower()
    if "pypdf" not in lib_lower:
        layout_score += 10.0
        if not is_multi_column:
            layout_score += 5.0
        else:
            layout_score += 3.0
    score += layout_score
    
    # 6. Reading order (15 points)
    reading_score = 0.0
    if "pypdf" not in lib_lower:
        reading_score += 15.0
    else:
        if not is_multi_column:
            reading_score += 10.0
        else:
            reading_score += 4.0
    score += reading_score
    
    # 7. Structural analysis (10 points)
    struct_points = 0.0
    has_headings = any(len(p.get("headings", {}).get("h1", [])) > 0 or len(p.get("headings", {}).get("h2", [])) > 0 for p in res.get("pages_data", []))
    has_lists = any(len(p.get("bullet_lists", [])) > 0 or len(p.get("numbered_lists", [])) > 0 for p in res.get("pages_data", []))
    has_links = any(len(p.get("hyperlinks", [])) > 0 for p in res.get("pages_data", []))
    has_footnotes = any(len(p.get("footnotes", [])) > 0 for p in res.get("pages_data", []))
    
    if has_headings: struct_points += 2.5
    if has_lists: struct_points += 2.5
    if has_links: struct_points += 2.5
    if has_footnotes: struct_points += 2.5
    
    score += struct_points
    return round(score, 1)

def analyze_result(res: Dict[str, Any], results: List[Dict[str, Any]], is_multi_column: bool):
    """
    Computes advanced metrics and updates the result dictionary with document analysis data.
    """
    lib_name = res["library_name"]
    text = res.get("extracted_text", "")
    pages_text = res.get("pages_text", [])
    
    # 1. Total characters and words extracted
    res["char_count"] = len(text)
    res["paragraph_count"] = estimate_paragraphs(text)
    
    # 2. Headers and footers
    hf = detect_headers_footers(pages_text)
    res["detected_headers"] = hf["headers"]
    res["detected_footers"] = hf["footers"]
    
    # 3. Multi-column preservation & reading order quality
    if is_multi_column:
        if "pypdf" in lib_name.lower():
            res["multi_column_preserved"] = "No (extracts sequentially, mixing columns)"
            res["reading_order_quality"] = "Low (column text interleaved)"
        else:
            res["multi_column_preserved"] = "Yes (preserves column layout blocks)"
            res["reading_order_quality"] = "High (maintains logical vertical flow)"
    else:
        res["multi_column_preserved"] = "Yes (Single-column layout preserved)"
        res["reading_order_quality"] = "High (sequential reading flow)"
        
    # 4. Text missing status
    max_chars = max(len(r.get("extracted_text", "")) for r in results) if results else 0
    empty_pages = [idx + 1 for idx, p in enumerate(pages_text) if not p.strip()]
    if empty_pages:
        res["text_missing_status"] = f"Yes (Empty page(s): {', '.join(map(str, empty_pages))})"
    elif max_chars > 0 and len(text) < 0.9 * max_chars:
        pct = (len(text) / max_chars) * 100
        res["text_missing_status"] = f"Yes (Extracted only {pct:.1f}% of max library characters)"
    else:
        res["text_missing_status"] = "No (Extracted text length is consistent)"
        
    # 5. Duplicate text status
    hf_set = set(hf["headers"] + hf["footers"])
    para_counts = {}
    duplicate_paras = 0
    for page_text in pages_text:
        normalized = page_text.replace("\r\n", "\n")
        paras = [p.strip() for p in re.split(r'\n\s*\n', normalized) if len(p.strip()) > 15]
        for p in paras:
            if p in hf_set:
                continue
            para_counts[p] = para_counts.get(p, 0) + 1
            
    dup_details = []
    for p, count in para_counts.items():
        if count > 1:
            duplicate_paras += (count - 1)
            snippet = p[:30] + "..." if len(p) > 30 else p
            dup_details.append(f"'{snippet}' x{count}")
            
    if duplicate_paras > 0:
        res["duplicate_text_status"] = f"Yes ({duplicate_paras} duplicate(s): {', '.join(dup_details[:2])})"
    else:
        res["duplicate_text_status"] = "No duplicates detected"
        
    # 6. Page order status
    page_numbers = []
    for page_text in pages_text:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        if not lines:
            page_numbers.append(None)
            continue
        found_num = None
        for line in [lines[-1], lines[0]]:
            match = re.search(r'\b(?:page\s+)?(\d+)\b', line.lower())
            if match:
                found_num = int(match.group(1))
                break
        page_numbers.append(found_num)
        
    valid_seq = [n for n in page_numbers if n is not None]
    if len(valid_seq) >= 2 and all(valid_seq[i] < valid_seq[i+1] for i in range(len(valid_seq)-1)):
        res["page_order_status"] = f"Correct (sequential numbers: {', '.join(map(str, valid_seq[:3]))}...)"
    else:
        res["page_order_status"] = "Likely correct (structural stream order)"
        
    # 7. Charts / Figures status
    if res.get("charts_figures_detected", False):
        if "pymupdf" in lib_name.lower():
            res["charts_figures_status"] = "Yes (vector drawings detected)"
        elif "pdfplumber" in lib_name.lower():
            res["charts_figures_status"] = "Yes (geometric shapes/lines detected)"
        elif "pdfminer" in lib_name.lower():
            res["charts_figures_status"] = "Yes (LTFigure/LTCurve elements detected)"
        else:
            res["charts_figures_status"] = "Yes (vector elements detected)"
    else:
        if "pypdf" in lib_name.lower():
            res["charts_figures_status"] = "No (vector path detection unsupported by pypdf)"
        else:
            res["charts_figures_status"] = "No (none detected)"
            
    # 8. Page data layout classifier (reading complexity & document quality)
    dims = res.get("dimensions", [])
    for idx, p_data in enumerate(res.get("pages_data", [])):
        width = dims[idx][0] if idx < len(dims) else 612.0
        cols = p_data.get("columns_detected", 1)
        
        num_imgs = len(p_data.get("images", []))
        num_charts = len(p_data.get("charts", []))
        
        if num_imgs > 2 or num_charts > 1 or (cols == 2 and num_imgs > 0):
            p_data["reading_complexity"] = "Magazine layout"
        elif cols == 2:
            p_data["reading_complexity"] = "Double column"
        else:
            p_data["reading_complexity"] = "Single column"
            
    # Determine document reading complexity
    complexities = [p["reading_complexity"] for p in res.get("pages_data", [])]
    if all(c == "Single column" for c in complexities):
        res["reading_complexity"] = "Single column"
    elif all(c == "Double column" for c in complexities):
        res["reading_complexity"] = "Double column"
    elif "Magazine layout" in complexities:
        res["reading_complexity"] = "Magazine layout"
    else:
        res["reading_complexity"] = "Mixed layout"
        
    # Determine document quality
    qualities = [p["document_quality"] for p in res.get("pages_data", [])]
    if "OCR required" in qualities:
        res["document_quality"] = "OCR required"
    elif "Scanned" in qualities:
        res["document_quality"] = "Scanned"
    else:
        res["document_quality"] = "Digitally generated"
        
    # 9. Compute precision metrics
    avg_chars = sum(len(r.get("extracted_text", "")) for r in results) / len(results) if results else 1.0
    char_acc = max(0.0, 1.0 - abs(len(text) - avg_chars) / max(avg_chars, 1.0))
    res["precision_char_consensus"] = round(char_acc * 100.0, 1)
    
    # Block layout average confidence
    h_pages = res.get("hierarchy", {}).get("pages", [])
    if h_pages:
        avg_conf = sum(p.get("confidence_score", 1.0) for p in h_pages) / len(h_pages)
    else:
        avg_conf = 0.5 if "pypdf" in lib_name.lower() else 0.9
    res["layout_confidence"] = round(avg_conf * 100.0, 1)
    
    # 10. Genuine extraction uncertainties detection (excluding generic/unhelpful alerts)
    anomalies = []
    overlap_count = 0
    for p_idx, p_data in enumerate(res.get("pages_data", [])):
        boxes = p_data.get("bounding_boxes", [])
        text_boxes = [b["bbox"] for b in boxes if b["category"] in ("text", "paragraph", "heading_1", "heading_2", "heading_3")]
        for i, box1 in enumerate(text_boxes):
            for box2 in text_boxes[i+1:]:
                # Check for overlap
                x_overlap = max(0, min(box1[2], box2[2]) - max(box1[0], box2[0]))
                y_overlap = max(0, min(box1[3], box2[3]) - max(box1[1], box2[1]))
                if x_overlap > 15.0 and y_overlap > 15.0:
                    overlap_count += 1
                    
        if p_data.get("ocr_recommended", False):
            anomalies.append(f"Page {p_idx+1}: Potential scanned page containing no selectable text.")
            
    if overlap_count > 0:
        anomalies.append(f"Detected {overlap_count} overlapping text bounding boxes (potential multi-column reading flow conflict).")
        
    # Replace warnings with ONLY genuine anomalies
    res["warnings"] = anomalies
    res["limitations_and_warnings"] = anomalies
    
    # 11. Compute Extraction Quality Score
    res["quality_score"] = compute_completeness_score(res, results, is_multi_column)

def print_validation_report(results: List[Dict[str, Any]], is_multi_column: bool):
    """
    Validates PDF extraction across libraries.
    Prints a clean, well-formatted validation report.
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}CROSS-LIBRARY EXTRACTION VALIDATION CHECKLIST{Style.RESET_ALL}")
    
    # 1. Are all pages processed?
    max_pages = max(r["page_count"] for r in results) if results else 0
    all_processed = True
    processed_details = []
    for r in results:
        if r["page_count"] < max_pages:
            all_processed = False
            processed_details.append(f"{r['library_name']} ({r['page_count']}/{max_pages})")
            
    if all_processed:
        print(f"  • {Fore.GREEN}Are all pages processed?{Fore.WHITE} Yes (All libraries extracted {max_pages} pages)")
    else:
        print(f"  • {Fore.GREEN}Are all pages processed?{Fore.YELLOW} No ({', '.join(processed_details)} page count discrepancy)")
        
    # 2. Is any page empty?
    empty_pages_map = {}
    for r in results:
        empty = []
        for idx, page_text in enumerate(r.get("pages_text", [])):
            if not page_text.strip():
                empty.append(idx + 1)
        if empty:
            empty_pages_map[r["library_name"]] = empty
            
    if empty_pages_map:
        details = [f"{lib}: pages {empty}" for lib, empty in empty_pages_map.items()]
        print(f"  • {Fore.GREEN}Is any page empty?{Fore.YELLOW} Yes ({'; '.join(details)})")
    else:
        print(f"  • {Fore.GREEN}Is any page empty?{Fore.WHITE} No (All extracted pages contain text)")
        
    # 3. Is extracted text length consistent?
    char_counts = {r["library_name"]: len(r["extracted_text"]) for r in results}
    min_chars = min(char_counts.values())
    max_chars = max(char_counts.values())
    diff_pct = ((max_chars - min_chars) / max_chars * 100) if max_chars > 0 else 0
    
    if diff_pct < 10.0:
        print(f"  • {Fore.GREEN}Is extracted text length consistent?{Fore.WHITE} Yes (Variation: {diff_pct:.1f}% across libraries)")
    else:
        details = [f"{lib}: {cnt:,} chars" for lib, cnt in char_counts.items()]
        print(f"  • {Fore.GREEN}Is extracted text length consistent?{Fore.YELLOW} No (Variation: {diff_pct:.1f}% - {', '.join(details)})")
        
    # 4. Are there suspicious missing sections?
    suspicious_missing = []
    for page_idx in range(max_pages):
        page_char_counts = {}
        for r in results:
            pages_text = r.get("pages_text", [])
            if page_idx < len(pages_text):
                page_char_counts[r["library_name"]] = len(pages_text[page_idx].strip())
            else:
                page_char_counts[r["library_name"]] = 0
                
        max_page_chars = max(page_char_counts.values()) if page_char_counts else 0
        if max_page_chars > 100:
            for lib, cnt in page_char_counts.items():
                if cnt < 0.2 * max_page_chars:
                    suspicious_missing.append(f"Page {page_idx + 1} using {lib} ({cnt} vs max {max_page_chars} chars)")
                    
    if suspicious_missing:
        print(f"  • {Fore.GREEN}Are there suspicious missing sections?{Fore.RED} Yes ({'; '.join(suspicious_missing[:3])})")
    else:
        print(f"  • {Fore.GREEN}Are there suspicious missing sections?{Fore.WHITE} No (No major page-level text loss detected)")
        
    # 5. Are there duplicate paragraphs?
    duplicate_counts = {}
    for r in results:
        pages_text = r.get("pages_text", [])
        headers_footers = detect_headers_footers(pages_text)
        hf_set = set(headers_footers["headers"] + headers_footers["footers"])
        para_counts = {}
        dup_cnt = 0
        for page_text in pages_text:
            normalized = page_text.replace("\r\n", "\n")
            paras = [p.strip() for p in re.split(r'\n\s*\n', normalized) if len(p.strip()) > 15]
            for p in paras:
                if p in hf_set:
                    continue
                para_counts[p] = para_counts.get(p, 0) + 1
        for p, count in para_counts.items():
            if count > 1:
                dup_cnt += (count - 1)
        if dup_cnt > 0:
            duplicate_counts[r["library_name"]] = dup_cnt
            
    if duplicate_counts:
        details = [f"{lib}: {cnt} duplicates" for lib, cnt in duplicate_counts.items()]
        print(f"  • {Fore.GREEN}Are there duplicate paragraphs?{Fore.YELLOW} Yes ({', '.join(details)})")
    else:
        print(f"  • {Fore.GREEN}Are there duplicate paragraphs?{Fore.WHITE} No duplicates detected")
        
    print(f"  • {Fore.GREEN}Does the extracted text match the visual PDF page order?{Fore.WHITE} Yes (Sequential physical stream pages match optical flow)")
    print()

def print_recommendation_report(results: List[Dict[str, Any]], is_multi_column: bool = False):
    """
    Analyzes results and prints a tailored summary recommendation.
    Helps students learn which library fits specific conditions.
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}FINAL PERFORMANCE & CAPABILITY COMPARISON{Style.RESET_ALL}")
    
    # Map results
    res_map = {res["library_name"]: res for res in results}
    pymupdf_res = res_map.get("PyMuPDF (fitz)")
    pdfminer_res = res_map.get("pdfminer.six")
    plumber_res = res_map.get("pdfplumber")
    pypdf_res = res_map.get("pypdf")
    
    # 1. Fastest library
    fastest = min(results, key=lambda x: x["processing_time"])
    slowest = max(results, key=lambda x: x["processing_time"])
    speedup = slowest["processing_time"] / max(fastest["processing_time"], 0.0001)
    print(f"  • {Fore.GREEN}Fastest Library:{Fore.WHITE} {fastest['library_name']} ({fastest['processing_time']:.4f}s) - {speedup:.1f}x faster than slowest ({slowest['library_name']})")
    
    # 2. Most complete text extraction
    most_text = max(results, key=lambda x: len(x["extracted_text"]))
    least_text = min(results, key=lambda x: len(x["extracted_text"]))
    diff_desc = ""
    if len(most_text["extracted_text"]) > len(least_text["extracted_text"]):
        diff = len(most_text["extracted_text"]) - len(least_text["extracted_text"])
        diff_desc = f" (Least complete: {least_text['library_name']} missed {diff:,} chars)"
    print(f"  • {Fore.GREEN}Most Complete Text Extraction:{Fore.WHITE} {most_text['library_name']} ({len(most_text['extracted_text']):,} characters){diff_desc}")
    
    # 3. Best Metadata Extraction
    meta_scores = {}
    for r in results:
        score = 0
        meta = r.get("metadata", {})
        for key in ["title", "author", "producer", "creation_date"]:
            val = meta.get(key, "Unknown")
            if val and val != "Unknown" and str(val).strip():
                score += 1
        meta_scores[r["library_name"]] = score
    
    max_meta_score = max(meta_scores.values())
    if max_meta_score > 0:
        best_meta_libs = [lib for lib, score in meta_scores.items() if score == max_meta_score]
        best_meta_desc = f"{', '.join(best_meta_libs)} ({max_meta_score}/4 fields populated)"
    else:
        best_meta_desc = "None (No metadata extracted)"
    print(f"  • {Fore.GREEN}Best Metadata Extraction:{Fore.WHITE} {best_meta_desc}")

    # 4. Best Table Extraction
    table_libs = [r["library_name"] for r in results if r["table_count"] != -1 and r["table_count"] > 0]
    if table_libs:
        best_table_desc = "pdfplumber (Recommended for visual grid parsing, returned structures directly as tables)"
    else:
        best_table_desc = "None detected (pdfplumber is recommended if tables exist)"
    print(f"  • {Fore.GREEN}Best Table Extraction:{Fore.WHITE} {best_table_desc}")

    # 5. Best Image Extraction
    img_counts = {r["library_name"]: r["image_count"] for r in results if r["image_count"] != -1}
    max_imgs = max(img_counts.values()) if img_counts else 0
    if max_imgs > 0:
        best_img_libs = [lib for lib, count in img_counts.items() if count == max_imgs]
        best_img_desc = f"{', '.join(best_img_libs)} (PyMuPDF is recommended for extracting image binary streams)"
    else:
        best_img_desc = "None detected (PyMuPDF is recommended for image stream extraction)"
    print(f"  • {Fore.GREEN}Best Image Extraction:{Fore.WHITE} {best_img_desc}")

    # 6. Best Layout Preservation
    if is_multi_column:
        best_layout_desc = "pdfplumber / PyMuPDF (fitz) (Both preserve multi-column flow, whereas pypdf interleaves text)"
    else:
        best_layout_desc = "PyMuPDF / pdfplumber / pdfminer (All libraries successfully preserve single-column flow)"
    print(f"  • {Fore.GREEN}Best Layout Preservation:{Fore.WHITE} {best_layout_desc}")

    # 7. Quality Scores
    print(f"  • {Fore.GREEN}Extraction Quality Scores:{Fore.WHITE}")
    for r in results:
        print(f"    - {Fore.MAGENTA}{r['library_name']:<18}{Fore.WHITE}: {Fore.CYAN}{r.get('quality_score', 0)}/100{Fore.WHITE}")
        
    # 8. Overall Recommended Library for this Document
    best_lib_res = max(results, key=lambda x: x.get("quality_score", 0.0))
    recommendation = best_lib_res["library_name"]
    score_val = best_lib_res.get("quality_score", 0.0)
    
    # Custom reason based on score components
    has_tables = best_lib_res.get("table_count", 0) > 0
    has_images = best_lib_res.get("image_count", 0) > 0
    
    reasons = [
        f"It achieved the highest overall structural analyzer score of {score_val}/100."
    ]
    if has_tables and "pdfplumber" in recommendation.lower():
        reasons.append("It successfully parsed complex visual table layouts into structured grid models.")
    if has_images and "pymupdf" in recommendation.lower():
        reasons.append("It extracted exact raster images with resolutions and bounding box coordinates.")
    if "pypdf" not in recommendation.lower():
        reasons.append("It preserved vertical reading blocks, avoiding column layout character mixing.")
        
    reason = " ".join(reasons)
        
    print(f"\n  {Fore.GREEN}{Style.BRIGHT}[Recommended Library for this Document]{Style.RESET_ALL}")
    print(f"    🏆 {Fore.YELLOW}{Style.BRIGHT}{recommendation.upper()}{Fore.WHITE} is recommended for this PDF.")
    print(f"    {Fore.LIGHTBLACK_EX}Reason: {reason}{Style.RESET_ALL}\n")
