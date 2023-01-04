from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, JSON, or_
from sqlalchemy.ext.mutable import MutableDict, MutableList
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
    history = Column(MutableList.as_mutable(JSON), default=list)
    message_log = Column(MutableList.as_mutable(JSON), default=list)
    victor_id = Column(ForeignKey('user.id'), nullable=True)
    victor = relationship('User', foreign_keys=[victor_id])

    def __init__(self, *args, **kwargs):
        kwargs['history'] = [kwargs['board_state']]
        super().__init__(*args, **kwargs)

    def perform_checks(self, inputs):
        validation_errors = list()

        if self.board_state['turn'] != int(inputs['turn']):
            validation_errors.append(('The turn had already ended!', 'error'))

        if self.board_state['turn'] >= 12:
            validation_errors.append(('The game is finished!', 'error'))

        return validation_errors

    def process_inputs(game, inputs):
        ...

    def progress_time(self):
        self.message_log.append(f"End of turn {self.board_state['turn']}.")
        self.board_state['turn'] += 1

    def determine_winner(self):
        self.victor = self.first_player
        self.message_log.append(f'Player {self.victor.username} won the game.')

    def enable_attacks(self):
        self.message_log.append('Attacks enabled.')
        for entity in self.board_state['teams']['red']['entities']:
            match entity['id']:
                case 'bear':
                    entity['attacks'] = ['plc']
                case 'trolls':
                    entity['attacks'] = ['elect']

    def all_players_ready(self):
        return True

    def process_turn(self, inputs):
        self.process_inputs(inputs)

        if self.all_players_ready():
            self.progress_time()

            if self.board_state['turn'] == 2:
                self.enable_attacks()
            elif self.board_state['turn'] == 12:
                self.determine_winner()

            self.history.append(self.board_state)
