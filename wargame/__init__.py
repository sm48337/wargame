import os
from http import HTTPStatus

from flask import Flask, abort, redirect, url_for, request
from flask_login import LoginManager, utils

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = f'sqlite:///{os.path.join(basedir, "database.db")}'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from . import api, auth, game

    app.register_blueprint(api.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(game.bp)

    app.secret_key = b'bla'

    login_manager.init_app(app)

    from .db import db
    db.init_app(app)
    with app.app_context():
        db.create_all(app=app)
        db.session.commit()

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import User
    try:
        return User.query.filter_by(id=user_id).one()
    except User.DoesNotExist:
        return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint == 'api':
        abort(HTTPStatus.UNAUTHORIZED)
    next_param = utils.make_next_param(url_for('auth.login'), request.url)
    return redirect(url_for('auth.login', next=next_param))
