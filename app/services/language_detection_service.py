from pathlib import Path


class LanguageDetectionService:
    EXTENSION_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".sql": "sql",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".dockerfile": "dockerfile",
    }
    SPECIAL_FILENAMES = {
        "dockerfile": "dockerfile",
        "makefile": "makefile",
        ".gitignore": "gitignore",
        ".env": "dotenv",
    }

    def detect_language(self, file_path: Path) -> str:
        filename = file_path.name.lower()
        if filename in self.SPECIAL_FILENAMES:
            return self.SPECIAL_FILENAMES[filename]

        suffix = file_path.suffix.lower()
        return self.EXTENSION_MAP.get(suffix, "plaintext")

    def detect_content_type(self, file_path: Path, raw_bytes: bytes) -> str:
        if b"\x00" in raw_bytes[:1024]:
            return "binary"
        return "text"
