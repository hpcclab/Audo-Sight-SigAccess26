# Core LangChain components
from langchain_core.documents import Document

# Integrations for LOCAL embeddings and vector stores
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


import json
import csv
import time
from pathlib import Path
import configHandler

# Path to the JSON files
CONFIG_PATH = "config.txt"

config = configHandler.load_config(CONFIG_PATH)

train  = ""
out = ""
while train == "":
    choice = input("moe or urgent? (enter M or U)")
    if choice.upper() == "U":
        train = "Urgency_train_path"
        out = "Urgency_embed_path"
    elif choice.upper() == "M":
        train = "MoE_train_path"
        out = "MoE_embed_path"
    else:
        print("invalid")

INPUT_PATH = config.get(train)
# TEST_PATH = config.get("test_path")
persist_directory = config.get(out)
# RESULT_OUTPUT = "results.json"
# output_csv_file = config.get("results_path")

SCRIPT_DIR = Path(__file__).resolve().parent
path = SCRIPT_DIR / INPUT_PATH
persist_directory = SCRIPT_DIR / persist_directory
with open(path, "r", encoding="utf-8") as f:
    ExampleLoaded = json.load(f)

examples = []
for category, questions in ExampleLoaded.items():
    chain_name = category.lower()  # normalize category to lowercase (optional)
    for q in questions:
        examples.append({
            "question": q,
            "chain_name": chain_name
        })

print("Converting the dictionary examples into LangChain Document objects")
start_doc = time.time()

# Convert the dictionary examples into LangChain Document objects
documents = [
    Document(page_content=ex["question"], metadata={"chain_name": ex["chain_name"]})
    for ex in examples
]
t = time.time() - start_doc

print(f"finished Converting the dictionary examples into LangChain Document objects - {t}")

print("Load local model")
start_ex = time.time()
# Specify the model name from Hugging Face
model_name = "sentence-transformers/all-MiniLM-L6-v2"
# Use model_kwargs to specify device='cpu' if you want to ensure it runs on CPU
model_kwargs = {'device': 'cpu'}
# Instantiate the local embeddings model
embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs
)
t = time.time() - start_ex
print(f"finished Loading local model - {t}")

vectorstore = Chroma.from_documents(documents, embedding=embeddings, persist_directory=str(persist_directory))
retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

print("creating topic detection chain")
start_tdc = time.time()
# --- 4. Create the Topic Detection Chain ---
# This chain remains unchanged as it works with any LangChain retriever.
topic_detection_chain = (
    retriever | (lambda docs: {
        "chain_name": docs[0].metadata["chain_name"],
        # "confidence": docs[0].metadata["score"]  # <-- Add this line
    })
)
t = time.time() - start_tdc
print(f"created topic detection chain - {t}")

print(f"Embeddings have been created and saved locally in the {persist_directory} folder.")


# # Your existing retriever setup
# retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

# # Temporarily invoke just the retriever to inspect its output
# retrieved_docs = retriever.invoke("Who all is in the room?")

# # 2. Print the metadata of the first document
# print(retrieved_docs[0].metadata)

##################
