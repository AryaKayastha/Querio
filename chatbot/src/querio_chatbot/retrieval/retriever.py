from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from querio_chatbot.config import VECTORSTORE_DIR, collection_name
from querio_chatbot.llm.gemini_client import get_embeddings


@lru_cache
def _get_collection(domain_code: str) -> Chroma:
    return Chroma(
        collection_name=collection_name(domain_code),
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )


def retrieve(domain_code: str, query: str, k: int = 4) -> list[Document]:
    """Retrieve documents for one domain, returning no results for an empty collection."""
    collection = _get_collection(domain_code)
    if collection._collection.count() == 0:
        return []
    return collection.similarity_search(query, k=k)
