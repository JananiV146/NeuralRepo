from uuid import uuid4

from fastapi.testclient import TestClient



def test_get_missing_project_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/projects/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"].startswith("Project '")



def test_get_project_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.get("/api/v1/projects/not-a-uuid")

    assert response.status_code == 422
