import flask
from flask import g
import requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import json
from sqlalchemy import text
import os
from werkzeug.middleware.proxy_fix import ProxyFix

CLIENT_SECRETS_FILE = 'creds.json'
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
API_SERVICE_NAME = "calendar"
API_VERSION = 'v3'


def create_app(config_name='config.py', testing=False, instance_path: str | None = None, environment='development'):
    if instance_path is None:
        app = flask.Flask(__name__)
    else:
        app = flask.Flask(__name__, instance_path=instance_path)

    app.config.from_pyfile(config_name)
    app.config.update({'ENVIRONMENT': environment})

    if environment == 'production':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=2, x_host=2, x_prefix=2)
    
    app.secret_key = app.config.get('SECRET_KEY')
    if testing:
        app.config.update({"TESTING": True})
        app.config.update({"DATABASE": 'sqlite:///:memory:'})
    else:
        app.config.update({'TESTING': False})
        app.config.update({'DATABASE': f'sqlite:///{app.instance_path}/guilds.db'})

    if app.config.get('ENVIRONMENT') == 'development':
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    path = f'{app.instance_path}/guilds.db'
    if not testing:
        if os.path.isfile(path):
            print('database file is mounted!')
        else:
            print('database file is missing!')
            quit()

    from db import init_app, db
    init_app(app)

    def validate_auth_header(request: flask.Request):
        auth_header = request.headers.get('Authorization')
        if auth_header == app.config.get('API_KEY'):
            return True
        return False

    @app.route("/")
    def index():
        return '<h1>return to discord!</h1>'
    
    @app.route('/authorize/<guild_id>/<app_state>')
    def authorize(guild_id, app_state):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES)
        flow.redirect_uri = flask.url_for('oauth2callback', _external=True)
        auth_url, state = flow.authorization_url(access_type='offline',
                                                 prompt='consent')
        flask.session['state'] = state
        flask.session['guild_id'] = guild_id
        flask.session['app_state'] = app_state
        return flask.redirect(auth_url)

    @app.route('/oauth2callback')
    def oauth2callback():
        con = db()
        state = flask.session['state']
        guild_id = flask.session['guild_id']
        app_state = flask.session['app_state']

        guild = con.execute(text("SELECT * FROM guild WHERE guild_id=:id"), {
            'id': guild_id
        }).fetchone()

        if guild is None:
            flask.abort(400)

        guild = guild._tuple()

        if guild[2] != app_state:
            flask.abort(400)

        try:
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=None,
                state=state,
                redirect_uri=flask.url_for('oauth2callback', _external=True))

            auth_resp = flask.request.url
            flow.fetch_token(authorization_response=auth_resp)

            credentials = flow.credentials
            con.execute(
                text("""
                UPDATE guild SET credential=:new_cred WHERE guild_id=:id
            """), {
                    'id': guild_id,
                    'new_cred': json.dumps(credentials_to_dict(credentials)),
                })
            return flask.redirect(flask.url_for('index'))
        finally:
            con.commit()

    @app.route('/revoke/<guild_id>')
    def revoke(guild_id):
        con = db()
        if not validate_auth_header(flask.request):
            flask.abort(403)
        try:
            res = con.execute(
                text("SELECT credential FROM guild WHERE guild_id=:guild_id"),
                {
                    'guild_id': guild_id
                }).fetchone()

            if res == None:
                flask.abort(400)

            creds = res._tuple()[0]
            if creds == 'null' or creds == None:
                flask.abort(400)

            credentials = google.oauth2.credentials.Credentials(
                **json.loads(creds))

            revoke = requests.post(
                'http://oauth2.googleapis.com/revoke',
                params={'token': credentials.token},
                headers={'content-type': 'application/x-www-form-urlencoded'})
            status_code = getattr(revoke, 'status_code')
            print(f'Status code: {status_code}')
            if status_code == 200:
                return ('Credentials revoked')
            else:
                flask.abort(500)
        finally:
            con = g.con
            con.commit()

    @app.route('/clear/<guild_id>')
    def clear_credentials(guild_id: str):
        con = db()
        try:
            res = con.execute(
                text("SELECT credential FROM guild WHERE guild_id=:guild_id"), {'guild_id': guild_id})

            creds = res.fetchone()
            if creds:
                con.execute(text("DELETE FROM guild WHERE guild_id=:guild_id"), {'guild_id': guild_id})
            return ('credentials cleared')
        finally:
            con.commit()



    @app.errorhandler(400)
    def bad_request(e):
        return 'bad request', 400

    @app.errorhandler(403)
    def not_authorized(e):
        return 'unauthorized request', 403

    @app.errorhandler(500)
    def server_error(e):
        return 'internal server error', 500

    return app

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
#    if not app.config.get('TESTING'):
#    ask_to_drop_table = input(
#        "would you like to drop the 'guild' table from the database. WARNING: DROPPING THE TABLE DELETES ALL OF THE DATA [Yes/No]: "
#    )
#
#    if ask_to_drop_table.lower() == "yes":
#        con.execute(text("DROP TABLE guild"))

# con.execute(
#    text('''CREATE TABLE IF NOT EXISTS guild (
#  guild_id TEXT PRIMARY KEY,
#  credential TEXT,
#  state TEXT
#)'''))

#con.execute(
#    text('''CREATE TABLE IF NOT EXISTS linked (
#         guild_id TEXT PRIMARY KEY,
#         member_id TEXT NOT NULL UNIQUE,
#         email TEXT NOT NULL UNIQUE,
#    )

#'''))
#con.commit()
#con.close()
