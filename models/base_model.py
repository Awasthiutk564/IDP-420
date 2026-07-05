import abc

class BaseModel(abc.ABC):
    """
    Base model wrapper for machine learning models (OCR, YOLO Layout, Nougat, etc.).
    Allows modular replacements of models without pipeline redesigns.
    """
    def __init__(self, model_name: str, framework: str):
        self.model_name = model_name
        self.framework = framework

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        pass
