from abc import ABC, abstractmethod

from app.models.document import Document


class Parser(ABC):

    @abstractmethod
    def parse(self, path: str) -> Document:
        """
        Convert an external file into a Document
        """
        pass