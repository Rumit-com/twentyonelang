import flask
import hashlib
import hmac
import secrets
from flask_socketio import SocketIO
from flask_socketio import emit
from runners import split_by_not_in_blocks_or_strings
app = flask.Flask(__name__)
socketio = SocketIO(app, manage_session=True)


def verify_password(password: str, stored: str) -> bool:
    """
    Docstring для verify_password

    :param password: password you want to check
    :type password: str
    :param stored: stored hash:salt
    :type stored: str
    :return: do passwords match
    :rtype: bool
    """
    salt_hex, key_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    stored_key = bytes.fromhex(key_hex)

    new_key = hashlib.pbkdf2_hmac("sha256",
                                  password.encode("utf-8"),
                                  salt,
                                  200_000)
    return hmac.compare_digest(new_key, stored_key)


def hash_password(password: str) -> str:
    """
    Docstring для hash_password

    :param password: password you want to hash
    :type password: str
    :return: hash
    :rtype: str
    """
    salt = secrets.token_bytes(16)  # random salt
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000,  # iterations (slow = good)
    )
    return salt.hex() + ":" + key.hex()


class Server:
    """Server class for managing a multi-user web-based IDE environment with authentication and sandboxed code execution.

    This class handles user authentication, session management, and isolated code execution environments
    for each connected user through a Flask web application with WebSocket support.

    Attributes:
        env_cls: Environment class used to create isolated execution sandboxes for each user
        runner_cls: Runner class used to execute code strings within an environment
        users_to_pass_hashes (dict): Mapping of usernames to hashed passwords for authentication
        sandboxes (dict): Mapping of usernames to their respective isolated execution environments"""
    def __init__(self, env_cls, rcls):
        self.env_cls = env_cls
        self.runner_cls = rcls
        self.users_to_pass_hashes = {}
        self.sandboxes = {}

    def init_server(self, auth_template, ide_template):
        """
        Initialize the Flask server with authentication and IDE routes.
        Sets up the following routes:
        - GET /auth: Displays the authentication page
        - GET/POST /auth/done: Handles user authentication logic with user registration and validation
        - GET /: Home page that serves the IDE template (requires authentication)
        - WebSocket on("run_code"): Handles code execution requests from authenticated clients
        :param auth_template: Path to the authentication template file
        :type auth_template: str
        :param ide_template: Path to the IDE template file
        :type ide_template: str
        """
        @app.route("/auth")
        def auth():
            """
            Docstring для auth
            later it redirects to /auth/done where the logic is done and this is just the main auth page
            """
            return flask.render_template(auth_template)

        @app.route("/auth/done", methods=["GET", "POST"])
        def authdone():
            """
            Docstring для authdone
            auth logic
            :return: where to redirect
            :rtype: Response
            """
            if flask.request.method == "POST":
                username = flask.request.form.get("user").strip()
                password = flask.request.form.get("pass")
                if username not in self.users_to_pass_hashes or (
                    username in self.users_to_pass_hashes
                    and verify_password(password, self.users_to_pass_hashes[username])
                    and username
                    and password.strip()
                ):
                    if username not in self.users_to_pass_hashes:
                        self.users_to_pass_hashes.setdefault(username, hash_password(password))
                        self.sandboxes.setdefault(username, self.env_cls())
                    flask.session["user"] = username
                    return flask.redirect("/")
                return flask.redirect("/auth")
            return flask.redirect("/auth")

        @app.route("/")
        def home():
            """
            home page
            """
            if "user" not in flask.session:
                return flask.redirect("/auth")

            if flask.session['user'] not in self.sandboxes:
                self.sandboxes[flask.session['user']] = self.env_cls()

            return flask.render_template(ide_template, user=flask.session["user"])

        @socketio.on("run_code")
        def handle_client_message(data):
            """
            Docstring для handle_client_message

            :param data: clients command
            :return: is it ok?
            :rtype: Literal[False] | None
            """
            if "user" not in flask.session:
                return False
            if not isinstance(data["text"], str):
                emit("server", "Error: input must be a string")
                self.sandboxes[flask.session["user"]].output("Error: input must be a string")
                return False
            emit("clear", "")
            envir=self.sandboxes[flask.session["user"]]
            for i in split_by_not_in_blocks_or_strings(data["text"], "\n"):
                self.runner_cls.from_string(i, envir).run()
            return True

    def run(self, host: str, port: int):
        """Runs server as a flask application"""
        app.run(host, port)
