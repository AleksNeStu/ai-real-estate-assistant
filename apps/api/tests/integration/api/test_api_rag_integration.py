import builtins
import sys
import types

from fastapi.testclient import TestClient

from api.dependencies import get_knowledge_store, get_rag_qa_llm_details
from api.main import app
from config.settings import settings as app_settings
from utils.document_text_extractor import DocumentTextExtractionError
from vector_store.knowledge_store import KnowledgeStore

client = TestClient(app)


class _Msg:
    def __init__(self, content: str):
        self.content = content


class _Llm:
    """A model that answers, so the test does not depend on a live provider."""

    def invoke(self, _prompt: str):
        return _Msg("ok")


def test_rag_end_to_end_text_upload_and_qa(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store
    # The flow is what this test is about, so the model is a stub: a live
    # provider would make the test depend on a network call.
    app.dependency_overrides[get_rag_qa_llm_details] = lambda: (_Llm(), "openai", "m1")

    try:
        content = "Krakow is a city in Poland. It is known for Wawel Castle."
        files = {"files": ("guide.txt", content.encode("utf-8"), "text/plain")}
        r = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert r.status_code == 200
        assert r.json()["chunks_indexed"] > 0

        q = client.post(
            "/api/v1/rag/qa",
            json={"question": "What is Krakow known for?"},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert q.status_code == 200
        payload = q.json()
        assert isinstance(payload["answer"], str)
        assert len(payload["citations"]) >= 1
        assert isinstance(payload["llm_used"], bool)
    finally:
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_end_to_end_pdf_upload_citations_include_page_number(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    class _Page:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self):
            return self._text

    class _Reader:
        def __init__(self, _stream):
            self.pages = [_Page("alpha"), _Page("beta")]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=_Reader))
    app.dependency_overrides[get_rag_qa_llm_details] = lambda: (_Llm(), "openai", "m1")

    try:
        files = {"files": ("doc.pdf", b"%PDF-", "application/pdf")}
        r = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert r.status_code == 200
        assert r.json()["chunks_indexed"] > 0

        q = client.post(
            "/api/v1/rag/qa",
            json={"question": "beta", "top_k": 3},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert q.status_code == 200
        payload = q.json()
        assert isinstance(payload["answer"], str)
        assert payload["citations"] != []
        assert any(c.get("page_number") == 2 for c in payload["citations"])
    finally:
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_reset_clears_documents_and_qa_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        files = {"files": ("guide.txt", b"Some content to index", "text/plain")}
        r = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert r.status_code == 200
        assert r.json()["chunks_indexed"] > 0

        reset = client.post("/api/v1/rag/reset", headers={"X-API-Key": "dev-secret-key"})
        assert reset.status_code == 200
        payload = reset.json()
        assert payload["message"] == "Knowledge cleared"
        assert payload["documents_removed"] > 0
        assert payload["documents_remaining"] == 0

        q = client.post(
            "/api/v1/rag/qa",
            json={"question": "anything"},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert q.status_code == 200
        data = q.json()
        assert data["answer"] == ""
        assert data["citations"] == []
        assert data["llm_used"] is False
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_no_docs_returns_empty_answer(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        q = client.post(
            "/api/v1/rag/qa",
            json={"question": "anything"},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert q.status_code == 200
        payload = q.json()
        assert payload["answer"] == ""
        assert payload["citations"] == []
        assert payload["llm_used"] is False
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_llm_success_returns_llm_answer(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    app.dependency_overrides[get_rag_qa_llm_details] = lambda: (_Llm(), "openai", "m1")

    try:
        store.ingest_text("Some fact", source="facts.md")
        q = client.post(
            "/api/v1/rag/qa",
            json={"question": "fact"},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert q.status_code == 200
        payload = q.json()
        assert payload["answer"] == "ok"
        assert payload["llm_used"] is True
        assert payload["provider"] == "openai"
        assert payload["model"] == "m1"
    finally:
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_mixed_text_and_pdf_returns_partial_success(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        real_import = builtins.__import__

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "pypdf" or name.startswith("pypdf."):
                raise ImportError("no pypdf")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        files = [
            ("files", ("guide.txt", b"Hello from text", "text/plain")),
            ("files", ("doc.pdf", b"%PDF-", "application/pdf")),
        ]
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] > 0
        assert any("PDF parsing requires optional dependency" in e for e in data["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_pdf_only_returns_422_when_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        real_import = builtins.__import__

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "pypdf" or name.startswith("pypdf."):
                raise ImportError("no pypdf")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        files = {"files": ("doc.pdf", b"%PDF-", "application/pdf")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("PDF parsing requires optional dependency" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_docx_only_returns_422_when_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        real_import = builtins.__import__

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "docx" or name.startswith("docx."):
                raise ImportError("no docx")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        files = {
            "files": (
                "doc.docx",
                b"PK\x03\x04",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("DOCX parsing requires optional dependency" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_document_extraction_error_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        monkeypatch.setattr(
            "api.routers.rag.extract_text_segments_from_upload",
            lambda **_kwargs: (_ for _ in ()).throw(DocumentTextExtractionError("bad parse")),
        )
        files = {"files": ("guide.txt", b"Hello", "text/plain")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("bad parse" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_empty_text_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        monkeypatch.setattr(
            "api.routers.rag.extract_text_segments_from_upload", lambda **_kwargs: []
        )
        files = {"files": ("guide.txt", b"Hello", "text/plain")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("No extractable text found" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_ingest_exception_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    monkeypatch.setattr(
        store, "ingest_text_segments", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    app.dependency_overrides[get_knowledge_store] = lambda: store

    try:
        files = {"files": ("guide.txt", b"Hello", "text/plain")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("boom" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_total_payload_too_large_returns_413_and_no_ingest(monkeypatch, tmp_path):
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    store = KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")
    app.dependency_overrides[get_knowledge_store] = lambda: store
    monkeypatch.setattr(app_settings, "rag_max_files", 10)
    monkeypatch.setattr(app_settings, "rag_max_file_bytes", 100)
    monkeypatch.setattr(app_settings, "rag_max_total_bytes", 5)

    try:
        files = [
            ("files", ("a.md", b"123", "text/markdown")),
            ("files", ("b.md", b"456", "text/markdown")),
        ]
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 413
        assert getattr(store, "_docs", []) == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)
