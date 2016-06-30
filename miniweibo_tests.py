import os
import miniweibo
import unittest
import tempfile
from flask_bootstrap import Bootstrap
import flask

class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        """Create a new test client and initialize a new database"""
        self.db_fd, miniweibo.app.config['DATABASE'] = tempfile.mkstemp()
        miniweibo.app.config['TESTING'] = True
        self.app = miniweibo.app.test_client()
        with miniweibo.app.app_context():
            miniweibo.init_db()

    def tearDown(self):
        """Delete the database after the test"""
        os.close(self.db_fd)
        os.unlink(miniweibo.app.config['DATABASE'])

    def register(self, username, password, password2=None, email=None):
        """Helper function to register a user"""
        if password2 is None:
            password2 = password
        if email is None:
            email = username + '@example.com'
        return self.app.post('/register', data={
            'username': username,
            'password': password,
            'password2': password2,
            'email': email
        }, follow_redirects=True)

    def login(self, username, password):
        """Helper function to sign in"""
        return self.app.post('/login', data={
            'username': username,
            'password': password,
        }, follow_redirects=True)

    def register_and_login(self, username, password):
        """Register an account then login"""
        self.register(username, password)
        return self.login(username, password)

    def logout(self):
        """Helper function to logout"""
        return self.app.get('/logout', follow_redirects=True)

    def add_message(self, text):
        """Helper function to add a message"""
        rv = self.app.post('/add_message', data={'text': text},
            follow_redirects=True)
        return rv

    def test_register(self):
        """Make sure registering works"""
        rv = self.register('user1', 'default')
        assert 'You were successfully registered and can login now' in rv.data
        rv = self.register('user1', 'default')
        assert 'The username is already taken' in rv.data
        rv = self.register('', 'default')
        assert 'You have to enter a username' in rv.data
        rv = self.register('meh', '')
        assert 'You have to enter a password' in rv.data
        rv = self.register('meh', 'x', 'y')
        assert 'The two password do not match' in rv.data
        rv = self.register('meh', 'foo', email='broken')
        assert 'You have to enter a valid email address' in rv.data

    def test_login_logout(self):
        """Make sure logging in and logging out works"""
        rv = self.register_and_login('user1', 'default')
        assert 'You were logged in' in rv.data
        rv = self.logout()
        assert 'You were logged out' in rv.data
        rv = self.login('user1', 'wrongpassword')
        assert 'Invalid password' in rv.data
        rv = self.login('user2', 'default')
        assert 'Invalid username' in rv.data

    def test_add_message(self):
        """Check if adding messages works"""
        self.register_and_login('foo', 'default')
        rv = self.add_message('test message 1')
        assert 'test message 1' in rv.data

    def test_timelines(self):
        """Make sure that timelines work"""
        self.register_and_login('foo', 'default')
        self.add_message('the message by foo')
        self.logout()
        self.register_and_login('bar', 'default')
        self.add_message('the message by bar')
        rv = self.app.get('/public')
        assert 'the message by foo' in rv.data
        assert 'the message by bar' in rv.data

        # test bar's timeline
        rv = self.app.get('/')
        assert 'the message by foo' not in rv.data
        assert 'the message by bar' in rv.data

        # test follow function
        rv = self.app.get('/foo/follow', follow_redirects=True)
        assert 'You are now following &#34;foo&#34;' in rv.data

        rv = self.app.get('/')
        assert 'the message by foo' in rv.data
        assert 'the message by bar' in rv.data

        # test the user timeline
        rv = self.app.get('/bar')
        assert 'the message by foo' not in rv.data
        assert 'the message by bar' in rv.data
        rv = self.app.get('/foo')
        assert 'the message by foo' in rv.data
        assert 'the message by bar' not in rv.data

        # test unfollow function
        rv = self.app.get('/foo/unfollow', follow_redirects=True)
        assert 'You are no longer following &#34;foo&#34;' in rv.data
        rv = self.app.get('/')
        assert 'the message by foo' not in rv.data
        assert 'the message by bar' in rv.data


if __name__ == '__main__':
    unittest.main()
