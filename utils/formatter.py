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
    print(format_metric("Page Count", result["page_count"]))
    
    # Dimensions summary
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
    
    # 3. Extraction Metrics
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Extraction Metrics]{Style.RESET_ALL}")
    print(format_metric("Text Blocks Detected", result["block_count"]))
    print(format_metric("Words Extracted", result["word_count"]))
    print(format_metric("Images Detected", result["image_count"]))
    print(format_metric("Tables Detected", result["table_count"]))
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
    
    # 5. Warnings/Limitations
    if result["warnings"]:
        print(f"  {Fore.RED}{Style.BRIGHT}[Warnings & Limitations]{Style.RESET_ALL}")
        for w in result["warnings"]:
            print(f"  {Fore.RED}⚠ {w}")
        print()
        
    # 6. Extracted Text Snippet
    print(f"  {Fore.CYAN}{Style.BRIGHT}[Extracted Text Snippet]{Style.RESET_ALL}")
    print(format_text_snippet(result["extracted_text"]))
    print()
