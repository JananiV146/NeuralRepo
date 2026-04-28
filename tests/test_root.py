from fastapi.testclient import TestClient



def test_root_route(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"



def test_favicon_route_returns_no_content(client: TestClient) -> None:
    response = client.get("/favicon.ico")

    assert response.status_code == 204
