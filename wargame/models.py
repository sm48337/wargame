from enum import Enum, auto
from itertools import chain

from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import select
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
        user_teams = Team.query.filter(Team.players.any(User.id == self.id))
        query = db.union(
            Game.query.filter(Game.first_team.has(user_teams)),
            Game.query.filter(Game.second_team.has(user_teams)),
        )
        return chain.from_iterable(db.session.execute(select(Game).from_statement(query)).all())


class TeamRoles(Enum):
    GOVERNMENT = auto()
    PEOPLE = auto()
    BUSINESS = auto()
    INFRASTRUCTURE = auto()
    MILITARY = auto()


class UserRole(db.Model):
    __tablename__ = 'user_role',
    user_id = Column(ForeignKey('user.id'), primary_key=True)
    team_id = Column(ForeignKey('team.id'), primary_key=True)
    role = Column(SQLEnum(TeamRoles), primary_key=True)


class Team(db.Model):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True)
    players = relationship('UserRole', lazy='joined')


class Game(db.Model):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True)
    first_team_id = Column(ForeignKey('team.id'), nullable=False)
    first_team = relationship('Team', foreign_keys=[first_team_id])
    second_team_id = Column(ForeignKey('team.id'), nullable=False)
    second_team = relationship('Team', foreign_keys=[second_team_id])
    board_state = Column(JSON)
    victor_id = Column(ForeignKey('team.id'), nullable=True)
    victor = relationship('Team', foreign_keys=[victor_id])
