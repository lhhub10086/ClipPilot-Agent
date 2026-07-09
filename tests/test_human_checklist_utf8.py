from pathlib import Path


def test_human_checklist_utf8_has_readable_chinese(tmp_path: Path):
    text = "主题完整性\n开头不是半句话\n字幕与语音基本一致\n"
    path = tmp_path / "checklist.md"
    path.write_text(text, encoding="utf-8")
    reread = path.read_text(encoding="utf-8")
    assert "主题完整性" in reread
    assert "????" not in reread
