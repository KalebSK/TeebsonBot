from flask import Flask, g
import google_auth_oauthlib.flow as flow
import google.oauth2.credentials
import pytest
import api
import requests
import db as database
from unittest.mock import MagicMock
from unittest.mock import Mock

@pytest.fixture
def mock_google_client(mocker):
    mock_google_client = MagicMock(spec=flow.Flow)
    mocker.patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file',
                 return_value=mock_google_client)
    return mock_google_client

"""patches the google.oauth2.credentials module to return a mock credential"""
@pytest.fixture
def mock_google_oauth2(mocker):
    mock_google_oauth2 = MagicMock(spec=google.oauth2.credentials)
    mocker.patch('google.oauth2.credentials', return_value=mock_google_oauth2)
    return mock_google_oauth2

"""patches the requests.post method to return a mock response"""
@pytest.fixture
def mock_post(mocker):
    mock = MagicMock(spec=requests.Response)
    mocker.patch('requests.post', return_value=mock)
    return mock

"""Provides a Flask application fixture for testing.

Creates a Flask app with test configuration, patches credential 
loading and HTTP requests, yields the app for test usage, then resets
the configuration after testing."""
@pytest.fixture()
def app(mocker):
    app = api.create_app(testing=True)
    app.config.update({"API_KEY": 'key'})

    mocker.patch('api.credentials_to_dict',
                 return_value={
                     "token": "abc",
                     "refresh_token": "def",
                     "token_uri": "https://accounts.google.com/o/oauth2/token",
                     "client_id": "ghi",
                     "client_secret": "jkl",
                     "scopes": ['scope1', 'scope2', 'scope3'],
                 })
    mocker.patch('requests.post', return_value=Mock())
    yield app
    app.config.update({"TESTING": False})

"""Yields a database connection."""
@pytest.fixture()
def db(context):
    with context:
        yield g.con
        database.close_db()

"""Initializes the database before each test."""
@pytest.fixture(autouse=True)
def init_db(context):
    with context:
        database.init_db()
        return True

"""Provides a Flask test client for use during testing.

Yields an app test client that can make requests to the Flask
app in a test context."""
@pytest.fixture()
def client(app: Flask, context ,init_db):
    with context:
        with app.test_client() as test_client:
            yield test_client

"""Provides an application context."""
@pytest.fixture()
def context(app: Flask):
    with app.app_context() as context:
        return context

"""Returns the Flask test CLI runner for the given app.

This is a pytest fixture that can be used to invoke CLI commands
for the Flask app during testing."""
@pytest.fixture()
def runner(app: Flask):
    return app.test_cli_runner()
