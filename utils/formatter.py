import colorama
from colorama import Fore, Back, Style
from typing import Dict, Any, List

# Initialize colorama for Windows terminal styling support
colorama.init(autoreset=True)

def format_banner(text: str, color_code: str = Fore.CYAN) -> str:
    """Creates a beautiful banner for section headers."""
    border = "=" * 80
    return f"\n{color_code}{Style.BRIGHT}{border}\n{text.center(80)}\n{border}{Style.RESET_ALL}"

def format_library_header(library_name: str) -> str:
    """Formats the heading for a specific library's extraction results."""
    title = f" ANALYSIS BY: {library_name.upper()} "
    padding = (80 - len(title)) // 2
    border_left = "★" * padding
    border_right = "★" * (80 - len(title) - padding)
    return f"\n{Fore.MAGENTA}{Style.BRIGHT}{border_left}{Back.MAGENTA}{Fore.WHITE}{title}{Style.RESET_ALL}{Fore.MAGENTA}{Style.BRIGHT}{border_right}{Style.RESET_ALL}\n"

def format_metric(label: str, value: Any, is_supported: bool = True) -> str:
    """Helper to format a single metric with consistent alignment and colors."""
    label_part = f"{Fore.GREEN}{label:<22}"
    if not is_supported or value == -1:
        val_part = f"{Fore.YELLOW}{Style.DIM}Unsupported{Style.RESET_ALL}"
    elif value is None or value == "Unknown" or value == "":
        val_part = f"{Fore.RED}{Style.DIM}Unknown{Style.RESET_ALL}"
    else:
        val_part = f"{Fore.WHITE}{Style.BRIGHT}{value}{Style.RESET_ALL}"
    return f"  {label_part} : {val_part}"

def get_dimensions_summary(dimensions: List[tuple]) -> str:
    """
    Summarizes page dimensions. 
    If all pages are the same size, prints it once.
    Otherwise, lists individual page sizes (or a summary if too many pages).
    """
    if not dimensions:
        return "Unknown"
    
    # Check if all pages have the exact same dimensions
    first_dim = dimensions[0]
    all_same = all(dim == first_dim for dim in dimensions)
    
    if all_same:
        return f"{first_dim[0]:.2f} x {first_dim[1]:.2f} pt (All {len(dimensions)} pages)"
    
    # Otherwise, show details for up to 5 pages, then summarize
    summary_parts = []
    for idx, (w, h) in enumerate(dimensions[:5]):
        summary_parts.append(f"P{idx+1}: {w:.1f}x{h:.1f}")
    if len(dimensions) > 5:
        summary_parts.append(f"... (+{len(dimensions)-5} more)")
    
    return ", ".join(summary_parts)

def format_text_snippet(text: str, snippet_length: int = 800) -> str:
    """Boxes the first N characters of extracted text for clean display."""
    if not text:
        return f"  {Fore.RED}{Style.DIM}[No text extracted or text is empty]{Style.RESET_ALL}"
    
    # Clean text: normalize whitespace/newlines for preview
    lines = text.splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    cleaned_text = " \n  │ ".join(cleaned_lines[:15])  # Take up to 15 non-empty lines
    
    # Truncate clean preview if too long
    snippet = text[:snippet_length].strip()
    # Normalize snippet newlines to look clean in the box
    formatted_snippet = ""
    for line in snippet.splitlines()[:20]: # Limit to 20 lines to keep terminal readable
        # Truncate very long single lines to fit standard terminal
        if len(line) > 72:
            formatted_snippet += f"  │ {line[:69]}...\n"
        else:
            formatted_snippet += f"  │ {line}\n"
            
    if len(text) > snippet_length or len(snippet.splitlines()) > 20:
        formatted_snippet += f"  │ {Fore.YELLOW}... [TRUNCATED - {len(text) - len(snippet)} characters remaining] ...{Style.RESET_ALL}\n"
        
    border_top = f"  ┌─── EXTRACTED TEXT SNIPPET (First {snippet_length} chars) ──────────────────────────"
    border_bottom = "  └─────────────────────────────────────────────────────────────────────────────"
    
    return f"{Fore.LIGHTBLACK_EX}{border_top}\n{formatted_snippet.rstrip()}\n{Fore.LIGHTBLACK_EX}{border_bottom}{Style.RESET_ALL}"

def print_result_report(result: Dict[str, Any]):
    """Prints the full detailed report for a single library processor."""
    print(format_library_header(result["library_name"]))
    
    # 1. Processing and Page Info
    print(format_metric("Processing Time", f"{result['processing_time']:.4f} seconds"))
    print(format_metric("Total Pages", result["page_count"]))
    dim_summary = get_dimensions_summary(result["dimensions"])
    print(format_metric("Page Dimensions", dim_summary))
    print()
    
    # 2. Metadata Section
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Metadata]{Style.RESET_ALL}")
    meta = result["metadata"]
    print(format_metric("Title", meta.get("title")))
    print(format_metric("Author", meta.get("author")))
    print(format_metric("Producer", meta.get("producer")))
    print(format_metric("Creation Date", meta.get("creation_date")))
    print()
    
    # 3. Extraction Metrics & Precision
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Extraction Metrics & Precision]{Style.RESET_ALL}")
    print(format_metric("Total Chars Extracted", f"{result.get('char_count', len(result['extracted_text'])):,}"))
    print(format_metric("Total Words Extracted", f"{result['word_count']:,}" if result["word_count"] != -1 else -1))
    print(format_metric("Number of Text Blocks", result["block_count"]))
    print(format_metric("Paragraphs (Estimated)", result.get("paragraph_count", 0)))
    print(format_metric("Number of Images", result["image_count"]))
    print(format_metric("Number of Tables", result["table_count"]))
    print(format_metric("Char Consensus Accuracy", f"{result.get('precision_char_consensus', 0.0)}%"))
    print(format_metric("Layout Parser Confidence", f"{result.get('layout_confidence', 0.0)}%"))
    print(format_metric("Document Reading Complexity", result.get("reading_complexity", "Unknown")))
    print(format_metric("Document Quality Class", result.get("document_quality", "Unknown")))
    print(format_metric("Extraction Quality Score", f"{result.get('quality_score', 0.0)}/100"))
    print()
    
    # 4. Fonts Section
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Fonts Detected]{Style.RESET_ALL}")
    if result["fonts"]:
        fonts_list = ", ".join(result["fonts"][:10])
        if len(result["fonts"]) > 10:
            fonts_list += f" (+{len(result['fonts'])-10} more)"
        print(f"  {Fore.WHITE}{fonts_list}")
    else:
        print(f"  {Fore.YELLOW}{Style.DIM}No font metadata extracted or unsupported{Style.RESET_ALL}")
    print()

    # 5. Advanced Layout & Structural Analysis
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Layout & Structural Analysis]{Style.RESET_ALL}")
    print(format_metric("Reading Order Quality", result.get("reading_order_quality", "Unknown")))
    print(format_metric("Text Missing Status", result.get("text_missing_status", "Unknown")))
    print(format_metric("Duplicate Text Status", result.get("duplicate_text_status", "Unknown")))
    print(format_metric("Page Order Status", result.get("page_order_status", "Unknown")))
    print(format_metric("Multi-column Preserved", result.get("multi_column_preserved", "Unknown")))
    print(format_metric("Charts/Figures Status", result.get("charts_figures_status", "Unknown")))
    print()

    # 6. Headers and Footers Detected
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Headers & Footers Detected]{Style.RESET_ALL}")
    headers = result.get("detected_headers", [])
    footers = result.get("detected_footers", [])
    if headers:
        print(f"    {Fore.GREEN}Headers: {Fore.WHITE}{'; '.join(headers[:3])}")
    else:
        print(f"    {Fore.GREEN}Headers: {Fore.YELLOW}{Style.DIM}None detected{Style.RESET_ALL}")
    if footers:
        print(f"    {Fore.GREEN}Footers: {Fore.WHITE}{'; '.join(footers[:3])}")
    else:
        print(f"    {Fore.GREEN}Footers: {Fore.YELLOW}{Style.DIM}None detected{Style.RESET_ALL}")
    print()

    # 7. Page-by-Page Detailed Structural Analysis
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Page-by-Page Structural Analysis]{Style.RESET_ALL}")
    for idx, p_data in enumerate(result.get("pages_data", [])):
        print(f"  {Fore.LIGHTBLACK_EX}---------------------------------------")
        print(f"  {Fore.MAGENTA}{Style.BRIGHT}PAGE {p_data['page_number']}{Style.RESET_ALL}")
        print(f"  {Fore.LIGHTBLACK_EX}---------------------------------------")
        
        headers_found = p_data.get("headers", [])
        print(f"    {Fore.GREEN}Header                : {Fore.WHITE}{'; '.join(headers_found[:2]) if headers_found else 'None'}")
        
        h1s = p_data.get("headings", {}).get("h1", [])
        h2s = p_data.get("headings", {}).get("h2", [])
        h3s = p_data.get("headings", {}).get("h3", [])
        
        main_title = "None"
        if h1s:
            main_title = h1s[0]
        elif h2s:
            main_title = h2s[0]
        elif p_data.get("paragraphs"):
            main_title = p_data["paragraphs"][0][:60] + "..." if len(p_data["paragraphs"][0]) > 60 else p_data["paragraphs"][0]
            
        print(f"    {Fore.GREEN}Main Title            : {Fore.WHITE}{main_title}")
        
        subheadings = []
        if len(h1s) > 1: subheadings.extend(h1s[1:3])
        subheadings.extend(h2s[:3])
        subheadings.extend(h3s[:3])
        subheadings_str = "; ".join([s[:40] + "..." if len(s) > 40 else s for s in subheadings])
        print(f"    {Fore.GREEN}Subheadings           : {Fore.WHITE}{subheadings_str if subheadings_str else 'None'}")
        
        print(f"    {Fore.GREEN}Paragraph Count       : {Fore.WHITE}{len(p_data.get('paragraphs', []))}")
        print(f"    {Fore.GREEN}Word Count            : {Fore.WHITE}{p_data.get('word_count', 0)}")
        print(f"    {Fore.GREEN}Character Count       : {Fore.WHITE}{p_data.get('char_count', 0)}")
        
        print(f"    {Fore.GREEN}Tables Found          : {Fore.WHITE}{len(p_data.get('tables', []))}")
        print(f"    {Fore.GREEN}Images Found          : {Fore.WHITE}{len(p_data.get('images', []))}")
        print(f"    {Fore.GREEN}Charts Found          : {Fore.WHITE}{len(p_data.get('charts', []))}")
        
        print(f"    {Fore.GREEN}Reading Complexity    : {Fore.WHITE}{p_data.get('reading_complexity', 'Unknown')}")
        print(f"    {Fore.GREEN}Columns Detected      : {Fore.WHITE}{p_data.get('columns_detected', 1)}")
        
        print(f"    {Fore.GREEN}Page Headers          : {Fore.WHITE}{'; '.join(p_data.get('headers', [])[:2]) if p_data.get('headers') else 'None'}")
        print(f"    {Fore.GREEN}Page Footers          : {Fore.WHITE}{'; '.join(p_data.get('footers', [])[:2]) if p_data.get('footers') else 'None'}")
        
        fonts_used = [f"{f['fontname']} ({f['size']}pt, {f['style']})" for f in p_data.get("fonts", [])[:3]]
        print(f"    {Fore.GREEN}Fonts                 : {Fore.WHITE}{', '.join(fonts_used) if fonts_used else 'None'}")
        
        bbox_summary = f"Total bboxes: {len(p_data.get('bounding_boxes', []))}"
        print(f"    {Fore.GREEN}Bounding Boxes        : {Fore.WHITE}{bbox_summary}")
        
        if p_data.get("ocr_recommended", False):
            print(f"    {Fore.YELLOW}⚠ OCR Recommendation: Selectable text is empty. Bounding boxes exist. Document quality classified as: {p_data.get('document_quality')}. OCR is highly recommended for this page.")
            
        for idx_i, img in enumerate(p_data.get("images", [])):
            bbox_fmt = ", ".join(f"{v:.1f}" for v in img["bbox"])
            print(f"      {Fore.CYAN}Image {idx_i+1} [{img.get('figure_type', 'photo').upper()}]")
            print(f"        Location    : ({bbox_fmt})")
            print(f"        Width/Height: {img['width']} x {img['height']}")
            print(f"        Resolution  : {img.get('resolution', 'N/A')}")
            if img.get('caption'):
                print(f"        Caption     : {Fore.LIGHTWHITE_EX}\"{img['caption']}\"{Fore.RESET}")
            
        for idx_t, tbl in enumerate(p_data.get("tables", [])):
            bbox_fmt = ", ".join(f"{v:.1f}" for v in tbl["bbox"])
            print(f"      {Fore.CYAN}Table {idx_t+1}")
            print(f"        Rows/Columns: {tbl['rows']} x {tbl['columns']}")
            print(f"        Location    : ({bbox_fmt})")
            print(f"        Confidence  : {tbl.get('confidence', 1.0)}")
            if tbl.get('caption'):
                print(f"        Caption     : {Fore.LIGHTWHITE_EX}\"{tbl['caption']}\"{Fore.RESET}")
            
        for idx_c, chrt in enumerate(p_data.get("charts", [])):
            bbox_fmt = ", ".join(f"{v:.1f}" for v in chrt["bbox"])
            print(f"      {Fore.CYAN}Chart {idx_c+1} [{chrt.get('figure_type', 'chart').upper()}]")
            print(f"        Type        : {chrt['chart_type']}")
            print(f"        Location    : ({bbox_fmt})")
            if chrt.get('caption'):
                print(f"        Caption     : {Fore.LIGHTWHITE_EX}\"{chrt['caption']}\"{Fore.RESET}")
            
        print(f"  {Fore.LIGHTBLACK_EX}---------------------------------------")
    print()
    
    # 8. Warnings & Genuine Extraction Uncertainties
    warnings_limits = result.get("limitations_and_warnings", result.get("warnings", []))
    if warnings_limits:
        print(f"  {Fore.RED}{Style.BRIGHT}[Genuine Extraction Uncertainties]{Style.RESET_ALL}")
        for wl in warnings_limits:
            print(f"  {Fore.RED}⚠ {wl}")
        print()
        
    # 9. Extracted Text Snippet
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Extracted Text Snippet]{Style.RESET_ALL}")
    print(format_text_snippet(result["extracted_text"]))
    print()


def print_hybrid_report(doc_graph: Any):
    """
    Prints a beautiful, highly detailed representation of the Hybrid Document Graph in the console.
    """
    print(format_banner(f"HYBRID DOCUMENT EXTRACTION REPORT", Fore.CYAN))
    print(format_metric("Filename", doc_graph.filename))
    print(format_metric("Document Type", doc_graph.document_type))
    print(format_metric("Total Pages", doc_graph.page_count))
    print()
    
    # 2. Metadata Section
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Document Metadata]{Style.RESET_ALL}")
    meta = doc_graph.metadata
    print(format_metric("Title", meta.get("title")))
    print(format_metric("Author", meta.get("author")))
    print(format_metric("Producer", meta.get("producer")))
    print(format_metric("Creation Date", meta.get("creation_date")))
    print(format_metric("Is Encrypted", meta.get("is_encrypted", False)))
    print()
    
    # Compile hybrid text length
    hybrid_text = ""
    for page in doc_graph.pages:
        blocks = page.statistics.get("blocks", [])
        for b in blocks:
            hybrid_text += b.text + "\n"
            
    # 3. Page by Page Graph Node summary
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Page-by-Page Detailed Structural Analysis]{Style.RESET_ALL}")
    for page in doc_graph.pages:
        print(f"  {Fore.LIGHTBLACK_EX}--------------------------------------------------------------------------------")
        print(f"  {Fore.MAGENTA}{Style.BRIGHT}PAGE {page.page_number} [{page.page_type.upper()}]{Style.RESET_ALL}")
        print(f"  {Fore.LIGHTBLACK_EX}--------------------------------------------------------------------------------")
        
        print(format_metric("Dimensions", f"{page.width:.1f} x {page.height:.1f} pt"))
        print(format_metric("Layout / Complexity", f"{page.reading_complexity} ({page.document_quality})"))
        print(format_metric("Overall Confidence", f"{page.confidence_score*100:.1f}%"))
        print(format_metric("Tables Count", len(page.tables)))
        print(format_metric("Images Count", len(page.images)))
        print(format_metric("Charts Count", len(page.charts)))
        print(format_metric("Hyperlinks Count", len(page.hyperlinks)))
        
        # Display Page Statistics
        stats = page.statistics
        print(f"    {Fore.LIGHTCYAN_EX}Page Processing Statistics:{Style.RESET_ALL}")
        print(f"      - Execution Time : {stats.get('processing_time', 0.0):.4f} seconds")
        print(f"      - Peak Memory    : {stats.get('memory_usage', 14.5):.1f} MB")
        
        # List Block Nodes
        blocks = stats.get("blocks", [])
        print(f"    {Fore.LIGHTCYAN_EX}Semantic Blocks Graph Node Sequence:{Style.RESET_ALL}")
        for idx_b, b in enumerate(blocks[:8]):
            bbox_fmt = ", ".join(f"{v:.1f}" for v in b.bbox)
            prov = b.provenance
            print(f"      [{idx_b+1}] {Fore.GREEN}{b.block_type.upper()}{Fore.RESET} (Conf: {b.confidence:.2f})")
            print(f"          BBox   : ({bbox_fmt})")
            
            # Print relationships if any exist
            rels = []
            if b.parent_id: rels.append(f"parent: {b.parent_id}")
            if b.next_id: rels.append(f"next: {b.next_id}")
            if b.caption_of: rels.append(f"caption_of: {b.caption_of}")
            if b.references: rels.append(f"references: {b.references}")
            if b.footnotes: rels.append(f"footnotes: {b.footnotes}")
            if rels:
                print(f"          Links  : {Fore.YELLOW}{', '.join(rels)}{Fore.RESET}")
                
            # If Equation, print LaTeX / MathML preview
            if b.block_type == "equation":
                print(f"          LaTeX  : {Fore.LIGHTWHITE_EX}$${b.latex}$${Fore.RESET}")
                print(f"          MathML : {Fore.LIGHTBLACK_EX}{b.mathml[:80]}...{Fore.RESET}")
            else:
                snippet = b.text[:75].replace('\n', ' ') + "..." if len(b.text) > 75 else b.text.replace('\n', ' ')
                print(f"          Text   : \"{snippet}\"")
                
        if len(blocks) > 8:
            print(f"      ... (+{len(blocks)-8} semantic blocks remaining in graph) ...")
            
        if stats.get("warnings"):
            print(f"    {Fore.RED}Page Validation Warnings:{Style.RESET_ALL}")
            for w in stats["warnings"]:
                print(f"      ⚠ {w}")
                
        print(f"  {Fore.LIGHTBLACK_EX}--------------------------------------------------------------------------------")
    print()
    
    # 4. Search Index Chunks & Knowledge Graph summary
    print(f"  {Fore.CYAN}{Style.BRIGHT}[RAG Chunk Builder Index & Knowledge Graph]{Style.RESET_ALL}")
    print(format_metric("Total Chars", len(hybrid_text)))
    print(format_metric("Total Chunks", len(doc_graph.chunks)))
    print(format_metric("KG Entities Count", len(doc_graph.knowledge_graph["entities"])))
    print(format_metric("KG Relations Count", len(doc_graph.knowledge_graph["relationships"])))
    print()
