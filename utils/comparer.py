from typing import List, Dict, Any
from colorama import Fore, Back, Style
import time

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

def print_recommendation_report(results: List[Dict[str, Any]]):
    """
    Analyzes results and prints a tailored summary recommendation.
    Helps students learn which library fits specific conditions.
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}FINAL COMPARISON & RECOMMENDATIONS{Style.RESET_ALL}")
    
    # Map results
    res_map = {res["library_name"]: res for res in results}
    pymupdf_res = res_map.get("PyMuPDF (fitz)")
    pdfminer_res = res_map.get("pdfminer.six")
    plumber_res = res_map.get("pdfplumber")
    pypdf_res = res_map.get("pypdf")
    
    # 1. Processing Time Comparison
    fastest = min(results, key=lambda x: x["processing_time"])
    slowest = max(results, key=lambda x: x["processing_time"])
    speedup = slowest["processing_time"] / max(fastest["processing_time"], 0.0001)
    
    print(f"  • {Fore.GREEN}Speed Champion:{Fore.WHITE} {fastest['library_name']} ({fastest['processing_time']:.4f}s)")
    print(f"    {Style.DIM}Note: {fastest['library_name']} was {speedup:.1f}x faster than the slowest library ({slowest['library_name']}: {slowest['processing_time']:.4f}s).{Style.RESET_ALL}")
    
    # 2. Text Extraction Comparison
    most_text = max(results, key=lambda x: len(x["extracted_text"]))
    least_text = min(results, key=lambda x: len(x["extracted_text"]))
    print(f"  • {Fore.GREEN}Text Extraction Volume:{Fore.WHITE} {most_text['library_name']} extracted the most ({len(most_text['extracted_text']):,} characters).")
    if len(most_text["extracted_text"]) > len(least_text["extracted_text"]):
        diff = len(most_text["extracted_text"]) - len(least_text["extracted_text"])
        print(f"    {Style.DIM}Note: {least_text['library_name']} missed {diff:,} characters compared to the maximum extracted.{Style.RESET_ALL}")
        
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
        best_meta_desc = "None (No metadata extracted by any library)"
    print(f"  • {Fore.GREEN}Best Metadata Extraction:{Fore.WHITE} {best_meta_desc}")

    # 4. Best Table Extraction
    table_libs = [r["library_name"] for r in results if r["table_count"] != -1 and r["table_count"] > 0]
    if table_libs:
        best_table_desc = (
            f"pdfplumber and PyMuPDF. pdfplumber is recommended for table-heavy documents due to its "
            f"configurable visual grid parsing, while PyMuPDF is ideal for simple, fast table boundary checks."
        )
    else:
        best_table_desc = "None (No tables detected). If tables are present, pdfplumber is typically the best choice."
    print(f"  • {Fore.GREEN}Best Table Extraction:{Fore.WHITE} {best_table_desc}")

    # 5. Best Image Extraction
    img_counts = {r["library_name"]: r["image_count"] for r in results if r["image_count"] != -1}
    max_imgs = max(img_counts.values()) if img_counts else 0
    if max_imgs > 0:
        best_img_libs = [lib for lib, count in img_counts.items() if count == max_imgs]
        best_img_desc = f"{', '.join(best_img_libs)} (Detected {max_imgs} image(s)). PyMuPDF is recommended for extracting image binary streams."
    else:
        best_img_desc = "None (No images detected)"
    print(f"  • {Fore.GREEN}Best Image Extraction:{Fore.WHITE} {best_img_desc}")

    # 6. Layout Preservation Analysis (Learning notes)
    print(f"\n  {Fore.YELLOW}{Style.BRIGHT}[Layout Preservation Evaluation]{Style.RESET_ALL}")
    print(f"    - {Fore.MAGENTA}PyMuPDF:{Fore.WHITE} Best for keeping column reading order. Uses block grouping heuristics.")
    print(f"    - {Fore.MAGENTA}pdfplumber:{Fore.WHITE} Superior layout control. Allows character-by-character analysis and exact grid matching.")
    print(f"    - {Fore.MAGENTA}pdfminer.six:{Fore.WHITE} Reconstructs hierarchical structure, but runs slower and has complex APIs.")
    print(f"    - {Fore.MAGENTA}pypdf:{Fore.WHITE} Basic stream extraction. Often suffers from layout shifts (merged columns, missing spaces).")

    # 7. Recommendations logic based on PDF properties
    print(f"\n  {Fore.GREEN}{Style.BRIGHT}[Recommended Library for this Document]{Style.RESET_ALL}")
    
    has_tables = plumber_res and plumber_res.get("table_count", 0) > 0
    has_images = pymupdf_res and pymupdf_res.get("image_count", 0) > 0
    page_count = pymupdf_res.get("page_count", 1) if pymupdf_res else 1
    
    recommendation = ""
    reason = ""
    
    if has_tables:
        recommendation = "pdfplumber"
        reason = (
            "The document contains tables. pdfplumber provides the most detailed and customizible "
            "table extraction grid settings, returning structures directly as nested python lists of strings. "
            "It is highly recommended for structured financial or tabular sheets."
        )
    elif page_count > 15:
        recommendation = "PyMuPDF (fitz)"
        reason = (
            f"The document is relatively large ({page_count} pages) and has no complex tables. "
            f"PyMuPDF completed the analysis in {pymupdf_res['processing_time']:.4f}s (extremely fast) and uses "
            f"minimal memory due to its optimized C-engine backend. It is the best choice for high-throughput pipelines."
        )
    elif has_images:
        recommendation = "PyMuPDF (fitz)"
        reason = (
            "The document contains embedded images. PyMuPDF extracts full binary image objects quickly "
            "via simple xref mappings (get_images), and allows rendering pages as high-DPI rasters (pixmaps) easily."
        )
    else:
        # Default fallback
        recommendation = "PyMuPDF (fitz)"
        reason = (
            "For general-purpose digital text extraction without tables, PyMuPDF offers the best balance "
            "of speed, layout block preservation, font metadata detection, and clean text streams."
        )
        
    print(f"    🏆 {Fore.YELLOW}{Style.BRIGHT}{recommendation.upper()}{Fore.WHITE} is recommended for this PDF.")
    print(f"    {Fore.LIGHTBLACK_EX}Reason: {reason}{Style.RESET_ALL}\n")
