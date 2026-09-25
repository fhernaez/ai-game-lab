import os
import tempfile

import pytest

from app import create_app
from app.extensions import db as _db
from config import TestConfig


@pytest.fixture()
def app(tmp_path):
    config = TestConfig()
    db_path = tmp_path / "test.db"
    config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(db_path)

    app = create_app(config)
    with app.app_context():
        _db.create_all()
        from app.application.seed import seed

        seed()
    yield app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return client
