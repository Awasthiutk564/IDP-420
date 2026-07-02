import os
import glob
import sys
from colorama import Fore, Style
from PIL import Image

# Reconfigure stdout/stderr to use UTF-8 encoding on Windows to prevent Unicode encoding issues
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Import processors
from processors.pymupdf_processor import PyMuPDFProcessor
from processors.pdfminer_processor import PDFMinerProcessor
from processors.pdfplumber_processor import PDFPlumberProcessor
from processors.pypdf_processor import PyPDFProcessor

# Import utils
from utils.formatter import format_banner, print_result_report
from utils.comparer import print_comparison_matrix, print_recommendation_report

INPUT_DIR = os.path.join("data", "input")

def ensure_input_directory():
    """Ensures input directory exists, creating it if necessary."""
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)

def generate_sample_pdf(output_path: str):
    """
    Generates a sample PDF dynamically using PyMuPDF and Pillow.
    This creates an immediate learning resource containing text, metadata,
    an image, and a table structure, allowing the application to be tested
    straight out of the box.
    """
    import fitz  # Import fitz inside function so it's only imported when needed
    
    print(f"{Fore.YELLOW}No PDF found in '{INPUT_DIR}/'. Generating a sample PDF for learning...{Style.RESET_ALL}")
    
    # 1. Create a temporary image using Pillow
    temp_img_path = "temp_sample_image.png"
    img = Image.new('RGB', (200, 200), color=(73, 109, 137))
    img.save(temp_img_path)
    
    # 2. Build PDF using PyMuPDF
    doc = fitz.open()
    
    # Page 1: General Info & Table
    page1 = doc.new_page(width=612, height=792)  # Letter size
    
    # Add title and text
    page1.insert_text((50, 60), "Traditional Intelligent Document Processor (Learning Sample)", fontsize=16, color=(0.1, 0.3, 0.6))
    
    intro_text = (
        "This PDF was generated dynamically to serve as a test document for comparing PDF parser libraries.\n"
        "Traditional libraries parse digital PDFs by accessing the internal page object streams. Unlike OCR,\n"
        "they do not perform optical character recognition but extract embedded character data, metadata,\n"
        "vector graphics, and image streams directly from the PDF file format."
    )
    page1.insert_text((50, 100), intro_text, fontsize=10, color=(0.2, 0.2, 0.2))
    
    # Draw table bounding lines (traditional tables are made of line vectors, not tabular elements)
    # Outer box
    page1.draw_rect(fitz.Rect(50, 180, 550, 280), color=(0.3, 0.3, 0.3), width=1.5)
    # Horizontal headers divider line
    page1.draw_line(fitz.Point(50, 210), fitz.Point(550, 210), color=(0.3, 0.3, 0.3), width=1)
    # Horizontal content divider
    page1.draw_line(fitz.Point(50, 245), fitz.Point(550, 245), color=(0.5, 0.5, 0.5), width=0.5)
    # Vertical grid line
    page1.draw_line(fitz.Point(180, 180), fitz.Point(180, 280), color=(0.3, 0.3, 0.3), width=1)
    page1.draw_line(fitz.Point(380, 180), fitz.Point(380, 280), color=(0.3, 0.3, 0.3), width=1)
    
    # Write Table text content
    page1.insert_text((65, 200), "Library", fontsize=11, color=(0, 0, 0))
    page1.insert_text((195, 200), "Language backend", fontsize=11, color=(0, 0, 0))
    page1.insert_text((395, 200), "Primary Strength", fontsize=11, color=(0, 0, 0))
    
    # Row 1
    page1.insert_text((65, 230), "PyMuPDF", fontsize=10, color=(0, 0, 0))
    page1.insert_text((195, 230), "C / C++ (MuPDF wrapper)", fontsize=10, color=(0, 0, 0))
    page1.insert_text((395, 230), "Speed, image render, robust", fontsize=10, color=(0, 0, 0))
    
    # Row 2
    page1.insert_text((65, 265), "pdfplumber", fontsize=10, color=(0, 0, 0))
    page1.insert_text((195, 265), "Python (built on pdfminer)", fontsize=10, color=(0, 0, 0))
    page1.insert_text((395, 265), "Table parsing, layout bounding", fontsize=10, color=(0, 0, 0))
    
    # Page 2: Layout & Images
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((50, 60), "Visual and Graphics Content (Page 2)", fontsize=14, color=(0.1, 0.3, 0.6))
    
    desc_p2 = (
        "This second page demonstrates image embed support and font styling variances.\n"
        "Parsing tools scan the page resources to locate raster image streams (DCTDecode, FlateDecode)\n"
        "and list the fonts included in the document's global resources."
    )
    page2.insert_text((50, 90), desc_p2, fontsize=10, color=(0.2, 0.2, 0.2))
    
    # Insert the image we created using Pillow
    page2.insert_image(fitz.Rect(50, 160, 200, 310), filename=temp_img_path)
    page2.insert_text((220, 200), "<- This image is an embedded raster graphic.", fontsize=10, color=(0.4, 0.4, 0.4))
    
    # 3. Add Metadata
    doc.set_metadata({
        "title": "Traditional PDF Learning Guide",
        "author": "Antigravity AI",
        "subject": "PDF Extraction Comparison",
        "keywords": "PyMuPDF, pdfminer, pdfplumber, pypdf",
        "producer": "Traditional IDP Project Generator",
        "creationDate": "D:20260702223800"
    })
    
    # Save PDF
    doc.save(output_path)
    doc.close()
    
    # Clean up temp image
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)
        
    print(f"{Fore.GREEN}Successfully generated sample PDF at '{output_path}'.{Style.RESET_ALL}\n")

def validate_pdf_path(path: str) -> tuple[bool, str]:
    """
    Validates the provided file path to ensure it exists, is a valid PDF
    by checking extension and magic bytes, and can be opened without password protection.
    
    Args:
        path (str): File path to validate.
        
    Returns:
        tuple[bool, str]: (is_valid, cleaned_path_or_error_message)
    """
    path = path.strip()
    if not path:
        return False, "Path is empty."
        
    # Strip quotes if the user drags-and-drops the file into the console
    if path.startswith(('"', "'")) and path.endswith(('"', "'")):
        path = path[1:-1]
        
    if not os.path.exists(path):
        return False, f"File does not exist: {path}"
        
    if not os.path.isfile(path):
        return False, f"Path is a directory, not a file: {path}"
        
    if not path.lower().endswith(".pdf"):
        return False, f"File extension is not .pdf: {path}"
        
    # Check PDF magic bytes header (%PDF) to prevent running on fake/renamed files
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            if header != b"%PDF":
                return False, "File is not a valid PDF (invalid magic bytes header)."
    except Exception as e:
        return False, f"Cannot read file header: {e}"
        
    # Check if the PDF is password-protected or corrupted
    try:
        import pypdf
        reader = pypdf.PdfReader(path)
        if reader.is_encrypted:
            return False, "The PDF is password-protected/encrypted."
        # Access page count to trigger general parsing check
        _ = len(reader.pages)
    except Exception as e:
        return False, f"PDF appears corrupted or unopenable: {e}"
        
    return True, path

def select_and_validate_pdf() -> str:
    """
    Prompts the user for a PDF path, validates it, and returns the verified path.
    If the user presses Enter (blank input), it falls back to data/input/ sample PDF.
    """
    while True:
        try:
            user_path = input("Enter the path of the PDF (or press Enter to use default sample): ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.RED}Execution cancelled by user.{Style.RESET_ALL}")
            sys.exit(0)
            
        if not user_path:
            # Fallback mode
            ensure_input_directory()
            pdf_pattern = os.path.join(INPUT_DIR, "*.pdf")
            pdf_files = sorted(glob.glob(pdf_pattern))
            
            if not pdf_files:
                sample_path = os.path.join(INPUT_DIR, "learning_sample.pdf")
                if not os.path.exists(sample_path):
                    generate_sample_pdf(sample_path)
                selected_path = sample_path
            else:
                selected_path = pdf_files[0]
                
            print(f"{Fore.GREEN}Using fallback default PDF: {selected_path}{Style.RESET_ALL}")
            return selected_path
            
        # Run full validation check
        is_valid, result = validate_pdf_path(user_path)
        if is_valid:
            return result
        else:
            print(f"{Fore.RED}Error: {result}{Style.RESET_ALL}")
            print("Please enter a valid PDF path.\n")

def main():
    # Print welcome banner
    print(format_banner("TRADITIONAL INTELLIGENT DOCUMENT PROCESSOR", Fore.BLUE))
    
    # Retrieve the single validated PDF source path
    pdf_path = select_and_validate_pdf()
    pdf_name = os.path.basename(pdf_path)
    
    print(format_banner(f"PROCESSING SINGLE PDF SOURCE: {pdf_name.upper()}", Fore.CYAN))
    
    # Initialize processors
    processors = [
        PyMuPDFProcessor(),
        PDFMinerProcessor(),
        PDFPlumberProcessor(),
        PyPDFProcessor()
    ]
    
    # Process the single PDF with all four processors
    results = []
    for processor in processors:
        print(f"Running extraction using {Fore.YELLOW}{processor.library_name}{Style.RESET_ALL}...", end="", flush=True)
        res = processor.process(pdf_path)
        print(f" {Fore.GREEN}Done! ({res['processing_time']:.4f}s){Style.RESET_ALL}")
        results.append(res)
        
    # Print detailed report for each library
    print(format_banner(f"DETAILED EXTRACTION REPORTS", Fore.CYAN))
    for res in results:
        print_result_report(res)
        
    # Print comparison matrix and final recommendations
    print(format_banner(f"FINAL PERFORMANCE & CAPABILITY COMPARISON", Fore.CYAN))
    print_comparison_matrix(results)
    print_recommendation_report(results)
    print(format_banner(f"FINISHED PROCESSING: {pdf_name.upper()}", Fore.BLUE))

if __name__ == "__main__":
    main()
