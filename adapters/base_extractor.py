import abc
from typing import Dict, Any, List

class BaseExtractor(abc.ABC):
    """
    Abstract Base Class for PDF library adapters.
    Each adapter must wrap a specific library and extract raw data.
    """
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    @abc.abstractmethod
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def extract_pages_raw(self, pdf_path: str) -> List[Dict[str, Any]]:
        pass
