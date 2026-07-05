from typing import List, Dict, Any, Tuple, Optional
import uuid

class CharacterNode:
    def __init__(self, char: str, bbox: Tuple[float, float, float, float], font_name: str, font_size: float, font_style: str, color: str, confidence: float, provenance: Dict[str, Any]):
        self.id = f"char_{uuid.uuid4().hex[:8]}"
        self.char = char
        self.bbox = bbox
        self.font_name = font_name
        self.font_size = font_size
        self.font_style = font_style
        self.color = color
        self.confidence = confidence
        self.provenance = provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "char": self.char,
            "bbox": self.bbox,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "font_style": self.font_style,
            "color": self.color,
            "confidence": round(self.confidence, 2),
            "provenance": self.provenance
        }

class WordNode:
    def __init__(self, text: str, bbox: Tuple[float, float, float, float], confidence: float, provenance: Dict[str, Any], characters: List[CharacterNode]):
        self.id = f"word_{uuid.uuid4().hex[:8]}"
        self.text = text
        self.bbox = bbox
        self.confidence = confidence
        self.provenance = provenance
        self.characters = characters

    @property
    def font_size(self) -> float:
        if self.characters:
            return self.characters[0].font_size
        return 10.0

    @property
    def font_style(self) -> str:
        if self.characters:
            return self.characters[0].font_style
        return "Regular"

    @property
    def font_name(self) -> str:
        if self.characters:
            return self.characters[0].font_name
        return "Unknown"

    @property
    def color(self) -> str:
        if self.characters:
            return self.characters[0].color
        return "#000000"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "bbox": self.bbox,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "font_style": self.font_style,
            "color": self.color,
            "confidence": round(self.confidence, 2),
            "provenance": self.provenance,
            "characters": [c.to_dict() for c in self.characters]
        }

class LineNode:
    def __init__(self, text: str, bbox: Tuple[float, float, float, float], confidence: float, provenance: Dict[str, Any], words: List[WordNode]):
        self.id = f"line_{uuid.uuid4().hex[:8]}"
        self.text = text
        self.bbox = bbox
        self.confidence = confidence
        self.provenance = provenance
        self.words = words

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 2),
            "provenance": self.provenance,
            "words": [w.to_dict() for w in self.words]
        }

class BlockNode:
    def __init__(self, block_type: str, text: str, bbox: Tuple[float, float, float, float], confidence: float, provenance: Dict[str, Any], lines: List[LineNode]):
        self.id = f"block_{uuid.uuid4().hex[:8]}"
        self.block_type = block_type  # title, heading_1, heading_2, heading_3, paragraph, list_item, table, chart, figure, equation, footnote, reference, page_number
        self.text = text
        self.bbox = bbox
        self.confidence = confidence
        self.provenance = provenance
        self.lines = lines
        
        # Extended semantic graph relationships
        self.parent_id: Optional[str] = None
        self.next_id: Optional[str] = None
        self.prev_id: Optional[str] = None
        self.caption_of: Optional[str] = None
        self.references: List[str] = []
        self.footnotes: List[str] = []
        self.contains_equations: List[str] = []
        
        # Math specific structures
        self.latex: Optional[str] = None
        self.mathml: Optional[str] = None
        self.symbol_tree: Optional[Dict[str, Any]] = None
        
        # Chart specific structures
        self.chart_structure: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "id": self.id,
            "block_type": self.block_type,
            "text": self.text,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 2),
            "provenance": self.provenance,
            "relationships": {
                "parent": self.parent_id,
                "next": self.next_id,
                "prev": self.prev_id,
                "caption_of": self.caption_of,
                "references": self.references,
                "footnotes": self.footnotes,
                "contains_equations": self.contains_equations
            },
            "lines": [l.to_dict() for l in self.lines]
        }
        if self.latex: res["latex"] = self.latex
        if self.mathml: res["mathml"] = self.mathml
        if self.symbol_tree: res["symbol_tree"] = self.symbol_tree
        if self.chart_structure: res["chart_structure"] = self.chart_structure
        return res

class SectionNode:
    def __init__(self, section_type: str, bbox: Tuple[float, float, float, float], blocks: List[BlockNode]):
        self.id = f"section_{uuid.uuid4().hex[:8]}"
        self.section_type = section_type  # header, footer, body, sidebar
        self.bbox = bbox
        self.blocks = blocks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "section_type": self.section_type,
            "bbox": self.bbox,
            "blocks": [b.to_dict() for b in self.blocks]
        }

class PageNode:
    def __init__(self, page_number: int, width: float, height: float, page_type: str = "Normal Page"):
        self.id = f"page_{uuid.uuid4().hex[:8]}"
        self.page_number = page_number
        self.width = width
        self.height = height
        self.page_type = page_type
        
        self.reading_complexity = "Single column"
        self.document_quality = "Digitally generated"
        self.ocr_recommended = False
        self.confidence_score = 1.0
        
        self.sections: List[SectionNode] = []
        self.tables: List[Dict[str, Any]] = []
        self.images: List[Dict[str, Any]] = []
        self.charts: List[Dict[str, Any]] = []
        self.hyperlinks: List[Dict[str, Any]] = []
        
        self.statistics = {
            "processing_time": 0.0,
            "memory_usage": 0.0,
            "extractor": "PyMuPDF+PDFMiner Hybrid",
            "warnings": [],
            "errors": [],
            "fallbacks": []
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "page_type": self.page_type,
            "reading_complexity": self.reading_complexity,
            "document_quality": self.document_quality,
            "ocr_recommended": self.ocr_recommended,
            "confidence_score": round(self.confidence_score, 2),
            "statistics": self.statistics,
            "sections": [s.to_dict() for s in self.sections],
            "tables": self.tables,
            "images": self.images,
            "charts": self.charts,
            "hyperlinks": self.hyperlinks
        }

class DocumentNode:
    def __init__(self, filename: str, metadata: Dict[str, Any]):
        self.id = f"doc_{uuid.uuid4().hex[:8]}"
        self.filename = filename
        self.metadata = metadata
        self.document_type = "Normal Document"
        self.page_count = 0
        self.pages: List[PageNode] = []
        self.chunks: List[Dict[str, Any]] = []
        self.knowledge_graph = {
            "entities": [],
            "relationships": []
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "document_type": self.document_type,
            "metadata": self.metadata,
            "page_count": self.page_count,
            "pages": [p.to_dict() for p in self.pages],
            "chunks": self.chunks,
            "knowledge_graph": self.knowledge_graph
        }
