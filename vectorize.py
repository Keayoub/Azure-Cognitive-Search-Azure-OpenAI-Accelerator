import os
import urllib
import requests
import random
import json
from collections import OrderedDict
from IPython.display import display, HTML, Markdown
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import AzureOpenAI
from langchain.chat_models import AzureChatOpenAI
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.embeddings import OpenAIEmbeddings

from common.prompts import (
    COMBINE_QUESTION_PROMPT,
    COMBINE_PROMPT,
    COMBINE_PROMPT_TEMPLATE,
)
from common.utils import (
    get_search_results,
    model_tokens_limit,
    num_tokens_from_docs,
    num_tokens_from_string,
)

from dotenv import load_dotenv

load_dotenv("credentials.env")

# Set the ENV variables that Langchain needs to connect to Azure OpenAI
os.environ["OPENAI_API_BASE"] = os.environ["AZURE_OPENAI_ENDPOINT"]
os.environ["OPENAI_API_KEY"] = os.environ["AZURE_OPENAI_API_KEY"]
os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]
os.environ["OPENAI_API_TYPE"] = "azure"

# Setup the Payloads header
headers = {
    "Content-Type": "application/json",
    "api-key": os.environ["AZURE_SEARCH_KEY"],
}
params = {"api-version": os.environ["AZURE_SEARCH_API_VERSION"]}

index1_name = "cogsrch-index-sales-cs"
index2_name = "*"
indexes = [index1_name]
QUESTION = "*;$top=100;"

k = 100  # Number of results per each text_index
ordered_results = get_search_results(QUESTION, indexes, k=100, reranker_threshold=1)
print("Number of results:", len(ordered_results))

embedder = OpenAIEmbeddings(deployment="text-embedding-ada-002", chunk_size=1)

for key, value in ordered_results.items():
    if value["vectorized"] != True:  # If the document has not been vectorized yet
        print("Vectorizing", len(value["ServiceName"]))
        # Update document in text-based index and mark it as "vectorized"
        value_to_vectorise = f"{value['Description']} {value['InternalComments']}"
        upload_payload = {
            "value": [
                {
                    "id": key,
                    "Vector": embedder.embed_query(value_to_vectorise),
                    "vectorized": True,
                    "@search.action": "merge",
                },
            ]
        }

        r = requests.post(
            os.environ["AZURE_SEARCH_ENDPOINT"]
            + "/indexes/"
            + value["index"]
            + "/docs/index",
            data=json.dumps(upload_payload),
            headers=headers,
            params=params,
            timeout=10,  # Add a timeout argument to prevent hanging indefinitely
        )

        r = requests.post(
            os.environ["AZURE_SEARCH_ENDPOINT"]
            + "/indexes/"
            + value["index"]
            + "/docs/index",
            data=json.dumps(upload_payload),
            headers=headers,
            params=params,
            timeout=10,  # Add a timeout argument to prevent hanging indefinitely
        )
