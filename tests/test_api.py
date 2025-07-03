import os
import sys
from datetime import date

import pytest

# přidej kořenový adresář do sys.path, aby importy z app/ fungovaly
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
sys.path.insert(0, project_root)

from app import create_app
from app.db import db
from app.models import Zakaznik, VernostniUcet


@pytest.fixture(scope='module')
def test_client():
    app = create_app(config_name="testing")  # v testovací configu máš in-memory sqlite
    client = app.test_client()
    ctx = app.app_context()
    ctx.push()
    yield client
    ctx.pop()


@pytest.fixture(scope='module')
def init_database(test_client):
    db.create_all()
    yield
    db.drop_all()


@pytest.fixture(scope='function')
def seed_db(test_client, init_database):
    # před každým testem smažeme všechna data, ale necháme strukturu
    db.session.remove()
    db.drop_all()
    db.create_all()

    # Vložíme dva zákazníky + jejich účty
    zak1 = Zakaznik(jmeno='testuser1', prijmeni='Prvni', email='test1@example.com', telefon='111')
    zak1.password = 'password1'
    zak2 = Zakaznik(jmeno='testuser2', prijmeni='Druhy', email='test2@example.com', telefon='222')
    zak2.password = 'password2'
    db.session.add_all([zak1, zak2])
    db.session.commit()

    uc1 = VernostniUcet(body=0, datum_zalozeni=date(2025, 1, 1), zakaznik=zak1)
    uc2 = VernostniUcet(body=0, datum_zalozeni=date(2025, 1, 2), zakaznik=zak2)
    db.session.add_all([uc1, uc2])
    db.session.commit()

    yield

    # po testu jen vyčistíme session, tabulky zůstanou pro další seed
    db.session.remove()


def test_get_zakaznik_list(test_client, seed_db):
    resp = test_client.get('/api/zakaznik')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_create_zakaznik_success(test_client, seed_db):
    new = {
        "jmeno": "novy",
        "prijmeni": "Zakaznik",
        "email": "novy@example.com",
        "telefon": "999",
        "password": "tajnicaslo"
    }
    resp = test_client.post('/api/zakaznik', json=new)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['email'] == new['email']
    # ověříme, že to opravdu existuje v DB a heslo sedí
    zak = db.session.get(Zakaznik, data['id_zakaznika'])
    assert zak and zak.check_password(new['password'])


def test_create_zakaznik_duplicate_email(test_client, seed_db):
    dup = {
        "jmeno": "x",
        "prijmeni": "x",
        "email": "test1@example.com",
        "telefon": "000",
        # password musí mít alespoň 8 znaků, aby došlo ke kontrole unikátního emailu
        "password": "duplicate"
    }
    resp = test_client.post('/api/zakaznik', json=dup)
    assert resp.status_code == 409


def test_create_zakaznik_missing_field(test_client, seed_db):
    resp = test_client.post('/api/zakaznik', json={})
    assert resp.status_code == 422


def test_get_single_zakaznik_success(test_client, seed_db):
    zak = Zakaznik.query.filter_by(email='test1@example.com').first()
    resp = test_client.get(f'/api/zakaznik/{zak.id_zakaznika}')
    assert resp.status_code == 200


def test_get_single_zakaznik_not_found(test_client, seed_db):
    resp = test_client.get('/api/zakaznik/9999')
    assert resp.status_code == 404


def test_update_zakaznik_success(test_client, seed_db):
    zak = Zakaznik.query.filter_by(email='test1@example.com').first()
    resp = test_client.put(f'/api/zakaznik/{zak.id_zakaznika}', json={"telefon": "123"})
    assert resp.status_code == 200
    assert resp.get_json()['telefon'] == "123"


def test_update_zakaznik_not_found(test_client, seed_db):
    resp = test_client.put('/api/zakaznik/9999', json={"telefon": "123"})
    assert resp.status_code == 404


def test_delete_zakaznik_success(test_client, seed_db):
    zak = Zakaznik.query.filter_by(email='test1@example.com').first()
    resp = test_client.delete(f'/api/zakaznik/{zak.id_zakaznika}')
    assert resp.status_code == 204
    assert db.session.get(Zakaznik, zak.id_zakaznika) is None


def test_delete_zakaznik_not_found(test_client, seed_db):
    resp = test_client.delete('/api/zakaznik/9999')
    assert resp.status_code == 404
