import os
import gradio as gr
from dotenv import load_dotenv
from template import template_
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
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")  # Not used with DocArray

MODEL = "gpt-3.5-turbo"

# Initialize LangChain components
prompt = ChatPromptTemplate.from_template(template_)
model = ChatOpenAI(model=MODEL)
parser = StrOutputParser()
embeddings = OpenAIEmbeddings()

cached_chain = None


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
            "context": RunnableLambda(lambda inputs: vector_store.as_retriever().get_relevant_documents(inputs["question"])),
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


def chat_interface(pdf_file, user_message, history, vector_store):
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
    return gr.update(value=None), [], None, []


with gr.Blocks() as app:
    gr.Markdown("# PDF GPT Chat")
    pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"])
    chatbot = gr.Chatbot(label="Chat", type="messages")
    question = gr.Textbox(label="Ask a question", placeholder="Ask me anything about the PDF file")
    submit_btn = gr.Button("Send")
    reset_btn = gr.Button("Reset Session")

    history_state = gr.State(value=[])
    vector_store_state = gr.State(value=None)

    submit_btn.click(
        fn=chat_interface,
        inputs=[pdf_file, question, history_state, vector_store_state],
        outputs=[question, chatbot, vector_store_state],
    )

    reset_btn.click(
        fn=reset_session,
        inputs=[],
        outputs=[pdf_file, chatbot, vector_store_state, history_state],
    )

if __name__ == "__main__":
    app.queue()
    app.launch(server_name="0.0.0.0", server_port=5001)