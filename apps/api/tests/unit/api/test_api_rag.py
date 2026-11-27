from fastapi.testclient import TestClient

from api.dependencies import get_knowledge_store, get_rag_qa_llm_details
from api.main import app
from config.settings import settings as app_settings
from utils.document_text_extractor import (
    DocumentTextExtractionError,
    OptionalDependencyMissingError,
)
from vector_store.knowledge_store import KnowledgeStore

client = TestClient(app)


def _make_store(monkeypatch, tmp_path) -> KnowledgeStore:
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    return KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")


def _override_store(store):
    app.dependency_overrides[get_knowledge_store] = lambda: store


def test_rag_upload_text_success(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        files = {"files": ("note.md", b"# Title\n\nHello world", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] > 0
        assert data["errors"] == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_unsupported_type(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        monkeypatch.setattr(
            "utils.document_text_extractor._extract_pdf_text_segments",
            lambda _data: (_ for _ in ()).throw(
                OptionalDependencyMissingError(
                    "PDF parsing requires optional dependency 'pypdf'. Install with: pip install pypdf",
                    dependency="pypdf",
                )
            ),
        )
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


def test_rag_upload_mixed_text_and_pdf_returns_partial_success(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        monkeypatch.setattr(
            "utils.document_text_extractor._extract_pdf_text_segments",
            lambda _data: (_ for _ in ()).throw(
                OptionalDependencyMissingError(
                    "PDF parsing requires optional dependency 'pypdf'. Install with: pip install pypdf",
                    dependency="pypdf",
                )
            ),
        )
        files = [
            ("files", ("note.md", b"# Title\n\nHello world", "text/markdown")),
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


def test_rag_upload_empty_extracted_text_returns_422(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        monkeypatch.setattr(
            "api.routers.rag.extract_text_segments_from_upload", lambda **_kwargs: []
        )
        files = {"files": ("note.md", b"# Title\n\nHello world", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("No extractable text found" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_document_extraction_error_is_reported(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        monkeypatch.setattr(
            "api.routers.rag.extract_text_segments_from_upload",
            lambda **_kwargs: (_ for _ in ()).throw(DocumentTextExtractionError("bad parse")),
        )
        files = {"files": ("note.md", b"Hello", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("bad parse" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_unexpected_extraction_error_is_reported(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        monkeypatch.setattr(
            "api.routers.rag.extract_text_segments_from_upload",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("unexpected")),
        )
        files = {"files": ("note.md", b"Hello", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("unexpected" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_no_files(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        resp = client.post("/api/v1/rag/upload", headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 422  # FastAPI validates form-data presence
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_store_unavailable(monkeypatch):
    _override_store(None)
    try:
        files = {"files": ("note.md", b"Hello", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Knowledge store is not available"
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_file_too_large_returns_422(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    monkeypatch.setattr(app_settings, "rag_max_files", 10)
    monkeypatch.setattr(app_settings, "rag_max_file_bytes", 5)
    monkeypatch.setattr(app_settings, "rag_max_total_bytes", 100)

    try:
        files = {"files": ("note.md", b"123456", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("File too large" in e for e in detail["errors"])
        assert getattr(store, "_docs", []) == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_mixed_small_and_oversize_returns_partial_success(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    monkeypatch.setattr(app_settings, "rag_max_files", 10)
    monkeypatch.setattr(app_settings, "rag_max_file_bytes", 5)
    monkeypatch.setattr(app_settings, "rag_max_total_bytes", 100)

    try:
        files = [
            ("files", ("small.md", b"1234", "text/markdown")),
            ("files", ("big.md", b"123456", "text/markdown")),
        ]
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] > 0
        assert any("File too large" in e for e in data["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_total_payload_too_large_returns_413(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
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
        detail = resp.json()["detail"]
        assert detail["message"] == "Upload payload too large"
        assert detail["max_total_bytes"] == 5
        assert detail["total_bytes"] == 6
        assert getattr(store, "_docs", []) == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_too_many_files_returns_400(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    monkeypatch.setattr(app_settings, "rag_max_files", 1)
    monkeypatch.setattr(app_settings, "rag_max_file_bytes", 100)
    monkeypatch.setattr(app_settings, "rag_max_total_bytes", 100)

    try:
        files = [
            ("files", ("a.md", b"123", "text/markdown")),
            ("files", ("b.md", b"456", "text/markdown")),
        ]
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 400
        assert "Too many files" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_returns_citations(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    class _Msg:
        def __init__(self, content: str):
            self.content = content

    class _Llm:
        def invoke(self, _prompt: str):
            return _Msg("Warsaw.")

    # The citation shape is what this test is about, so the model is a stub:
    # a live provider would make the test depend on a network call.
    app.dependency_overrides[get_rag_qa_llm_details] = lambda: (_Llm(), "openai", "m1")

    try:
        store.ingest_text("The capital of Poland is Warsaw.", source="facts.md")

        resp = client.post(
            "/api/v1/rag/qa",
            json={"question": "capital Poland", "top_k": 3},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["answer"], str)
        assert data["citations"] != []
        assert isinstance(data["llm_used"], bool)
    finally:
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_no_docs(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        resp = client.post(
            "/api/v1/rag/qa",
            json={"question": "unknown", "top_k": 2},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == ""
        assert data["citations"] == []
        assert data["llm_used"] is False
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_llm_unavailable(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        app.dependency_overrides[get_rag_qa_llm_details] = lambda: (None, None, None)
        store.ingest_text("The answer is here", source="s.md")
        resp = client.post(
            "/api/v1/rag/qa",
            json={"question": "answer", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["answer"], str)
        assert data["citations"] != []
        assert data["llm_used"] is False
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)


def test_rag_qa_llm_failure_answers_503(monkeypatch, tmp_path):
    """A model that failed is not an answer - the request fails with 503.

    The retrieved text is the MATERIAL the answer would have been built
    from; handing it back as the answer with a 200 tells the reader the
    model answered when it did not.
    """
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    class _Llm:
        def invoke(self, _prompt: str):
            raise RuntimeError("llm down")

    try:
        app.dependency_overrides[get_rag_qa_llm_details] = lambda: (_Llm(), "openai", "m1")
        store.ingest_text("The answer is here", source="s.md")
        resp = client.post(
            "/api/v1/rag/qa",
            json={"question": "answer", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 503
        assert "temporarily unavailable" in resp.json()["detail"]
        # The provider's own error text is the server's business.
        assert "llm down" not in resp.text
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)


def test_rag_upload_ingest_exception_is_reported(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    monkeypatch.setattr(
        store, "ingest_text_segments", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    try:
        files = {"files": ("note.md", b"Hello", "text/markdown")}
        resp = client.post(
            "/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"}
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["message"] == "No documents were indexed"
        assert any("boom" in e for e in detail["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_store_unavailable_returns_503(monkeypatch):
    _override_store(None)
    try:
        resp = client.post(
            "/api/v1/rag/qa",
            json={"question": "hi", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Knowledge store is not available"
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_reset_clears_all_documents(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        store.ingest_text("Alpha", source="a.txt")
        store.ingest_text("Beta", source="b.txt")

        resp = client.post("/api/v1/rag/reset", headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Knowledge cleared"
        assert data["documents_removed"] > 0
        assert data["documents_remaining"] == 0
        assert getattr(store, "_docs", []) == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_reset_store_unavailable_returns_503(monkeypatch):
    _override_store(None)
    try:
        resp = client.post("/api/v1/rag/reset", headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Knowledge store is not available"
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_lazy_llm_success(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    class _Msg:
        def __init__(self, content: str):
            self.content = content

    class _Llm:
        def invoke(self, prompt: str):
            assert "context" in prompt.lower()
            return _Msg("ok")

    try:
        app.dependency_overrides[get_rag_qa_llm_details] = lambda: (_Llm(), "openai", "m1")
        store.ingest_text("The capital of Poland is Warsaw.", source="facts.md")
        resp = client.post(
            "/api/v1/rag/qa",
            json={"question": "capital poland", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "ok"
        assert data["citations"] != []
        assert data["llm_used"] is True
        assert data["provider"] == "openai"
        assert data["model"] == "m1"
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)
        app.dependency_overrides.pop(get_rag_qa_llm_details, None)


def test_rag_qa_empty_question(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "   "},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)
