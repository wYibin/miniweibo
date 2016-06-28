import time
import sqlite3
from flask import Flask, render_template, redirect, url_for, \
    session, g, abort
from werkzeug import generate_password_hash, check_password_hash

#configuration
DATABASE = 'miniweibo.db'
DEBUG = True
SECRET_KEY = 'development key'
PER_PAGE = 20

# create application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINIWEIBO_SETTING', silent=True)

DATABASE = 'database.db'

def get_db():
    """Open a new database connection if there is none yet for the
    current application context.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    """Close the database when the request context ended."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initiate the database."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    """Queries the database and return a list of dictionaries."""
    rv = get_db().execute(query, args).fetchall()
    return (rv[0] if rv else None) if one else rv

def get_user_id(username):
    """Convenience method to look up the id for a given username."""
    rv = query_db('SELECT * FROM users WHERE username=?', [username], one=True)
    return rv[0] if rv else None

@app.route('/')
def timeline():
    """Show the messages from the current user or other users he is followed.
    If no user is logged in it will redirect to the public timeline.
    """
    if not g.user:
        return redirect(url_for('public_timeline'))
    query = '''
        SELECT messages.*, users.* FROM messages, users
        WHERE messages.user_id = users.user_id AND (
            users.user_id = ? OR
            users.user_id IN (SELECT followed_id FROM follows
                WHERE follower_id = ?))
        ORDER BY messages.pub_time DESC LIMIT ?'''
    messages = query_db(query, [session['user_id'], session['user_id'], PER_PAGE])
    return  render_template('timeline.html', messages=messages)

@app.route('/public')
def public_timeline():
    """Display the lastest mesages of all users."""
    query = '''
        SELECT messages.*, users.* FROM messages, users
        WHERE messages.user_id = users.user_id
        ORDER BY messages.pub_time DESC LIMIT ?'''
    messages = query_db(query, [PER_PAGE])
    return render_template('timeline.html', messages=messages)

@app.route('/<username>')
def user_timeline(username):
    """Display a users posts."""
    profile_user = query_db('SELECT * FROM user WHERE user_name = ?',
        [username], one=True)
    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = query_db('''SELECT 1 FROM follows WHERE
            follows.follower_id = ? AND follows.followed_id = ?''',
            [session['user_id'], profile_user['user_id']],
            one=True) is not None
    query = '''
        SELECT messages.*, users.* FROM messages, users
        WHERE users.user_id = message.user_id AND users.user_id = ?
        ORDER BY messages.pub_time DESC LIMIT ?'''
    messages = query_db(query, [profile_user[user_id], PER_PAGE])
    return render_template('timeline.html', messages=messages,
        followed=followed, profile_user=profile_user)

@app.route('/<username>/follow')
def follow(username):
    """Add the current user as follower of the given user."""
    if not g.user:
        abort(401)
    followed_id = get_user_id(username)
    if followed_id is None:
        abort(404)
    db = get_db()
    db.execute('''INSERT INTO follows (follower_id, followed_id)
        VALUES (?, ?)''', [session['user_id'], followed_id])
    db.commit()
    flash('Your are now following "%s".' % username)
    return redirect(url_for('user_timeline', username=username))

@app.route('/<username>/unfollow')
def unfollow(username):
    """Remove the current user as follower of the given user."""
    if not g.user:
        abort(401)
    followed_id = get_user_id(username)
    if followed_id is None:
        abort(404)
    db = get_db()
    db.execute('DELETE FROM follows WHERE follower_id=? AND followed_id=?',
        [session['user_id'], followed_id])
    db.commit()
    flash('You are no longer following "%s".' % username)
    return redirect(url_for('user_timeline', username=username))

@app.route('/add_message', methods=['POST'])
def add_message():
    """Post a message."""
    if not g.user:
        abort(401)
    if request.form['text']:
        db = get_db()
        db.execute('''INSERT INTO messages (user_id, text, pub_time)
            VALUES (?, ?, ?)''', [session['user_id'], request.form['text'],
            int(time.time())])
        db.commit()
        flash('Your message was recorded.')
    return redirect(url_for('timeline'))

@app.route('/register')
def register():
    """Register an account"""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid emial address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two password do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute('''INSERT INTO users (user_name, email, pw_hash) VALUES
                (?, ?, ?)''', [request.form['username'], request.form['email'], generate_password_hash(request.form['password'])])
            db.commit()
            flakh('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in"""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        user = query_db('''SELECT * FROM users WHERE user_name=?''',
            [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'], request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in.')
            session['user_id'] = user['user_id']
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out"""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('public_timeline'))

@app.route('/follow_list')
def follow_list():
    """List the users current user are following and the users who are
    following he.
    """
    if not g.user:
        abort(401)
    followed = query_db('SELECT * FROM follows WHERE follower_id=?',
        [session['user_id']])
    follower = query_db('SELECT * FROM follows WHERE followed_id=?',
        [session['user_id']])
    return render_template('follow_list.html', followed=followed, follower=follower)
