from pathlib import Path

from app.services.repository_scanner_service import RepositoryScannerService



def test_iter_files_skips_common_build_and_git_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("ignored", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("ignored", encoding="utf-8")

    service = RepositoryScannerService(session=None)  # type: ignore[arg-type]
    files = service._iter_files(tmp_path)

    assert [file.relative_to(tmp_path).as_posix() for file in files] == ["src/main.py"]
