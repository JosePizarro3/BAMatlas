from django.test import Client


def test_home_page_returns_ok():
    response = Client().get("/")

    assert response.status_code == 200
    assert b"BAMatlas" in response.content
