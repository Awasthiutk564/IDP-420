import abc
from utils.document_graph import DocumentNode
from typing import List, Dict, Any

class Stage(abc.ABC):
    """
    Abstract Base Class representing a single extraction/processing stage.
    """
    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        """
        Receives the DocumentNode graph, modifies/enhances it, and returns the updated graph.
        """
        pass
