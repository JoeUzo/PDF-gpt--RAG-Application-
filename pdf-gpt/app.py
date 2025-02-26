import os
import tempfile
import shutil
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

def persist_pdf_file(pdf_path: str) -> str:
    """
    Copy the provided PDF file (given by its path) to a persistent temporary file.
    Returns the new persistent file path.
    """
    temp_dir = tempfile.gettempdir()
    new_path = os.path.join(temp_dir, os.path.basename(pdf_path))
    shutil.copy(pdf_path, new_path)
    return new_path

def load_pdf_and_create_store(pdf_file, username):
    """
    Persist the uploaded PDF, load and split the document,
    and create a new Pinecone vector store under the given username namespace.
    """
    # Persist the PDF file so that its path remains valid even if Gradio's ephemeral file is cleaned up.
    persistent_path = persist_pdf_file(pdf_file)
    #loader = PDFLoader(persistent_path)
    loader = PDFLoader(pdf_file)
    print("Current PDF file path (load):", pdf_file)
    docs = loader.load()
    # Clear any previous vectors for this username
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
    - If a new PDF file is uploaded (i.e. the file path is different from the stored one),
      load the new vector store and clear chat history.
    - Otherwise, use the existing vector store.
    """
    # If a PDF file is uploaded, and it's a new file compared to the previous upload:
    if pdf_file is not None:
        # pdf_file is a file path (string) from Gradio.
        if last_pdf_name is None or last_pdf_name != pdf_file:
            pinecone_store = load_pdf_and_create_store(pdf_file, username)
            history = [] 
            last_pdf_name = pdf_file 
    
    # Debug print: show current file path
    print("Current PDF file path:", pdf_file)
    print("Last PDF name in state:", last_pdf_name)

    if pinecone_store is None:
        return "Please upload a PDF first.", history, None, last_pdf_name

    if not user_message:
        return "Please enter a question.", history, pinecone_store, last_pdf_name

    answer = chain_invoke(pinecone_store, user_message)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})
    return "", history, pinecone_store, last_pdf_name

def reset_session():
    """
    Clear session state: PDF file, chat history, Pinecone store, and last PDF name.
    This ensures that after reset, any new PDF upload is processed fresh.
    """
    # Return updates: clear the file component, clear chat history, and reset stored states.
    return gr.update(value=None), [], None, None

def print_stuffs(pdf_file):
    print("Current PDF file path (print):", pdf_file)
    
with gr.Blocks() as app:
    gr.Markdown("# PDF GPT Chat")
    username = gr.Textbox(label="Username", placeholder="Enter username")
    pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"])
    chatbot = gr.Chatbot(label="Chat", type="messages")
    question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
    submit_btn = gr.Button("Send")
    reset_btn = gr.Button("Reset Session")

    # Gradio States to persist session data across interactions
    history_state = gr.State(value=[])
    pinecone_state = gr.State(value=None)
    last_pdf_name_state = gr.State(value=None)

    # When "Send" is clicked, process the chat query
    submit_btn.click(
        fn=chat_interface,
        inputs=[pdf_file, username, question, history_state, pinecone_state, last_pdf_name_state],
        outputs=[question, chatbot, pinecone_state, last_pdf_name_state],
    )

    submit_btn.click(
        fn=print_stuffs,
        inputs=[pdf_file],
        outputs=[],
    )

    print("Current PDF file path (submit):", pdf_file)

    # When "Reset Session" is clicked, clear all session state including the file input.
    reset_btn.click(
        fn=reset_session,
        inputs=[],
        outputs=[pdf_file, chatbot, pinecone_state, last_pdf_name_state],
    )
    print("Current PDF file path (reset):", pdf_file)

if __name__ == "__main__":
    app.queue()
    app.launch(server_name="0.0.0.0", server_port=5000)
