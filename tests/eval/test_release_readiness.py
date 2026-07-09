from pathlib import Path


def test_ci_workflow_exists_and_runs_pytest():
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python-version: \"3.12\"" in ci
    assert "python -m compileall src scripts eval" in ci
    assert "pytest tests/ -q" in ci


def test_github_publish_guide_exists():
    guide = Path("docs/github_publish_guide.md").read_text(encoding="utf-8")
    assert "git push -u origin master" in guide
    assert "git push origin v1.0.0-harness" in guide
    assert "git push --force" in guide


def test_untracked_directory_audit_documents_local_dirs():
    audit = Path("docs/untracked_directories_audit.md").read_text(encoding="utf-8")
    assert "FireRed-OpenStoryline/" in audit
    assert "Mainline dependency: none found" in audit
    assert "archive_before_cleanup/" in audit


def test_gitignore_blocks_raw_outputs_and_reference_dirs():
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/" in ignore
    assert "outputs/" in ignore
    assert "FireRed-OpenStoryline/" in ignore
    assert "archive_before_cleanup/" in ignore
