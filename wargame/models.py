from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, JSON, or_
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from .db import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    def is_active(self):
        return self.active

    def get_id(self):
        return self.id

    def is_anonymous(self):
        return False

    def __repr__(self):
        id, username = self.id, self.username
        return f'<User {id=} {username=}>'

    @property
    def games(self):
        return Game.query.filter(or_(Game.first_player == self, Game.second_player == self)).all()


class Game(db.Model):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True)
    first_player_id = Column(ForeignKey('user.id'), nullable=False)
    first_player = relationship('User', foreign_keys=[first_player_id])
    second_player_id = Column(ForeignKey('user.id'), nullable=False)
    second_player = relationship('User', foreign_keys=[second_player_id])
    board_state = Column(MutableDict.as_mutable(JSON))
    victor_id = Column(ForeignKey('user.id'), nullable=True)
    victor = relationship('User', foreign_keys=[victor_id])
