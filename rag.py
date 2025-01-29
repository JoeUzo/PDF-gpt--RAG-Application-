import os 
from dotenv import load_dotenv
from pdf import PDFLoader
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
# from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_pinecone import PineconeVectorStore


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

MODEL = "gpt-3.5-turbo"

model = ChatOpenAI(model=MODEL)
parser = StrOutputParser()

template = '''
    You are an AI assistant. Use the context provided below to answer the user's question. 
    If the answer is not in the context, or the question cannot be answered based on the context alone, 
    reply with "I don't know."
    
    Context: {context}
    
    Question: {question}
'''

prompt = ChatPromptTemplate.from_template(template)

chain = prompt | model | parser
# print(chain.invoke("Hello, world!"))
print(chain.invoke({
    "context": "my name is John",
    "question": "What is the capital of France?"
}))