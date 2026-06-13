import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_home_page_returns_ok():
    response = Client().get("/")

    assert response.status_code == 200
    assert b"Find BAM expertise." in response.content


def test_health_endpoint_returns_ok():
    response = Client().get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
