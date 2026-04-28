from app.services.repository_dependency_graph_service import RepositoryDependencyGraphService



def test_resolve_relative_from_import_module_candidate() -> None:
    service = RepositoryDependencyGraphService(session=None)  # type: ignore[arg-type]
    candidates = service._candidate_modules(
        source_module_name="pkg.api.handlers",
        import_type="from",
        module_name=".services",
        imported_name="auth",
    )

    assert candidates == ["pkg.api.services.auth", "pkg.api.services"]



def test_module_name_from_init_file() -> None:
    service = RepositoryDependencyGraphService(session=None)  # type: ignore[arg-type]

    assert service._module_name_from_path("pkg/__init__.py") == "pkg"
    assert service._module_name_from_path("pkg/core/utils.py") == "pkg.core.utils"



def test_resolve_import_target_marks_external_when_not_local() -> None:
    service = RepositoryDependencyGraphService(session=None)  # type: ignore[arg-type]
    target_module_name, target_file_id, is_internal = service._resolve_import_target(
        source_module_name="pkg.core.utils",
        import_type="import",
        module_name="requests",
        imported_name=None,
        module_index={"pkg.core.utils": "ignored"},  # type: ignore[arg-type]
        module_roots={"pkg"},
    )

    assert target_module_name == "requests"
    assert target_file_id is None
    assert is_internal is False
