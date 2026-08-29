import os

os.environ["DATABASE_URL"] = "sqlite:///./test_project.db"
os.environ["JWT_SECRET"] = "test-secret-with-at-least-thirty-two-characters"
os.environ["DEMO_PASSWORD"] = "TestProjet123"

import pytest
from fastapi.testclient import TestClient

from app.core.base_de_donnees import BaseModele, moteur
from app.main import application


@pytest.fixture()
def client():
    BaseModele.metadata.drop_all(bind=moteur)
    with TestClient(application) as test_client:
        yield test_client
    BaseModele.metadata.drop_all(bind=moteur)


@pytest.fixture()
def authenticated(client):
    response = client.post("/api/authentification/connexion", json={"courriel": "trellikarl@mentor.com", "mot_de_passe": "TestProjet123"})
    assert response.status_code == 200
    csrf = client.cookies.get("csrf_token")
    client.headers.update({"X-CSRF-Token": csrf})
    return client
