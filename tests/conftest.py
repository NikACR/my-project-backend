# tests/conftest.py

import pytest
from app import create_app
from app.db import db as _db


@pytest.fixture(scope='session')
def app():
    # create_app by měl přijímat konfiguraci nebo použít default
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret",
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
