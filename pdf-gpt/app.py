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

temporary_directory = tempfile.TemporaryDirectory()

MODEL = "gpt-3.5-turbo"

template = template_

prompt = ChatPromptTemplate.from_template(template)
model = ChatOpenAI(model=MODEL)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()

pc = Pinecone(api_key=PINECONE_API_KEY)
pinecone_index = pc.Index(INDEX_NAME)


def delete_namespace(username):
    """Delete a namespace from Pinecone."""
    # Get index statistics
    stats = pinecone_index.describe_index_stats()

    # Extract namespaces
    namespaces = stats.get("namespaces", {}).keys()

    # Delete namespace if it exists
    if username in namespaces: 
        pinecone_index.delete(deleteAll=True, namespace=username)


def load_pdf_and_create_store(pdf_file, username):
    """Load PDF and create Pinecone store under a namespace = username."""
    loader = PDFLoader(pdf_file.name)
    docs = loader.load()

    # Delete existing namespace if it exists
    delete_namespace(username)

    # Create Pinecone store
    pinecone_store = PineconeVectorStore.from_documents(
        docs, embedding=embeddings, index_name=INDEX_NAME, namespace=username
    )
    return pinecone_store

    # # Create a persistent file path in the system temp directory (or any other directory)
    # persistent_dir = tempfile.gettempdir()  # typically '/tmp'
    # persistent_pdf = os.path.join(persistent_dir, os.path.basename(pdf_file))
    
    # # Copy the Gradio temp file to our persistent location
    # shutil.copy(pdf_file, persistent_pdf)
    
    # # (Optional) Verify that the file now exists
    # if not os.path.exists(persistent_pdf):
    #     raise FileNotFoundError(f"Could not copy file to {persistent_pdf}")
    
    # # Now load the PDF using the persistent file path
    # loader = PDFLoader(persistent_pdf)
    # docs = loader.load()
    
    # # Remove the persistent copy if it's no longer needed
    # os.remove(persistent_pdf)
    
    # # Delete existing namespace if it exists
    # delete_namespace(username)
    
    # # Create and return the Pinecone store
    # pinecone_store = PineconeVectorStore.from_documents(
    #     docs, embedding=embeddings, index_name=INDEX_NAME, namespace=username
    # )
    # return pinecone_store


def chain_invoke(pinecone_store, question):
    """Invoke the chain with the user question."""
    chain = (
        {"context": pinecone_store.as_retriever(), "question": RunnablePassthrough()}
        | prompt
        | model
        | parser
    )
    return chain.invoke(question)


def chat_interface(pdf_file, username, user_message, history, pinecone_store):
    # Create pinecone store if not yet created
    if pinecone_store is None:
        if pdf_file is None:
            return "Please upload a PDF first.", history, pinecone_store
        pinecone_store = load_pdf_and_create_store(pdf_file, username)

    if not user_message:
        return "Please enter a question.", history, pinecone_store

    # Model inference
    answer = chain_invoke(pinecone_store, user_message)

    # Append user message to history
    history.append({"role": "user", "content": user_message})
    # Append assistant message to history
    history.append({"role": "assistant", "content": answer})

    # Return:
    # 1) Empty string to clear input box
    # 2) Updated chat history
    # 3) Updated Pinecone store
    return "", history, pinecone_store


def reset_session():
    """Clear the PDF file, chat history, and pinecone store."""
    return None, [], None


with gr.Blocks() as app:
    gr.Markdown("# PDF GPT Chat")

    username = gr.Textbox(label="Username", placeholder="Enter username")
    pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"])

    # Specify `type="messages"` to avoid the deprecation warning
    chatbot = gr.Chatbot(label="Chat", type="messages")

    question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
    submit_btn = gr.Button("Send")
    reset_btn = gr.Button("Reset Session")

    # State to persist across interactions
    history_state = gr.State(value=[])
    pinecone_state = gr.State(value=None)

    # Main submit button: asks a question
    submit_btn.click(
        fn=chat_interface,
        inputs=[pdf_file, username, question, history_state, pinecone_state],
        outputs=[question, chatbot, pinecone_state],
    )

    # Reset session button
    reset_btn.click(
        fn=reset_session,
        inputs=[],
        outputs=[pdf_file, chatbot, pinecone_state],
    )


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=5000)