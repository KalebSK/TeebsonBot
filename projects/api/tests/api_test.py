from flask import session
from sqlalchemy import Connection, text
import json

def wipe_guild_table(con: Connection):
    con.execute(text("DELETE FROM guild"))
    con.commit()

class TestApi:
    def test_auth_flow(self, client, db, mock_google_client):
        db.execute(text("INSERT INTO guild VALUES(:guild_id, :credential, :state)"),
                    {
                        'guild_id': '123',
                        'state': 'xyz',
                        'credential': None
                    })
        db.commit()
        mock_google_client.authorization_url.return_value = (
            'http://localhost:5000/oauth2callback', 'abc')
        mock_google_client.fetch_token.return_value = None
        response = client.get('/authorize/123/xyz', follow_redirects=True)
        assert session['state'] == 'abc'
        assert session['app_state'] == 'xyz'
        assert session['guild_id'] == '123'
        assert len(response.history) == 2
        assert response.request.path == '/'
        assert response.status_code == 200
        result = db.execute(text(
            "SELECT * FROM guild WHERE guild_id = '123'")).fetchone()._tuple()
        creds_as_string = json.dumps({
            "token": "abc",
            "refresh_token": "def",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "client_id": "ghi",
            "client_secret": "jkl",
            "scopes": ['scope1', 'scope2', 'scope3'],
        })
        assert result == ('123', creds_as_string, 'xyz')
    
        wipe_guild_table(db)
    

    def test_revoke_credentials_successful(self, client, db, mock_post,
                                        mock_google_oauth2):
        creds = json.dumps({
            'token': '123',
            'refresh_token': '456',
            'token_uri': 'https://accounts.google.com/o/oauth2/token',
            'client_id': 'ghi',
            'client_secret': 'jkl',
            'scopes': ['scope1', 'scope2', 'scope3'],
        })
        db.execute(text("INSERT INTO guild VALUES ('123', :creds , 'xyz')"),
                {'creds': creds})
        db.commit()
        mock_google_oauth2.Credentials.return_value = 'abc'
        mock_post.status_code = 200
        response = client.get('/revoke/123', headers={'Authorization': 'key'})
        assert response.status_code == 200
        assert response.text == 'Credentials revoked'
    
        wipe_guild_table(db)
    
    def test_revoke_credentials_invalid_guild_id(self, client, db):
        db.execute(text("INSERT INTO guild VALUES ('456', 'abc', 'xyz')"))
        db.commit()
        response = client.get('/revoke/123', headers={'Authorization': 'key'})
        assert response.status_code == 400
        assert response.text == 'bad request'
    
    
    def test_revoke_credentials_server_error(self, client, db, mock_post):
        creds = json.dumps({
            'token': '123',
            'refresh_token': '456',
            'token_uri': 'https://accounts.google.com/o/oauth2/token',
            'client_id': 'ghi',
            'client_secret': 'jkl',
            'scopes': ['scope1', 'scope2', 'scope3'],
        })
        db.execute(text("INSERT INTO guild VALUES ('123',:creds, 'xyz')"),
                {'creds': creds})
        db.commit()
        mock_post.status_code = 404
    
        response = client.get('/revoke/123', headers={'Authorization': 'key'})
        assert response.status_code == 500
    
        assert response.text == 'internal server error'
        wipe_guild_table(db)
    
    
    def test_revoke_credentials_valid_guild_id_no_credential(self, client, db):
        db.execute(text("INSERT INTO guild VALUES ('123', 'null', 'xyz')"))
        db.commit()
        response = client.get('/revoke/123', headers={'Authorization': 'key'})
        assert response.status_code == 400
    
    def test_revoke_credentials_no_api_key(self, client):
        response = client.get('/revoke/123')
        assert response.status_code == 403
    
    def test_revoke_credentials_invalid_api_key(self, client):
        response = client.get('/revoke/123', headers={'Authorization': 'invalid'})
        assert response.status_code == 403