from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, Text
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
        return db.union(
            Game.query.filter_by(first_player=self),
            Game.query.filter_by(second_player=self),
        ).all()

    @property
    def games_in_progress(self):
        return self.games.filter_by(in_progress=True)


class Game(db.Model):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True)
    in_progress = Column(Boolean, default=True)
    first_player_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    first_player = relationship('User', foreign_keys=[first_player_id])
    second_player_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    second_player = relationship('User', foreign_keys=[second_player_id])
    board_state = Column(Text)
    victor_id = Column(Integer, ForeignKey('user.id'))
    victor = relationship('User', foreign_keys=[victor_id])
