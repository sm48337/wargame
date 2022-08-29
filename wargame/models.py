from flask_login.mixins import UserMixin
from .db import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    authenticated = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    def is_active(self):
        return self.active

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return self.authenticated

    def is_anonymous(self):
        return False
