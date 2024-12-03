from fastapi.testclient import TestClient
from app import app
from utils.test_utils import BaseTestCase


class TestApp(BaseTestCase):
    def test_status(self):
        client = TestClient(app)
        response = client.get("status")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_home(self):
        client = TestClient(app)
        # test that home redirects to docs
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307

        response = client.get("", follow_redirects=False)
        assert response.status_code == 307

        response = client.get("", follow_redirects=True)
        assert response.status_code == 200
        assert response.url == "http://testserver/docs"
