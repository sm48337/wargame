import os
from http import HTTPStatus
from secrets import token_hex

from flask import Flask, abort, redirect, url_for, request
from flask_login import LoginManager, utils as flask_utils

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = f'sqlite:///{os.path.join(basedir, "database.db")}'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from . import api, auth, game, utils

    app.register_blueprint(api.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(game.bp)

    app.secret_key = get_or_create_secret_key(os.path.join(basedir, 'secret_key'))

    login_manager.init_app(app)

    from .db import db
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.commit()

    app.context_processor(utils.helper_functions)

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.filter_by(id=user_id).one_or_none()


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint == 'api':
        abort(HTTPStatus.UNAUTHORIZED)
    next_param = flask_utils.make_next_param(url_for('auth.login'), request.url)
    return redirect(url_for('auth.login', next=next_param))


def get_or_create_secret_key(path):
    if not os.path.exists(path):
        secret_key = token_hex(32).encode()
        with open(path, 'wb') as f:
            f.write(secret_key)
    else:
        with open(path, 'rb') as f:
            secret_key = f.read()
    return secret_key
