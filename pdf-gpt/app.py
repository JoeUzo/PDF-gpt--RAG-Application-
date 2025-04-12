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
import redis
import json
import uuid

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure Redis connection
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

# Default model settings
DEFAULT_MODEL = "gpt-3.5-turbo"
current_model_name = DEFAULT_MODEL
model = None

# Initialize base LangChain components
prompt = ChatPromptTemplate.from_template(chat_template)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()

# Global chain reference
cached_chain = None

def get_img(pdf_file):
    """
    Extract the first page of an uploaded PDF and convert it to a preview image.
    """
    pdf_document = fitz.open(pdf_file.name)
    page = pdf_document.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def load_pdf_and_create_store(pdf_file):
    """
    Given an uploaded PDF, load its text and create an in-memory vector store
    for retrieval-augmented generation.
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
    Construct a retrieval-augmented generation chain using a vector store
    and the globally assigned ChatOpenAI model.
    """
    global cached_chain
    cached_chain = (
        {
            # Retrieve relevant chunks from the vector store
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
    Invoke the chain to generate a response based on the user's question
    and conversation history.
    """
    convo_history = "\n".join([f"{item['role']}: {item['content']}" for item in history])
    return cached_chain.invoke({"question": question, "conversation_history": convo_history})

def get_redis_session_data(session_id):
    """
    Retrieve the user's chat session data from Redis. If no data exists,
    return a default structure containing only the 'history' key.
    """
    raw_data = redis_client.get(session_id)
    if raw_data:
        return json.loads(raw_data)
    return {"history": []}

def set_redis_session_data(session_id, data):
    """
    Persist the user's chat session data to Redis with an expiration time.
    """
    redis_client.set(session_id, json.dumps(data), ex=7200)

def clear_redis_session(session_id):
    """
    Remove all data associated with a user's session in Redis.
    """
    redis_client.delete(session_id)

def chat_interface(model_choice, pdf_file, user_message, session_id):
    """
    Main logic for handling user requests:
      1. Load existing session data from Redis (history).
      2. Initialize or update the model if the user's selected model differs.
      3. Create a vector store from the uploaded PDF if necessary.
      4. Generate a response using the chain and update chat history in Redis.
    """
    global model, current_model_name

    # Retrieve session data (primarily 'history')
    session_data = get_redis_session_data(session_id)
    history = session_data.get("history", [])

    # If the chosen model differs from the current one, re-initialize
    if model is None or model_choice != current_model_name:
        model = ChatOpenAI(model=model_choice)
        current_model_name = model_choice

    # Build or reuse a chain for retrieval if a PDF is provided
    if pdf_file is not None:
        local_vector_store = load_pdf_and_create_store(pdf_file)
        create_chain(local_vector_store)
    else:
        # If no PDF is uploaded and there's no existing chain, prompt the user
        if cached_chain is None:
            return "Please upload a PDF first.", history, session_id

    # If no user input is provided, prompt for a question
    if not user_message:
        return "Please enter a question.", history, session_id

    # Generate an answer based on the current chain and conversation history
    answer = chain_invoke(user_message, history)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})

    # Update and save the session's chat history
    session_data["history"] = history
    set_redis_session_data(session_id, session_data)

    return "", history, session_id

def reset_session(session_id):
    """
    Clear the current session's data from Redis and generate a new session ID.
    Also resets Gradio UI components for the user.
    """
    clear_redis_session(session_id)
    new_session_id = str(uuid.uuid4())
    return (gr.update(value=None), [], DEFAULT_MODEL, new_session_id)

with gr.Blocks(css=custom_css) as app:
    with gr.Column(elem_id="container"):
        gr.Markdown("# PDF GPT Chat")

        # Maintain a unique session ID in Gradio state to track user history in Redis
        session_id_state = gr.State(str(uuid.uuid4()))

        model_choice = gr.Dropdown(
            choices=["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"],
            value=DEFAULT_MODEL,
            label="Select Model"
        )

        pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"], height=150)
        show_img = gr.Image(label="Preview PDF Page", height=250)
        chatbot = gr.Chatbot(label="Chat", type="messages")
        question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
        submit_btn = gr.Button("Send")
        reset_btn = gr.Button("Reset Session")

        # Generate a preview of the first page when a PDF is uploaded
        pdf_file.upload(
            fn=get_img,
            inputs=[pdf_file],
            outputs=[show_img]
        )

        # Handle user input and produce a response
        submit_btn.click(
            fn=chat_interface,
            inputs=[model_choice, pdf_file, question, session_id_state],
            outputs=[question, chatbot, session_id_state]
        )

        # Reset the session, clearing Redis data and refreshing the UI
        reset_btn.click(
            fn=reset_session,
            inputs=[session_id_state],
            outputs=[pdf_file, chatbot, model_choice, session_id_state]
        )

if __name__ == "__main__":
    # Launch the Gradio app with a queue for handling requests asynchronously
    app.queue()
    app.launch(
        server_name="0.0.0.0",
        server_port=5000,
        share=False,
        show_error=True,
    )
