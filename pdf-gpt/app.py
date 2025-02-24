import os
import threading
import gradio as gr
from dotenv import load_dotenv
from template import template_
from pdf import PDFLoader
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

MODEL = "gpt-3.5-turbo"

# Initialize components
prompt = ChatPromptTemplate.from_template(template_)
model = ChatOpenAI(model=MODEL)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()

# Initialize Pinecone client and index handle
pc = Pinecone(api_key=PINECONE_API_KEY)
pinecone_index = pc.Index(INDEX_NAME)

def delete_namespace(username):
    """Delete an entire namespace from Pinecone if needed."""
    stats = pinecone_index.describe_index_stats()
    namespaces = stats.get("namespaces", {}).keys()
    if username in namespaces:
        pinecone_index.delete(deleteAll=True, namespace=username)

def load_pdf_and_create_store(pdf_file, username):
    """
    Load the PDF, extract its text, and create a new Pinecone vector store under the given username namespace.
    """
    loader = PDFLoader(pdf_file.name)
    docs = loader.load()
    delete_namespace(username)
    pinecone_store = PineconeVectorStore.from_documents(
        docs,
        embedding=embeddings,
        index_name=INDEX_NAME,
        namespace=username
    )
    return pinecone_store

def chain_invoke(pinecone_store, question):
    """Run the retrieval-augmented generation chain using the given vector store and user question."""
    chain = (
        {"context": pinecone_store.as_retriever(), "question": RunnablePassthrough()}
        | prompt
        | model
        | parser
    )
    return chain.invoke(question)

def chat_interface(pdf_file, username, user_message, history, pinecone_store, last_pdf_name):
    """
    Main chat function:
    - If a new PDF file is uploaded (different file name), load the new vector store and clear chat history.
    - Otherwise, use the existing vector store.
    """
    if pdf_file is not None:
        if last_pdf_name is None or last_pdf_name != pdf_file.name:
            pinecone_store = load_pdf_and_create_store(pdf_file, username)
            history = []  # Clear the chat history for new context
            last_pdf_name = pdf_file.name

    if pinecone_store is None:
        return "Please upload a PDF first.", history, None, last_pdf_name

    if not user_message:
        return "Please enter a question.", history, pinecone_store, last_pdf_name

    answer = chain_invoke(pinecone_store, user_message)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})

    return "", history, pinecone_store, last_pdf_name

def reset_session():
    """Clear session state: PDF file, chat history, Pinecone store, and last PDF name."""
    return None, [], None, None

with gr.Blocks() as app:
    gr.Markdown("# PDF GPT Chat")

    username = gr.Textbox(label="Username", placeholder="Enter username")
    pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"])
    chatbot = gr.Chatbot(label="Chat", type="messages")
    question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
    submit_btn = gr.Button("Send")
    reset_btn = gr.Button("Reset Session")

    history_state = gr.State(value=[])
    pinecone_state = gr.State(value=None)
    last_pdf_name_state = gr.State(value=None)

    submit_btn.click(
        fn=chat_interface,
        inputs=[pdf_file, username, question, history_state, pinecone_state, last_pdf_name_state],
        outputs=[question, chatbot, pinecone_state, last_pdf_name_state],
    )

    reset_btn.click(
        fn=reset_session,
        inputs=[],
        outputs=[pdf_file, chatbot, pinecone_state, last_pdf_name_state],
    )

if __name__ == "__main__":
    app.queue()
    app.launch(server_name="0.0.0.0", server_port=5000)
