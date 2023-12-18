import google_auth_oauthlib
import google.oauth2.credentials
import pytest
import api
import requests
from mock import MagicMock
from mock import Mock

@pytest.fixture
def mock_google_client(mocker):
    mock_google_client = MagicMock(spec=google_auth_oauthlib.flow.Flow)
    mocker.patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file',
                 return_value=mock_google_client)
    return mock_google_client

@pytest.fixture
def mock_google_oauth2(mocker):
    mock_google_oauth2 = MagicMock(spec=google.oauth2.credentials)
    mocker.patch('google.oauth2.credentials', return_value=mock_google_oauth2)
    return mock_google_oauth2

@pytest.fixture
def mock_post(mocker):
    mock = MagicMock(spec=requests.Response)
    mocker.patch('requests.post', return_value=mock)
    return mock

@pytest.fixture()
def app(mocker):
    app = api.app
    app.config.update({"TESTING": True})
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

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db():
    return next(api.get_connection())

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
