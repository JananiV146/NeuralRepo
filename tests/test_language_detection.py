from pathlib import Path

from app.services.language_detection_service import LanguageDetectionService



def test_detect_language_from_extension() -> None:
    service = LanguageDetectionService()

    assert service.detect_language(Path("main.py")) == "python"
    assert service.detect_language(Path("index.tsx")) == "typescript"
    assert service.detect_language(Path("README.md")) == "markdown"



def test_detect_language_from_special_filename() -> None:
    service = LanguageDetectionService()

    assert service.detect_language(Path("Dockerfile")) == "dockerfile"
    assert service.detect_language(Path(".gitignore")) == "gitignore"



def test_detect_binary_content_type() -> None:
    service = LanguageDetectionService()

    assert service.detect_content_type(Path("image.bin"), b"\x00\x01\x02") == "binary"
    assert service.detect_content_type(Path("main.py"), b"print('hi')\n") == "text"
