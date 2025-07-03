# tests/test_menu.py

import pytest
from app.db import db
from app.models import Alergen, PolozkaMenu, PolozkaMenuAlergen


def register_and_login(client, email="user@example.com", password="pass1234"):
    # předpokládáme, že máte endpointy /auth/register a /auth/login
    rv = client.post("/auth/register", json={
        "jmeno": "Test",
        "prijmeni": "User",
        "email": email,
        "password": password
    })
    assert rv.status_code == 201

    rv = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    assert rv.status_code == 200
    token = rv.get_json()["access_token"]
    return token


def test_get_menu_unauthorized(client):
    rv = client.get("/menu")
    assert rv.status_code == 401


def test_get_menu_empty(client):
    token = register_and_login(client, "empty@example.com", "password")
    rv = client.get("/menu", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert rv.get_json() == []


@pytest.fixture
def sample_menu_item(app):
    # vložíme do DB jednu položku menu s jedním alergenem
    with app.app_context():
        al = Alergen(nazev="Mléko", popis="Testovací alergen")
        it = PolozkaMenu(nazev="Test pizza", popis="Popis", cena=99.9)
        db.session.add_all([al, it])
        db.session.flush()
        link = PolozkaMenuAlergen(
            id_menu_polozka=it.id_menu_polozka, id_alergenu=al.id_alergenu)
        db.session.add(link)
        db.session.commit()


def test_get_menu_with_data(client, sample_menu_item):
    token = register_and_login(client, "data@example.com", "password")
    rv = client.get("/menu", headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200

    data = rv.get_json()
    # musí být seznam délky 1
    assert isinstance(data, list) and len(data) == 1

    item = data[0]
    assert item["nazev"] == "Test pizza"
    assert isinstance(item["alergeny"], list) and len(item["alergeny"]) == 1

    al = item["alergeny"][0]
    # ověříme strukturu alergen objektu
    assert set(al.keys()) >= {"id_alergenu", "nazev", "popis"}
    assert al["nazev"] == "Mléko"
