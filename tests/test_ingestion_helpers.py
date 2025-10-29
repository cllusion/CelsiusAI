from pathlib import Path
from src.hub import ingestion


def test_approve_and_reject(tmp_path):
    project_root = tmp_path

    # prepare candidates
    candidates = [
        {"source": "http://example.com/a", "title": "A", "added_at": "t1"},
        {"source": "http://example.com/b", "title": "B", "added_at": "t2"},
    ]
    ingestion.save_candidates(project_root, candidates)

    # approve index 0
    ok = ingestion.approve_candidate(project_root, 0)
    assert ok
    # approved file exists and contains one item
    ap = ingestion.approved_path(project_root)
    assert ap.exists()
    approved = ap.read_text(encoding="utf-8")
    assert "http://example.com/a" in approved

    # remaining candidates should be one (B)
    remaining = ingestion.load_candidates(project_root)
    assert len(remaining) == 1
    assert remaining[0]["source"] == "http://example.com/b"

    # reject the remaining item
    ok2 = ingestion.reject_candidate(project_root, 0)
    assert ok2
    assert ingestion.load_candidates(project_root) == []
