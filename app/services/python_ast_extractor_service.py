import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExtractedSymbol:
    symbol_type: str
    name: str
    qualified_name: str
    parent_qualified_name: str | None
    line_start: int
    line_end: int
    docstring: str | None
    is_public: bool


@dataclass(slots=True)
class ExtractedImport:
    import_type: str
    module_name: str | None
    imported_name: str | None
    alias: str | None
    line_number: int


@dataclass(slots=True)
class PythonAstExtractionResult:
    module_name: str
    symbols: list[ExtractedSymbol]
    imports: list[ExtractedImport]


class PythonAstExtractorService:
    def extract(self, relative_path: str, source: str) -> PythonAstExtractionResult:
        module_name = self._module_name_from_path(relative_path)
        tree = ast.parse(source)
        symbols: list[ExtractedSymbol] = []
        imports: list[ExtractedImport] = []
        module_line_end = max(len(source.splitlines()), 1)
        symbols.append(
            ExtractedSymbol(
                symbol_type="module",
                name=module_name.split(".")[-1],
                qualified_name=module_name,
                parent_qualified_name=None,
                line_start=1,
                line_end=module_line_end,
                docstring=ast.get_docstring(tree),
                is_public=not module_name.split(".")[-1].startswith("_"),
            )
        )

        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(self._extract_imports(node))
            elif isinstance(node, ast.ImportFrom):
                imports.extend(self._extract_imports(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.extend(self._extract_symbols(node, module_name, None))

        for node in ast.walk(tree):
            if node in tree.body:
                continue
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(self._extract_imports(node))

        return PythonAstExtractionResult(module_name=module_name, symbols=symbols, imports=imports)

    def _extract_symbols(
        self,
        node: ast.AST,
        module_name: str,
        parent_qualified_name: str | None,
    ) -> list[ExtractedSymbol]:
        symbols: list[ExtractedSymbol] = []

        if isinstance(node, ast.ClassDef):
            qualified_name = self._join_qualified_name(parent_qualified_name or module_name, node.name)
            symbols.append(
                ExtractedSymbol(
                    symbol_type="class",
                    name=node.name,
                    qualified_name=qualified_name,
                    parent_qualified_name=parent_qualified_name or module_name,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    docstring=ast.get_docstring(node),
                    is_public=not node.name.startswith("_"),
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.extend(self._extract_symbols(child, module_name, qualified_name))
            return symbols

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol_type = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            if parent_qualified_name and parent_qualified_name != module_name:
                symbol_type = "async_method" if isinstance(node, ast.AsyncFunctionDef) else "method"

            qualified_name = self._join_qualified_name(parent_qualified_name or module_name, node.name)
            symbols.append(
                ExtractedSymbol(
                    symbol_type=symbol_type,
                    name=node.name,
                    qualified_name=qualified_name,
                    parent_qualified_name=parent_qualified_name or module_name,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    docstring=ast.get_docstring(node),
                    is_public=not node.name.startswith("_"),
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.extend(self._extract_symbols(child, module_name, qualified_name))
            return symbols

        return symbols

    def _extract_imports(self, node: ast.AST) -> list[ExtractedImport]:
        imports: list[ExtractedImport] = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ExtractedImport(
                        import_type="import",
                        module_name=alias.name,
                        imported_name=None,
                        alias=alias.asname,
                        line_number=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = "." * node.level + (node.module or "")
            for alias in node.names:
                imports.append(
                    ExtractedImport(
                        import_type="from",
                        module_name=module_name or None,
                        imported_name=alias.name,
                        alias=alias.asname,
                        line_number=node.lineno,
                    )
                )
        return imports

    def _module_name_from_path(self, relative_path: str) -> str:
        path = Path(relative_path)
        parts = list(path.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = path.stem
        return ".".join(parts)

    def _join_qualified_name(self, base: str, name: str) -> str:
        return f"{base}.{name}" if base else name
