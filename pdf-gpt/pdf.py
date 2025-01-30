from langchain_community.document_loaders import PDFPlumberLoader
# from langchain_community.document_loaders import UnstructuredPDFLoader

# Load a PDF document   
# loader = UnstructuredPDFLoader(pdf_doc, strategy="fast")

# docs = loader.load()
# print(docs)
class PDFLoader:
    def __init__(self, pdf_doc: str):
        self.pdf_doc = pdf_doc
        self.loader = PDFPlumberLoader(pdf_doc)

    def load(self):
        return self.loader.load_and_split()

