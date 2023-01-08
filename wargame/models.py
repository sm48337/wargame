from random import randint
from datetime import datetime

from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, DateTime, JSON, or_
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from .db import db
from .utils import (
    attack_result_table, current_team, opposing_team, find_attack_targets, find_transfer_targets,
    teams, vitality_recovery_cost, end_of_month, get_ends_of_months, total_vps
)


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
        return Game.query.filter(or_(Game.red_player == self, Game.blue_player == self)).all()


class Game(db.Model):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True)
    red_player_id = Column(ForeignKey('user.id'), nullable=False)
    red_player = relationship('User', foreign_keys=[red_player_id])
    blue_player_id = Column(ForeignKey('user.id'), nullable=False)
    blue_player = relationship('User', foreign_keys=[blue_player_id])
    board_state = Column(MutableDict.as_mutable(JSON))
    history = Column(MutableList.as_mutable(JSON), default=list)
    message_log = Column(MutableList.as_mutable(JSON), default=list)
    victor_id = Column(ForeignKey('user.id'), nullable=True)
    victor = relationship('User', foreign_keys=[victor_id])
    turn_start = Column(DateTime, default=datetime.now)

    def __init__(self, *args, **kwargs):
        kwargs['history'] = [kwargs['board_state']]
        super().__init__(*args, **kwargs)

    def get_current_entities(self):
        turn = self.board_state['turn']
        return self.board_state['teams'][current_team(turn)]['entities']

    def get_entity(self, entity_id):
        for team in teams:
            if entity := self.board_state['teams'][team]['entities'].get(entity_id):
                return entity

    def get_all_connections(self, entity_id, entity_team):
        entities = self.board_state['teams'][entity_team]['entities']
        entity = entities[entity_id]
        connected_entities = dict()
        for connection in entities.values():
            if connection['id'] in entity.get('connections', []):
                connected_entities[connection['id']] = connection
        for candidate in entities.values():
            if entity in candidate['connections']:
                connected_entities[candidate['id']] = candidate
        return connected_entities, entity

    def perform_checks(self, inputs):
        validation_errors = list()

        turn = self.board_state['turn']
        if turn != int(inputs['turn']):
            validation_errors.append(('The turn had already ended!', 'error'))

        if self.victor is not None:
            validation_errors.append(('The game is finished!', 'error'))

        return validation_errors

    def _do_revitalize(self, entity, inputs):
        vitality_recovered = int(inputs.get(entity['id'] + '__revitalize'))
        recovery_cost = vitality_recovery_cost[vitality_recovered]
        entity['vitality'] += vitality_recovered
        entity['resource'] -= recovery_cost
        self.message_log.append(f"{entity['name']} spent {recovery_cost} resources to gain {vitality_recovered} vitality.")

    def _entity_destroyed_check(self, entity, entity_team):
        if entity['vitality'] <= 0:
            opposing_team = teams[1 - teams.index(entity_team)]
            entities = self.board_state['teams'][opposing_team]['entities']
            gov = entities.get('uk_gov') or entities.get('rus_gov')
            gov['victory_points'] += 10
            self.determine_winner()
            self.message_log.append(f"{entity['name']} was dealt fatal damage. Opponent was awarded 10 VPs and the game ended.")

    def _do_damage(self, target_id, amount, target_team):
        connections, target = self.get_all_connections(target_id, target_team)
        target['vitality'] -= amount
        self._entity_destroyed_check(target, target_team)

        for connection in connections.values():
            connection['vitality'] -= amount // 2
            self._entity_destroyed_check(connection, target_team)
        self.message_log.append(f"{target['name']} was dealt {amount} damage. Connected entities got {amount // 2} damage.")

    def _do_attribution(self):
        ...

    def _do_attack(self, entity, inputs):
        turn = self.board_state['turn']
        for target_id, field in find_attack_targets(entity['id'], inputs):
            attack_investment = int(inputs.get(field) or 0)
            dice_roll = randint(1, 6)
            attack_success = attack_result_table[attack_investment][dice_roll]
            self.message_log.append(f"{entity['name']} spent {attack_investment} resources and rolled {dice_roll}.")

            if attack_success > 0:
                self._do_damage(target_id, attack_success, opposing_team(turn))
            elif attack_success < 0:
                self._do_damage(entity['id'], -attack_success, current_team(turn))
                self._do_attribution()

            entity['resource'] -= attack_investment
            if entity['id'] == 'trolls':
                if attack_investment >= 3:
                    vp_cost = 1 if attack_investment < 5 else 2
                    self.board_state['teams']['red']['entities']['rus_gov']['victory_points'] -= vp_cost
                    self.message_log.append(f'Control the Trolls - Russian Government lost {vp_cost} VP because Online Trolls launched a large attack.')
                    if 'ransomware' in entity['traits'].get('assets', []):
                        entity['victory_points'] += 4
                        self.message_log.append(
                            'Success breeds confidence - Online Trolls gained 4 VPs because they launched a large attack while having the Ransomware asset.'
                        )

    def _do_transfer(self, entity, inputs):
        for target_id, field in find_transfer_targets(entity['id'], inputs):
            transfer_amount = int(inputs.get(field) or 0)
            target = self.get_entity(target_id)
            target['resource'] += transfer_amount
            entity['resource'] -= transfer_amount
            if transfer_amount:
                self.message_log.append(f"{entity['name']} sent {transfer_amount} resources to {target['name']}.")
                if entity['id'] == 'elect':
                    entity['victory_points'] -= 1
                    self.message_log.append(f"Resist the drain - {entity['name']} lost 1 VP due to the transfer of resources.")

    def process_inputs(self, inputs):
        for entity in self.get_current_entities().values():
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
        entities = self.get_current_entities()
        gov_entity = entities.get('rus_gov') or entities.get('uk_gov')
        gov_entity['resource'] += 3
        self.message_log.append(f"{gov_entity['name']} gains 3 resources.")

    def progress_time(self):
        turn = self.board_state['turn']
        self.message_log.append(f'End of turn {turn // 2 + 1} for the {current_team(turn).capitalize()} team.')
        self.board_state['turn'] += 1
        self.turn_start = datetime.now()

    def determine_winner(self):
        teams = self.board_state['teams']
        red_vps = total_vps(teams['red'])
        blue_vps = total_vps(teams['blue'])
        self.victor = self.red_player if red_vps > blue_vps else self.blue_player
        self.message_log.append(f'Player {self.victor.username} won the game having {red_vps} VPs. The opponent had {blue_vps} VPs.')

    def enable_attacks(self):
        self.message_log.append('Attacks enabled.')
        for entity in self.board_state['teams']['red']['entities'].values():
            match entity['id']:
                case 'bear':
                    entity['attacks'] = ['plc']
                case 'trolls':
                    entity['attacks'] = ['elect']

    def calculate_blue_victory_points(self, turn, entities):
        if entities['elect']['resource'] >= 4:
            entities['uk_gov']['victory_points'] += 1
            self.message_log.append('Election time - UK Government gains 1 VP because a month ended with Electorate having 4 or more resources.')
        if turn == end_of_month(12) and entities['rus_gov']['vitality'] < 4:
            self.message_log.append(
                'Aggressive outlook - UK Government gains 5 VPs because the Russian Government ended the game with less vitality than it started with.'
            )
            entities['uk_gov']['victory_points'] += 5

        plc_triggers = get_ends_of_months(4, 8, 12)
        if turn in plc_triggers:
            index = plc_triggers.index(turn)
            limit = (index + 1) * 3
            amount_won = index + 2
            if entities['plc']['resource'] >= limit:
                entities['plc']['victory_points'] += amount_won
                self.message_log.append(
                    f'Weather the Brexit storm - UK PLC gains {amount_won} VP because it had more than {limit} resources at the end of the quarter.'
                )

        quarter_ends = get_ends_of_months(3, 6, 9, 12)
        if turn in quarter_ends:
            plc = entities['plc']
            rd = plc['traits']['recruitment_drive']
            if rd['vitality'] > plc['vitality']:
                amount_won = 1 + 2 * rd['count']
                plc['victory_points'] += 1 + 2 * rd['count']
                rd['count'] += 1
                self.message_log.append(f"Recruitment drive - UK PLC gains {amount_won} VP because it achieved vitality growth last {rd['count']} quarter(s).")
            else:
                rd['count'] = 0
            rd['vitality'] = plc['vitality']

        year_halves = get_ends_of_months(6, 12)
        if turn in year_halves:
            index = year_halves.index(turn)
            limit = 6 + index * 3
            if entities['energy']['vitality'] >= limit:
                amount_won = index + 2
                entities['energy']['victory_points'] += amount_won
                self.message_log.append(f'Grow capacity - UK Energy gains {amount_won} VP because has more than {limit} vitality.')

    @staticmethod
    def _count_assets(team):
        count = 0
        for entity in team['entities'].values():
            count += len(entity['traits'].get('assets', []))
        return count

    def calculate_red_victory_points(self, turn, entities):
        if entities['rus_gov']['resource'] >= 3:
            entities['rus_gov']['victory_points'] += 1
            self.message_log.append(
                'Some animals are more equal than others - Russian Government gains 1 VP because it ended the month with more than 3 resources.'
            )

        bear_triggers = get_ends_of_months(4, 8, 12)
        if turn in bear_triggers:
            bear = entities['bear']
            index = bear_triggers.index(turn)
            if bear['traits']['last_growth_vitality'] > bear['vitality']:
                amount_won = 1 + index * 2
                bear['traits']['last_growth_vitality'] = bear['vitality']
                bear['victory_points'] += amount_won
                self.message_log.append(f"Those who can't steal - Energetic Bear gains {amount_won} VP because it achieved vitality growth since last check.")

        if self._count_assets(self.board_state['teams']['blue']) < self._count_assets(self.board_state['teams']['red']):
            entities['scs']['victory_points'] += 2
            self.message_log.append('Win the arms race - SCS gains 2 VPs because Russia has a better cyber arsenal than the UK.')

        quarter_ends = get_ends_of_months(3, 6, 9, 12)
        if turn in quarter_ends:
            ros = entities['ros']
            gc = ros['traits']['grow_capacity']
            if gc['vitality'] > ros['vitality']:
                amount_won = 1 + 2 * gc['count']
                ros['victory_points'] += 1 + 2 * gc['count']
                gc['count'] += 1
                self.message_log.append(
                    f"Grow capacity - Rosenergoatom gains {amount_won} VP because it achieved vitality growth last {gc['count']} quarter(s)."
                )
            else:
                gc['count'] = 0
            gc['vitality'] = ros['vitality']

    def calculate_victory_points(self):
        turn = self.board_state['turn']
        teams = self.board_state['teams']
        entities = dict(**teams['red']['entities'], **teams['blue']['entities'])
        self.calculate_blue_victory_points(turn, entities)
        self.calculate_red_victory_points(turn, entities)

    def process_turn(self, inputs):
        self.process_inputs(inputs)
        self.progress_time()

        self.give_resources()

        turn = self.board_state['turn']
        if turn == end_of_month(1):
            self.enable_attacks()
        elif turn == end_of_month(12):
            self.determine_winner()

        # end of month
        if turn % 2 == 1:
            self.calculate_victory_points()

        self.history.append(self.board_state)
