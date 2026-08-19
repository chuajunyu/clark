from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_healthcheck():
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_main_pages_render():
    for path in ("/vouchers/new", "/vouchers", "/tray"):
        response = client.get(path)

        assert response.status_code == 200, path


def test_home_redirects_to_new_voucher():
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/vouchers/new"
