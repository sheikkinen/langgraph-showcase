"""Tests for booking API main entry point."""

from fastapi.testclient import TestClient


class TestMainApp:
    """Tests for main.py app configuration."""

    def test_app_exists(self):
        """Main module should export 'app'."""
        from examples.booking.main import app

        assert app is not None

    def test_app_title(self):
        """App should have correct title."""
        from examples.booking.main import app

        assert app.title == "Booking API"

    def test_health_endpoint(self):
        """Health endpoint should work."""
        from examples.booking.main import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_calendars_endpoint(self):
        """Calendar endpoints should be registered."""
        from examples.booking.main import app

        with TestClient(app) as client:
            response = client.get("/calendars")
            assert response.status_code == 200

    def test_openapi_schema(self):
        """OpenAPI schema should be available."""
        from examples.booking.main import app

        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            schema = response.json()
            assert schema["info"]["title"] == "Booking API"
            assert "/calendars" in schema["paths"]
            assert "/appointments" in schema["paths"]
            assert "/chat/{thread_id}" in schema["paths"]
