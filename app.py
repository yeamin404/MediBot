from flask import Flask, render_template, jsonify, request
##from langchain_openai import OpenAI
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
from src.helper import download_hugging_face_embeddings
from src.prompt import system_prompt


import os

app = Flask(__name__)

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
##OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

os.environ['PINECONE_API_KEY']  = PINECONE_API_KEY
##os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

embeddings = download_hugging_face_embeddings()
index_name = "medibot"

docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings,
)



retriever = docsearch.as_retriever(search_type = "similarity", search_kwargs = {"k":3})
##llm = OpenAI(temperature=0.4, max_tokens=100)
model: str ="qwen-2.5-32b"
#model: str ="deepseek-r1-distill-llama-70b"

deepmedibot = ChatGroq(api_key=GROQ_API_KEY, model_name= model)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)


question_answer_chain = create_stuff_documents_chain(deepmedibot, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)



@app.route("/")
def index():
    return render_template('chat.html')

"""@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    print(input)
    response = rag_chain.invoke({"input": msg})
    print("Response: ", response["answer"])
    return str(response["answer"])"""
@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form.get("msg", "").strip()
    response_format = request.form.get("format", "text").strip().lower()  # Default: text format

    if not msg:
        return "No input provided"

    print(f"User Input: {msg}")
    print(f"Requested Format: {response_format}")

    # Adjust the system prompt based on the requested format
    if response_format == "list":
        format_prompt = (
            "Provide the answer in a bullet-point list format. Example:\n"
            "- Point 1\n- Point 2\n- Point 3"
        )
    elif response_format == "table":
        format_prompt = (
            "Provide the answer in a structured table format using Markdown. Example:\n"
            "| Category | Description |\n"
            "|----------|------------|\n"
            "| Example 1 | Details 1 |\n"
            "| Example 2 | Details 2 |"
        )
    else:  # Default is plain text
        format_prompt = "Provide a concise, direct answer without explanations."

    # Create a dynamic prompt
    custom_prompt = system_prompt + "\n\n" + format_prompt

    prompt_template = ChatPromptTemplate.from_messages(
        [("system", custom_prompt), ("human", "{input}")]
    )

    response = rag_chain.invoke({"input": msg})
    answer = response.get("answer", "Error processing request")

    print(f"Response: {answer}")  # Debugging print

    return str(answer)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port= 8001, debug = True)