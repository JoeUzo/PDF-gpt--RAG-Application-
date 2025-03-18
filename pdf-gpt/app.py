import os
import gradio as gr
import fitz
from PIL import Image
from dotenv import load_dotenv
from template import *
from pdf import PDFLoader
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.vectorstores import DocArrayInMemorySearch

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_MODEL = "gpt-3.5-turbo"
current_model_name = DEFAULT_MODEL
model = None

# Initialize LangChain components
prompt = ChatPromptTemplate.from_template(chat_template)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()

cached_chain = None


def get_img(pdf_file):
    """
    Extract the first page of the PDF and convert it to an image.

    Parameters:
        pdf_file (gr.File): The uploaded PDF file.

    Returns:
        img (PIL.Image): The first page of the PDF as an image.
    """
    pdf_document = fitz.open(pdf_file.name)
    page = pdf_document.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def load_pdf_and_create_store(pdf_file):
    """
    Load the PDF file from the given file path, split its content into chunks,
    and create an in-memory vector store using DocArray.
    
    Parameters:
        pdf_file (gr.File): The uploaded PDF file from Gradio.
        
    Returns:
        vector_store (DocArrayInMemorySearch): In-memory vector store built from the document.
    """
    loader = PDFLoader(pdf_file.name)
    docs = loader.load()
    vector_store = DocArrayInMemorySearch.from_documents(
        docs,
        embedding=embeddings
    )
    return vector_store


def create_chain(vector_store):
    """
    Create a retrieval-augmented generation chain.

    Parameters:
        vector_store: In-memory vector store containing document chunks.
    """
    global cached_chain

    cached_chain = (
        {
            # Use a lambda to extract the question for retrieval
            "context": RunnableLambda(lambda inputs: vector_store.as_retriever().invoke(inputs["question"])),
            "question": RunnablePassthrough(),
            "conversation_history": RunnablePassthrough()
        }
        | prompt
        | model
        | parser
    )


def chain_invoke(question, history):
    """
    Run the retrieval-augmented generation chain to produce an answer.
    
    Parameters:
        question (str): The user's query.
        history (list): Previous chat history.
        
    Returns:
        answer (str): The generated answer.
    """

    convo_history = "\n".join([f"{item['role']}: {item['content']}" for item in history])

    return cached_chain.invoke({
    "question": question,
    "conversation_history": convo_history
    })


def chat_interface(model_choice, pdf_file, user_message, history, vector_store):
    """
    Main chat function:
    - If no vector store exists (i.e. a new PDF is uploaded), load the PDF and build a new vector store,
      then clear the chat history.
    - Otherwise, use the existing vector store.
    
    Parameters:
        pdf_file (gr.File): The uploaded PDF file.
        user_message (str): The user's question.
        history (list): Current chat history.
        vector_store: In-memory vector store (or None if not yet loaded).
        
    Returns:
        tuple: Updated question (cleared), chat history, and vector store.
    """
    global model, current_model_name

    if model is None or model_choice != current_model_name:
        model = ChatOpenAI(model=model_choice)
        current_model_name = model_choice

        if vector_store != None:
            create_chain(vector_store)
  
    if vector_store is None:
        if pdf_file is None:
            return "Please upload a PDF first.", history, vector_store
        vector_store = load_pdf_and_create_store(pdf_file)
        create_chain(vector_store)

    if not user_message:
        return "Please enter a question.", history, vector_store

    answer = chain_invoke(user_message, history)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})
    return "", history, vector_store


def reset_session():
    """
    Clear session state: PDF file, chat history, and vector store.
    
    Returns:
        tuple: Cleared file component, empty chat history, and None for vector store.
    """
    return gr.update(value=None), [], None, [], DEFAULT_MODEL, gr.update(value=None)


with gr.Blocks(
    css=custom_css,
    analytics_enabled=False,
    show_error=True,
    theme=gr.themes.Soft()
) as app:
    with gr.Column(elem_id="container"):
        gr.Markdown("# PDF GPT Chat")

        model_choice = gr.Dropdown(
            choices=["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"],
            value=DEFAULT_MODEL,
            label="Select Model"
        )

        pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"], height=150)
        show_img = gr.Image(label='Upload PDF', height=250)
        chatbot = gr.Chatbot(label="Chat", type="messages")
        question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
        submit_btn = gr.Button("Send")
        reset_btn = gr.Button("Reset Session")

        history_state = gr.State(value=[])
        vector_store_state = gr.State(value=None)

        pdf_file.upload(
            fn=get_img,
            inputs=[pdf_file],
            outputs=[show_img]
        )

        submit_btn.click(
            fn=chat_interface,
            inputs=[model_choice, pdf_file, question, history_state, vector_store_state],
            outputs=[question, chatbot, vector_store_state],
        )

        reset_btn.click(
            fn=reset_session,
            inputs=[],
            outputs=[pdf_file, chatbot, vector_store_state, history_state, model_choice, show_img],
        )

if __name__ == "__main__":
    app.queue(concurrency_count=8)  # Allow multiple concurrent requests
    app.launch(
        server_name="0.0.0.0",
        server_port=5000,
        share=False,
        root_path="/",
        ssl_verify=False,
        show_error=True,
        max_threads=40,
        file_directories=["/tmp"],
        quiet=True
    )