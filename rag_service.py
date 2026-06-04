import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models


logger = logging.getLogger("todo_api.rag")

RAG_ROOT = Path(os.getenv("RAG_STORAGE_DIR", "rag_storage"))
UPLOAD_DIR = RAG_ROOT / "uploads"
QDRANT_PATH = os.getenv("QDRANT_PATH", str(RAG_ROOT / "qdrant"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "pdf_documents")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")


def _ensure_storage_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# API key function:
def _get_google_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set")
    return api_key

# Embeddings function:
def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=_get_google_api_key()
    )

# LLM function:
def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=CHAT_MODEL,
        google_api_key=_get_google_api_key(),
        temperature=0
    )
def _get_qdrant_client() -> QdrantClient:
    return QdrantClient(path=QDRANT_PATH)


def _ensure_collection(client: QdrantClient, vector_size: int) -> None:
    if client.collection_exists(COLLECTION_NAME):
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qdrant_models.VectorParams(
            size=vector_size,
            distance=qdrant_models.Distance.COSINE,
        ),
    )


def _extract_text_from_pdf(pdf_path: Path) -> list:
    loader = PyPDFLoader(str(pdf_path))
    return loader.load()


def index_pdf_document(file: UploadFile) -> dict:
    _ensure_storage_dirs()
    _get_google_api_key()

    document_id = str(uuid.uuid4())
    suffix = Path(file.filename or "document.pdf").suffix or ".pdf"
    pdf_path = UPLOAD_DIR / f"{document_id}{suffix}"

    try:
        with pdf_path.open("wb") as output_file:
            output_file.write(file.file.read())

        documents = _extract_text_from_pdf(pdf_path)
        if not documents:
            raise ValueError("No text could be extracted from the uploaded PDF")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        chunks = splitter.split_documents(documents)
        if not chunks:
            raise ValueError("The uploaded PDF did not produce any searchable chunks")

        embeddings = _get_embeddings()
        chunk_texts = [chunk.page_content for chunk in chunks]
        vectors = embeddings.embed_documents(chunk_texts)

        client = _get_qdrant_client()
        _ensure_collection(client, len(vectors[0]))

        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                qdrant_models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "chunk_index": index,
                        "page_number": chunk.metadata.get("page"),
                        "source": file.filename or "document.pdf",
                        "text": chunk.page_content,
                    },
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        logger.info(
            "Indexed PDF %s into Qdrant with %d chunks",
            file.filename,
            len(points),
        )

        return {
            "document_id": document_id,
            "filename": file.filename or "document.pdf",
            "chunks_indexed": len(points),
            "message": "PDF indexed successfully",
        }
    finally:
        file.file.close()


def ask_question_about_pdf(document_id: str, question: str) -> dict:
    _get_google_api_key()
    client = _get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        raise ValueError("No PDFs have been indexed yet")

    query_vector = _get_embeddings().embed_query(question)
    search_results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=4,
        query_filter=qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="document_id",
                    match=qdrant_models.MatchValue(value=document_id),
                )
            ]
        ),
    )

    if not search_results:
        raise ValueError("No indexed chunks were found for that document_id")

    context_blocks = []
    sources = []
    for result in search_results:
        payload = result.payload or {}
        text = payload.get("text", "")
        context_blocks.append(text)
        sources.append(
            {
                "chunk_index": int(payload.get("chunk_index", 0)),
                "page_number": payload.get("page_number"),
                "score": float(result.score or 0.0),
                "text": text,
            }
        )

    system_prompt = (
        "You answer questions using only the provided PDF context. "
        "If the answer is not in the context, say you could not find it in the PDF. "
        "Keep the answer concise but complete."
    )
    user_prompt = (
        f"Question: {question}\n\n"
        f"PDF context:\n{chr(10).join(context_blocks)}"
    )

    response = _get_llm().invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    return {
        "document_id": document_id,
        "question": question,
        "answer": response.content.strip(),
        "sources": sources,
    }
