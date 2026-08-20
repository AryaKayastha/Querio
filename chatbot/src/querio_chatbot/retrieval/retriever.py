from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

<<<<<<< Updated upstream
from querio_chatbot.config import VECTORSTORE_DIR
=======
from querio_chatbot.config import VECTORSTORE_DIR, collection_name
>>>>>>> Stashed changes
from querio_chatbot.llm.gemini_client import get_embeddings


@lru_cache
def _get_collection(domain_code: str) -> Chroma:
    return Chroma(
        collection_name=domain_code,
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )


def retrieve(domain_code: str, query: str, k: int = 4) -> list[Document]:
    """Semantic retrieval for a single domain's collection. Returns [] if the
    domain hasn't been ingested yet, rather than raising."""
    collection = _get_collection(domain_code)
    if collection._collection.count() == 0:
        return []
    return collection.similarity_search(query, k=k)
