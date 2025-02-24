from langchain_community.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class PDFLoader:
    def __init__(self, pdf_doc: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.pdf_doc = pdf_doc
        self.loader = PDFPlumberLoader(pdf_doc)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load(self):
        docs = self.loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        return splitter.split_documents(docs)

