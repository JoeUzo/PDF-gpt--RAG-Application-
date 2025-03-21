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

# Redis configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

DEFAULT_MODEL = "gpt-3.5-turbo"
current_model_name = DEFAULT_MODEL
model = None

# Initialize LangChain components
prompt = ChatPromptTemplate.from_template(chat_template)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()

cached_chain = None

def get_img(pdf_file):
    pdf_document = fitz.open(pdf_file.name)
    page = pdf_document.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def load_pdf_and_create_store(pdf_file):
    loader = PDFLoader(pdf_file.name)
    docs = loader.load()
    vector_store = DocArrayInMemorySearch.from_documents(
        docs,
        embedding=embeddings
    )
    return vector_store

def create_chain(vector_store):
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
    convo_history = "\n".join([f"{item['role']}: {item['content']}" for item in history])
    return cached_chain.invoke({
        "question": question,
        "conversation_history": convo_history
    })

########################
# Redis Session Storage
########################

def get_redis_session_data(session_id):
    """
    Retrieve session data from Redis. We'll store only the conversation history.
    """
    raw_data = redis_client.get(session_id)
    if raw_data:
        return json.loads(raw_data)
    # If not found, return default structure
    return {"history": []}

def set_redis_session_data(session_id, data):
    """
    Store session data as JSON in Redis, with an expiration.
    """
    redis_client.set(session_id, json.dumps(data), ex=7200)

def clear_redis_session(session_id):
    redis_client.delete(session_id)

###############################
# Gradio Logic
###############################

def chat_interface(model_choice, pdf_file, user_message, session_id):
    global model, current_model_name

    # Get session from Redis
    session_data = get_redis_session_data(session_id)
    history = session_data.get("history", [])

    # Decide if we need to initialize or re-create chain
    if model is None or model_choice != current_model_name:
        print("Initializing model:", model_choice)
        model_obj = ChatOpenAI(model=model_choice)
        # Update global references
        model = model_obj
        current_model_name = model_choice

    # Build or re-use vector store in memory (not in Redis)
    # We'll store it in a local variable only for this request
    local_vector_store = None

    # If we have no vector store in memory, let's create it if a PDF is provided
    if pdf_file is not None:
        local_vector_store = load_pdf_and_create_store(pdf_file)
        create_chain(local_vector_store)
    else:
        # If no PDF, we can't do retrieval. 
        # If your user already loaded a PDF in a previous request on the same pod, 
        # you might want to keep it in a global variable. 
        # For this example, assume new request means new store if user re-uploads.
        if cached_chain is None:
            return "Please upload a PDF first.", history, session_id

    # If user didn't provide a message
    if not user_message:
        return "Please enter a question.", history, session_id

    # If there's a local vector store or a cached_chain, do the chain_invoke
    answer = chain_invoke(user_message, history)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})

    # Save updated history back to Redis
    session_data["history"] = history
    # We never store the local_vector_store in Redis
    set_redis_session_data(session_id, session_data)

    return "", history, session_id

def reset_session(session_id):
    clear_redis_session(session_id)
    new_session_id = str(uuid.uuid4())
    # Return updated UI states
    return (
        gr.update(value=None),  # pdf_file
        [],                    # chatbot
        DEFAULT_MODEL,         # model_choice
        new_session_id,        # updated session
    )

with gr.Blocks(css=custom_css) as app:
    with gr.Column(elem_id="container"):
        gr.Markdown("# PDF GPT Chat")

        # We store session_id in Gradio state
        session_id_state = gr.State(str(uuid.uuid4()))

        model_choice = gr.Dropdown(
            choices=["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"],
            value=DEFAULT_MODEL,
            label="Select Model"
        )

        pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"], height=150)
        show_img = gr.Image(label='Preview PDF Page', height=250)
        chatbot = gr.Chatbot(label="Chat", type="messages")
        question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
        submit_btn = gr.Button("Send")
        reset_btn = gr.Button("Reset Session")

        # On PDF upload, show an image preview
        pdf_file.upload(
            fn=get_img,
            inputs=[pdf_file],
            outputs=[show_img]
        )

        submit_btn.click(
            fn=chat_interface,
            inputs=[model_choice, pdf_file, question, session_id_state],
            outputs=[question, chatbot, session_id_state]
        )

        reset_btn.click(
            fn=reset_session,
            inputs=[session_id_state],
            outputs=[pdf_file, chatbot, model_choice, session_id_state]
        )

if __name__ == "__main__":
    app.queue()
    app.launch(
        server_name="0.0.0.0",
        server_port=5000,
        share=False,
        show_error=True,
        root_path="/"
    )
