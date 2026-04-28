from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.project_service import ProjectService


async def _fake_get_project(self: ProjectService, project_id):  # noqa: ANN001
    return None


def test_get_missing_project_returns_404(client: TestClient) -> None:
    original = ProjectService.get_project
    ProjectService.get_project = _fake_get_project
    try:
        response = client.get(f"/api/v1/projects/{uuid4()}")
    finally:
        ProjectService.get_project = original

    assert response.status_code == 404
    assert response.json()["detail"].startswith("Project '")



def test_get_project_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.get("/api/v1/projects/not-a-uuid")

    assert response.status_code == 422
