from flask import Flask

#configuration
DATABASE = 'miniweibo.db'
DEBUG = True
SECRET_KEY = 'development key'

# create application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINIWEIBO_SETTING', silent=True)

@route('/')
def index():
    return '<h1>Hello, MiniWeibo!</h1>'
