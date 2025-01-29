import gradio as gr
import os
from dotenv import load_dotenv

from template import template_
from pdf import PDFLoader
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_pinecone import PineconeVectorStore

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

MODEL = "gpt-3.5-turbo"

template = template_

prompt = ChatPromptTemplate.from_template(template)
model = ChatOpenAI(model=MODEL)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()


def load_pdf_and_create_store(pdf_file, user_id):
    """Load PDF and create Pinecone store under a namespace = user_id."""
    loader = PDFLoader(pdf_file.name)
    docs = loader.load()
    pinecone_store = PineconeVectorStore.from_documents(
        docs, embedding=embeddings, index_name=INDEX_NAME, namespace=user_id
    )
    return pinecone_store


def chain_invoke(pinecone_store, question):
    """Invoke the chain with the user question."""
    chain = (
        {"context": pinecone_store.as_retriever(), "question": RunnablePassthrough()}
        | prompt
        | model
        | parser
    )
    return chain.invoke(question)


def chat_interface(pdf_file, user_id, user_message, history, pinecone_store):
    """
    Gradio chat callback.

    - pdf_file: Uploaded PDF object
    - user_id: ID for user (namespace in Pinecone)
    - user_message: The question typed by the user
    - history: Current chat history in OpenAI-style messages format
    - pinecone_store: The Pinecone vector store (None if not created yet)
    """
    # Create pinecone store if not yet created
    if pinecone_store is None:
        if pdf_file is None:
            return "Please upload a PDF first.", history, pinecone_store
        pinecone_store = load_pdf_and_create_store(pdf_file, user_id)

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


with gr.Blocks() as demo:
    gr.Markdown("# PDF GPT Chat")

    user_id = gr.Textbox(label="Username", placeholder="Enter username")
    pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"])

    # Specify `type="messages"` to avoid the deprecation warning
    chatbot = gr.Chatbot(label="Chat", type="messages")

    question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about on the PDF file")
    submit_btn = gr.Button("Send")
    reset_btn = gr.Button("Reset Session")

    # State to persist across interactions
    history_state = gr.State(value=[])
    pinecone_state = gr.State(value=None)

    # Main submit button: asks a question
    submit_btn.click(
        fn=chat_interface,
        inputs=[pdf_file, user_id, question, history_state, pinecone_state],
        outputs=[question, chatbot, pinecone_state],
    )

    # Reset session button
    reset_btn.click(
        fn=reset_session,
        inputs=[],
        outputs=[pdf_file, chatbot, pinecone_state],
    )

demo.launch()
