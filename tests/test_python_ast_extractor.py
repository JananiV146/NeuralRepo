from app.services.python_ast_extractor_service import PythonAstExtractorService


SOURCE = '''"""Module doc"""
import os
from pkg import thing as alias

class Example:
    """Example class"""

    def method(self):
        return 1

async def run():
    return alias
'''


def test_extract_symbols_and_imports_from_python_source() -> None:
    service = PythonAstExtractorService()

    result = service.extract("pkg/example.py", SOURCE)

    qualified_names = [symbol.qualified_name for symbol in result.symbols]
    symbol_types = [symbol.symbol_type for symbol in result.symbols]

    assert result.module_name == "pkg.example"
    assert "pkg.example" in qualified_names
    assert "pkg.example.Example" in qualified_names
    assert "pkg.example.Example.method" in qualified_names
    assert "pkg.example.run" in qualified_names
    assert "module" in symbol_types
    assert "class" in symbol_types
    assert "method" in symbol_types
    assert "async_function" in symbol_types
    assert len(result.imports) == 2
    assert result.imports[0].import_type == "import"
    assert result.imports[1].import_type == "from"


def test_module_name_handles_init_file() -> None:
    service = PythonAstExtractorService()

    result = service.extract("pkg/__init__.py", "value = 1\n")

    assert result.module_name == "pkg"
