from sqlalchemy import create_engine, text, Connection, Engine
from flask import current_app, g, Flask
import click

def db(uri=None):
    engine = None
    if uri is None:
        engine = create_engine(current_app.config.get('DATABASE'),
                               pool_recycle=3600,
                               echo=True)
    else:
        engine = create_engine(uri, pool_recycle=3600, echo=True)
    
    if 'con' not in g:
        g.con = next(get_connection(engine))

    return g.con

def get_connection(engine: Engine):
    connection = engine.connect()
    yield connection
    connection.close()


def init_db():
    con = db()
    con.execute(text('''CREATE TABLE IF NOT EXISTS guild (
        guild_id TEXT PRIMARY KEY,
        credential TEXT,
        state TEXT
    )'''))
    con.execute(text('''CREATE TABLE IF NOT EXISTS linked (
        guild_id TEXT PRIMARY KEY,
        member_id TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE
    )'''))
    con.commit()

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the database.')


def init_app(app: Flask):
    app.teardown_appcontext(close_db)
    print(f'init command registered')
    app.cli.add_command(init_db_command)
