from typing import List

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader


class RawLoader(BaseLoader):
    """Load raw strings."""

    def __init__(self, text: str):
        """Initialize with text."""
        self.text = text

    def load(self) -> List[Document]:
        """Load from file path."""
        return [Document(page_content=self.text)]
