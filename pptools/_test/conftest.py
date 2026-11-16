"""Shared test setup

`app` is a front application on a fresh projects folder in `tmp_path`;
`client` is its Flask test client; `post` sends a JSON API request with
the required `X-PPTools` header and returns `(status, json)`.
"""

import pytest

from pptools import create_app

@pytest.fixture
def app(tmp_path):
    """Front application on an empty projects folder"""
    app = create_app(str(tmp_path/"projects"))
    app.config["TESTING"] = True
    yield app
    app.config["MODELS"].stop_all()

@pytest.fixture
def client(app):
    """Flask test client of `app`"""
    return app.test_client()

@pytest.fixture
def post(client):
    """POST JSON to the API and return (status, json)"""
    def _post(path,body=None):
        res = client.post(path,json=body or {},headers={"X-PPTools":"1"})
        return res.status_code,res.get_json()
    return _post
