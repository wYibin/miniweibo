from flask import Flask

#configuration
DATABASE = 'miniweibo.db'
DEBUG = True
SECRET_KEY = 'development key'

# create application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINIWEIBO_SETTING', silent=True)

import sqlite3
from flask import g

DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    rv = get_db().execute(query, args).fetchall()
    return (rv[0] if rv else None) if one else rv

def get_user_id(username):
    rv = query_db('SELECT * FROM users WHERE username=?', [username], one=True)
    return rv[0] if rv else None

@app.route('/')
def index():
    return '<h1>Hello, MiniWeibo!</h1>'
