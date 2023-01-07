from random import randint

from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, JSON, or_
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from .db import db
from .utils import attack_result_table, current_team, opposing_team, find_attack_targets, find_transfer_targets, teams, vitality_recovery_cost


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

    def get_current_entities(self):
        turn = self.board_state['turn']
        return self.board_state['teams'][current_team(turn)]['entities']

    def get_entity(self, entity_id):
        for team in teams:
            for entity in self.board_state['teams'][team]['entities']:
                if entity['id'] == entity_id:
                    return entity

    def get_all_connections(self, entity_id, entity_team):
        entities = self.board_state['teams'][entity_team]['entities']
        [entity] = filter(lambda e: e['id'] == entity_id, entities)
        connected_entities = dict()
        for connection in entities:
            if connection['id'] in entity['connections']:
                connected_entities[connection['id']] = connection
        for candidate in entities:
            if entity in candidate['connections']:
                connected_entities[candidate['id']] = candidate
        return connected_entities, entity

    def perform_checks(self, inputs):
        validation_errors = list()

        turn = self.board_state['turn']
        if turn != int(inputs['turn']):
            validation_errors.append(('The turn had already ended!', 'error'))

        if turn >= 23:
            validation_errors.append(('The game is finished!', 'error'))

        return validation_errors

    def _do_revitalize(self, entity, inputs):
        vitality_recovered = int(inputs.get(entity['id'] + '__revitalize'))
        recovery_cost = vitality_recovery_cost[vitality_recovered]
        entity['vitality'] += vitality_recovered
        entity['resource'] -= recovery_cost
        self.message_log.append(f"{entity['name']} spent {recovery_cost} resources to gain {vitality_recovered} vitality.")

    def _do_damage(self, target_id, amount, target_team):
        connections, target = self.get_all_connections(target_id, target_team)
        target['vitality'] -= amount
        for connection in connections:
            connection['vitality'] -= amount // 2
        self.message_log.append(f"{target['name']} was dealt {amount} damage. Connected entities got {amount // 2} damage.")

    def _do_attribution(self):
        ...

    def _do_attack(self, entity, inputs):
        turn = self.board_state['turn']
        for target_id, field in find_attack_targets(entity['id'], inputs):
            attack_investment = int(inputs.get(field))
            dice_roll = randint(1, 6)
            attack_success = attack_result_table[attack_investment][dice_roll]
            self.message_log.append(f"{entity['name']} spent {attack_investment} resources and rolled {dice_roll}.")

            if attack_success > 0:
                self._do_damage(target_id, attack_success, opposing_team(turn))
            elif attack_success < 0:
                self._do_damage(entity['id'], -attack_success, current_team(turn))
                self._do_attribution()

            entity['resource'] -= attack_investment

    def _do_transfer(self, entity, inputs):
        for target_id, field in find_transfer_targets(entity['id'], inputs):
            transfer_amount = int(inputs.get(field) or 0)
            target = self.get_entity(target_id)
            target['resource'] += transfer_amount
            entity['resource'] -= transfer_amount
            if transfer_amount:
                self.message_log.append(f"{entity['name']} sent {transfer_amount} resources to {target['name']}.")

    def process_inputs(self, inputs):
        for entity in self.get_current_entities():
            if action := inputs.get(entity['id'] + '__action'):
                match action:
                    case '' | 'none':
                        continue
                    case 'revitalize':
                        self._do_revitalize(entity, inputs)
                    case 'attack':
                        self._do_attack(entity, inputs)
                    case 'transfer':
                        self._do_transfer(entity, inputs)

    def give_resources(self):
        for entity in self.get_current_entities():
            if entity['id'].endswith('_gov'):
                entity['resource'] += 3
                self.message_log.append(f"{entity['name']} gains 3 resources.")

    def progress_time(self):
        turn = self.board_state['turn']
        self.message_log.append(f'End of turn {turn // 2 + 1} for the {current_team(turn).capitalize()} team.')
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

    def process_turn(self, inputs):
        self.process_inputs(inputs)
        self.give_resources()

        self.progress_time()

        if self.board_state['turn'] == 2:
            self.enable_attacks()
        elif self.board_state['turn'] == 23:
            self.determine_winner()

        self.history.append(self.board_state)
