from datetime import datetime, timedelta
from random import choice, randint

from flask_login.mixins import UserMixin
from sqlalchemy import Column, ForeignKey, String, Integer, Boolean, DateTime, JSON, or_
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .db import db
from .utils import (
    attack_result_table, current_team, opposing_team, find_attack_targets, find_transfer_targets,
    teams, vitality_recovery_cost, end_of_month, get_ends_of_months, total_vps, Event, Asset
)


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password)

    def is_active(self):
        return self.active

    def get_id(self):
        return self.id

    def is_anonymous(self):
        return False

    def __repr__(self):
        id, username = self.id, self.username
        return f'<User {id=} {username=}>'

    def _all_roles_query(self):
        return or_(Team.government_player == self,
                   Team.industry_player == self,
                   Team.people_player == self,
                   Team.security_player == self,
                   Team.energy_player == self)

    @property
    def games(self):
        return Game.query.join(
            Team, or_(Team.id == Game.red_team_id,
                      Team.id == Game.blue_team_id)
        ).where(self._all_roles_query()).all()


class Team(db.Model):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    government_player_id = Column(ForeignKey('user.id'), nullable=False)
    government_player = relationship('User', foreign_keys=[government_player_id])
    industry_player_id = Column(ForeignKey('user.id'), nullable=False)
    industry_player = relationship('User', foreign_keys=[industry_player_id])
    people_player_id = Column(ForeignKey('user.id'), nullable=False)
    people_player = relationship('User', foreign_keys=[people_player_id])
    security_player_id = Column(ForeignKey('user.id'), nullable=False)
    security_player = relationship('User', foreign_keys=[security_player_id])
    energy_player_id = Column(ForeignKey('user.id'), nullable=False)
    energy_player = relationship('User', foreign_keys=[energy_player_id])

    @property
    def players(self):
        return (self.government_player, self.industry_player, self.people_player, self.security_player, self.energy_player)


class Game(db.Model):
    __tablename__ = 'game'

    round_length = timedelta(minutes=3)
    unpause_delay = timedelta(seconds=5)

    id = Column(Integer, primary_key=True)
    owner_id = Column(ForeignKey('user.id'), nullable=False)
    owner = relationship('User')
    red_team_id = Column(ForeignKey('team.id'), nullable=False)
    red_team = relationship('Team', foreign_keys=[red_team_id])
    blue_team_id = Column(ForeignKey('team.id'), nullable=False)
    blue_team = relationship('Team', foreign_keys=[blue_team_id])
    victor_id = Column(ForeignKey('team.id'), nullable=True)
    victor = relationship('Team', foreign_keys=[victor_id])

    description = Column(String)
    ready_players = Column(MutableList.as_mutable(JSON), default=list)
    player_inputs = Column(MutableDict.as_mutable(JSON), default=dict)
    board_state = Column(MutableDict.as_mutable(JSON))
    history = Column(MutableList.as_mutable(JSON), default=list)
    message_log = Column(MutableList.as_mutable(JSON), default=list)
    unpause_time = Column(DateTime, default=datetime.now)
    seconds_left = Column(Integer, default=int(round_length.total_seconds()))
    is_paused = Column(Boolean, default=True)

    def __init__(self, *args, **kwargs):
        kwargs['history'] = [kwargs['board_state']]
        super().__init__(*args, **kwargs)
        self.message_log = list()
        self.give_resources()
        self.generate_bm_pool()
        self.get_new_bm_asset()
        self.process_event()

    def toggle_pause(self):
        if self.is_starting:
            return

        if self.is_paused:
            self.unpause_time = datetime.now() + self.unpause_delay
        else:
            difference = (datetime.now() - self.unpause_time)
            self.seconds_left -= int(difference.total_seconds())
        self.is_paused = not self.is_paused

    def get_current_entities(self):
        turn = self.board_state['turn']
        return self.board_state['teams'][current_team(turn)]['entities']

    def get_entity(self, entity_id):
        for team in teams:
            if entity := self.board_state['teams'][team]['entities'].get(entity_id):
                return entity

    def log(self, message, category):
        self.message_log.append((message, category))

    def time_left(self):
        if self.is_paused:
            return self.seconds_left
        difference = self.unpause_time + timedelta(seconds=self.seconds_left) - datetime.now()
        return int(difference.total_seconds())

    @property
    def is_starting(self):
        return self.starting_delay > 0

    @property
    def starting_delay(self):
        time_delay = self.unpause_time - datetime.now()
        return time_delay.total_seconds()

    def ready_player(self, player):
        if player.username not in self.ready_players:
            self.ready_players.append(player.username)

    @property
    def current_team(self):
        team_color = current_team(self.board_state['turn'])
        return getattr(self, team_color + '_team')

    def all_players_ready(self):
        return set(map(lambda p: p.username, self.current_team.players)) == set(self.ready_players)

    def get_all_connections(self, entity_id, entity_team):
        entities = self.board_state['teams'][entity_team]['entities']
        entity = entities[entity_id]
        connected_entities = dict()
        for connection in entities.values():
            if connection['id'] in entity.get('connections', []):
                connected_entities[connection['id']] = connection
        for candidate in entities.values():
            if entity in candidate.get('connections', []):
                connected_entities[candidate['id']] = candidate
        return connected_entities, entity

    def perform_checks(self, inputs, player):
        validation_errors = list()

        turn = self.board_state['turn']
        if turn != int(inputs['turn']):
            validation_errors.append(('The turn had already ended!', 'error'))

        if self.victor is not None:
            validation_errors.append(('The game is finished!', 'error'))

        if player.username in self.ready_players:
            validation_errors.append(('You already finished your turn - waiting for other players.', 'error'))

        if player not in self.current_team.players:
            validation_errors.append(('It is not your turn now, wait for your opponents to finish.', 'error'))

        return validation_errors

    def _do_revitalize(self, entity):
        vitality_recovered = int(self.player_inputs.get(entity['id'] + '__revitalize') or 0)
        recovery_cost = vitality_recovery_cost[vitality_recovered]
        entity['vitality'] += vitality_recovered
        entity['resource'] -= recovery_cost
        self.log(f"{entity['name']} spent {recovery_cost} resources to gain {vitality_recovered} vitality.", 'action')

    def check_health(self):
        govs = {
            'red': self.board_state['teams']['red']['entities']['rus_gov'],
            'blue': self.board_state['teams']['blue']['entities']['uk_gov'],
        }
        fatalities = False
        for team, other_team in zip(teams, reversed(teams)):
            for entity in self.board_state['teams'][team]['entities'].values():
                if entity['vitality'] > 0:
                    continue
                fatalities = True
                govs[other_team]['victory_points'] += 10
                self.log(f"{entity['name']} was dealt fatal damage. Opponent was awarded 10 VPs.", 'important')

        if fatalities:
            self.determine_winner()
        return fatalities

    def _do_damage(self, target_id, amount, target_team):
        connections, target = self.get_all_connections(target_id, target_team)

        direct_amount = amount
        if target['traits'].get('software_update'):
            direct_amount = 0
        if target['traits'].get('stuxnet'):
            direct_amount *= 2
        if target['traits'].get('education') or target['traits'].get('bargaining_chip'):
            direct_amount //= 2
        if target['traits'].get('ransomware'):
            target['traits']['paralyzed'] = 3

        target['vitality'] -= direct_amount

        for connection in connections.values():
            if connection['traits'].get('education'):
                connection['vitality'] -= amount // 4
            elif connection['traits'].get('network_policy'):
                pass
            else:
                connection['vitality'] -= amount // 2
        self.log(f"{target['name']} was dealt {amount} damage. Connected entities got {amount // 2} damage.", 'action')

    def _do_attribution(self, attacker, level):
        if attacker == 'bear':
            self.board_state['teams']['blue']['assets'].append('software_update')
            if level == -2:
                self.board_state['teams']['blue']['assets'].append('recovery')
        elif attacker == 'trolls':
            self.board_state['teams']['blue']['assets'].append('education')
            if level == -2:
                self.board_state['teams']['red']['trolls']['traits']['cannot_attack'] = 2
        elif attacker == 'scs':
            self.board_state['teams']['blue']['assets'].append('software_update')
            self.board_state['teams']['red']['scs']['traits']['cannot_bit'] = 2
            if level == -2:
                self.board_state['teams']['blue']['assets'].append('attack_vector')
        elif attacker == 'gchq':
            self.board_state['teams']['blue']['gchq']['traits']['cannot_attack'] = 2
            if level == -2:
                self.board_state['teams']['blue']['gchq']['traits']['cannot_perform_actions'] = 2
                self.board_state['teams']['blue']['uk_gov']['vitality'] -= 1
        elif attacker == 'uk_gov':
            self.board_state['teams']['red']['assets'].append('bargaining_chip')
            if level == -2:
                self.board_state['teams']['blue']['uk_gov']['resource'] -= 2
                self.board_state['teams']['blue']['uk_gov']['vitality'] -= 2

    def _do_attack(self, entity):
        turn = self.board_state['turn']
        for target_id, field in find_attack_targets(entity['id'], self.player_inputs):
            attack_investment = int(self.player_inputs.get(field) or 0)
            dice_roll = randint(1, 6)
            attack_success = attack_result_table[attack_investment][dice_roll]
            self.log(f"{entity['name']} spent {attack_investment} resources and rolled {dice_roll}.", 'action')

            if attack_success > 0:
                self._do_damage(target_id, attack_success, opposing_team(turn))
            elif attack_success < 0:
                self._do_damage(entity['id'], -attack_success, current_team(turn))
                self._do_attribution(entity['id'], -attack_success)

            entity['resource'] -= attack_investment
            if entity['id'] == 'trolls':
                if attack_investment >= 3:
                    vp_cost = 1 if attack_investment < 5 else 2
                    self.board_state['teams']['red']['entities']['rus_gov']['victory_points'] -= vp_cost
                    self.log(f'Control the Trolls - Russian Government lost {vp_cost} VP because Online Trolls launched a large attack.', 'victory-point')
                    if 'ransomware' in entity['traits'].get('assets', []):
                        entity['victory_points'] += 4
                        self.log('Success breeds confidence - Online Trolls gained 4 VPs because they launched a large attack '
                                 'while having the Ransomware asset.', 'victory-point')

    def _do_transfer(self, entity):
        for target_id, field in find_transfer_targets(entity['id'], self.player_inputs):
            transfer_amount = int(self.player_inputs.get(field) or 0)
            target = self.get_entity(target_id)
            target['resource'] += transfer_amount
            entity['resource'] -= transfer_amount
            if transfer_amount:
                self.log(f"{entity['name']} sent {transfer_amount} resources to {target['name']}.", 'action')
                if entity['id'] == 'elect':
                    entity['victory_points'] -= 1
                    self.log(f"Resist the drain - {entity['name']} lost 1 VP due to the transfer of resources.", 'victory-point')

    def process_inputs(self):
        teams = self.board_state['teams']
        turn = self.board_state['turn']
        team = teams[current_team(turn)]
        asset = Asset(self.board_state)
        if activated_assets := self.player_inputs.get('activated-assets'):
            activated_asset_ids = map(int, activated_assets.split(', '))
            used_assets = list()
            for index in activated_asset_ids:
                asset_id = team['assets'][index]
                asset.resolve(asset_id, self.player_inputs.get('option-' + str(index), ''))
                activated_asset = Asset.assets[asset_id]
                self.log(f'Team {current_team(turn).capitalize()} activated asset {activated_asset[0]} - {activated_asset[2]}.', 'action')
                used_assets.append(index)

            used_assets.sort(reverse=True)
            for index in used_assets:
                del team['assets'][index]

        bm_changes = {
            'remove': [],
            'bid': [],
        }
        for index, bm_item in enumerate(self.board_state['black_market']):
            asset, old_bid = bm_item
            bid = int(self.player_inputs.get(f'bm-bid-{index}') or 0)
            if current_team(turn) == 'red':
                team['entities']['scs']['resource'] -= bid
            else:
                team['entities']['gchq']['resource'] -= bid
            asset_name = Asset.assets[asset][0]
            if old_bid and not bid:
                self.log(f"Team {opposing_team(turn).capitalize()}'s bid for {asset_name} was not contested - asset gained.", 'action')
                self.board_state['teams'][opposing_team(turn)]['assets'].append(asset)
                bm_changes['remove'].append(index)
            elif bid:
                self.log(f'Team {current_team(turn).capitalize()} bid {bid} for {asset_name}.', 'action')
                self.board_state['black_market'][index] = asset, bid
                bm_changes['bid'].append((index, bid))

        for index, bid in bm_changes['bid']:
            asset = self.board_state['black_market'][index][0]
            self.board_state['black_market'][index] = asset, bid

        for removed_index in reversed(bm_changes['remove']):
            del self.board_state['black_market'][removed_index]

        for entity in self.get_current_entities().values():
            if action := self.player_inputs.get(entity['id'] + '__action'):
                match action:
                    case '' | 'none':
                        pass
                    case 'revitalize':
                        self._do_revitalize(entity)
                    case 'attack':
                        self._do_attack(entity)
                    case 'transfer':
                        self._do_transfer(entity)

            if entity['id'] == 'uk_gov' and entity['traits'].get('banking_error'):
                entity['traits']['banking_error'] = False

            if entity['id'] == 'scs' and entity['traits'].get('embargoed'):
                entity['traits']['embargoed'] = False

        for t, e, trait in (
                ('blue', 'elect', 'education'), ('red', 'rus_gov', 'bargaining_chip'),
                ('blue', 'plc', 'software_update'), ('blue', 'energy', 'software_update'), ('red', 'ros', 'software_update'),
                ):
            entity = teams[t]['entities'][e]
            if entity['traits'].get(trait):
                entity['traits'][trait] -= 1

        plc = teams['blue']['entities']['plc']
        if recovery := plc['traits'].get('recovery'):
            if plc['vitality'] < recovery:
                plc['vitality'] += 1
            plc['traits']['recovery'] = plc['vitality']

        for t, e in ('blue', 'energy'), ('red', 'ros'):
            entity = teams[t]['entities'][e]
            if entity['traits'].get('stuxnet'):
                entity['traits']['stuxnet'] = False

        for e in 'plc', 'elect':
            entity = teams['blue']['entities'][e]
            if entity['traits'].get('ransomware'):
                entity['traits']['ransomware'] = False
            if entity['traits'].get('paralyzed'):
                entity['traits']['paralyzed'] -= 1

    def give_resources(self):
        entities = self.get_current_entities()
        if entities.get('rus_gov', {}).get('traits', {}).get('people_revolt'):
            rus_gov = entities['rus_gov']
            rus_gov['traits']['people_revolt'] = False
            self.log(f"Turn starts - {rus_gov['name']} gains no resources because of the People's revolt effect.", 'event')
            return
        gov_entity = entities.get('rus_gov') or entities.get('uk_gov')
        gov_entity['resource'] += 3
        self.log(f"Turn starts - {gov_entity['name']} gains 3 resources.", 'turn')

    def progress_time(self, game_over):
        turn = self.board_state['turn']
        if not game_over:
            self.log(f'End of turn {turn // 2 + 1} for the {current_team(turn).capitalize()} team.', 'turn')
        self.board_state['turn'] += 1
        self.unpause_time = datetime.now()
        self.seconds_left = int(self.round_length.total_seconds())

    def determine_winner(self):
        teams = self.board_state['teams']
        red_vps = total_vps(teams['red'])
        blue_vps = total_vps(teams['blue'])
        self.victor = self.red_team if red_vps > blue_vps else self.blue_team
        self.log(f'Team {self.victor.name} won the game having {red_vps} VPs. The opposing team had {blue_vps} VPs.', 'important')

    def enable_attacks(self):
        self.log('Attacks enabled.', 'turn')
        for entity in self.board_state['teams']['red']['entities'].values():
            match entity['id']:
                case 'bear':
                    entity['attacks'] = ['plc']
                case 'trolls':
                    entity['attacks'] = ['elect']

    def calculate_blue_victory_points(self, turn, entities):
        if entities['elect']['resource'] >= 4:
            entities['uk_gov']['victory_points'] += 1
            self.log('Election time - UK Government gains 1 VP because a month ended with Electorate having 4 or more resources.', 'victory-point')
        if turn == end_of_month(12) and entities['rus_gov']['vitality'] < 4:
            self.log('Aggressive outlook - UK Government gains 5 VPs because the Russian Government '
                     'ended the game with less vitality than it started with.', 'victory-point')
            entities['uk_gov']['victory_points'] += 5

        plc_triggers = get_ends_of_months(4, 8, 12)
        if turn in plc_triggers:
            index = plc_triggers.index(turn)
            limit = (index + 1) * 3
            amount_won = index + 2
            if entities['plc']['resource'] >= limit:
                entities['plc']['victory_points'] += amount_won
                self.log(f'Weather the Brexit storm - UK PLC gains {amount_won} VP because it had '
                         f'more than {limit} resources at the end of the quarter.', 'victory-point')

        quarter_ends = get_ends_of_months(3, 6, 9, 12)
        if turn in quarter_ends:
            plc = entities['plc']
            rd = plc['traits']['recruitment_drive']
            if rd['vitality'] > plc['vitality']:
                amount_won = 1 + 2 * rd['count']
                plc['victory_points'] += 1 + 2 * rd['count']
                rd['count'] += 1
                self.log(f"Recruitment drive - UK PLC gains {amount_won} VP because it achieved vitality growth last {rd['count']} quarter(s).", 'victory-point')
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
                self.log(f'Grow capacity - UK Energy gains {amount_won} VP because has more than {limit} vitality.', 'victory-point')

    @staticmethod
    def _count_assets_of_type(assets, asset_type):
        return len(list(filter(lambda a: a[1] == asset_type, Asset.get_assets(assets))))

    def calculate_red_victory_points(self, turn, entities):
        if entities['rus_gov']['resource'] >= 3:
            entities['rus_gov']['victory_points'] += 1
            self.log('Some animals are more equal than others - Russian Government gains 1 VP '
                     'because it ended the month with more than 3 resources.', 'victory-point')

        bear_triggers = get_ends_of_months(4, 8, 12)
        if turn in bear_triggers:
            bear = entities['bear']
            index = bear_triggers.index(turn)
            if bear['traits']['last_growth_vitality'] > bear['vitality']:
                amount_won = 1 + index * 2
                bear['traits']['last_growth_vitality'] = bear['vitality']
                bear['victory_points'] += amount_won
                self.log(f"Those who can't steal - Energetic Bear gains {amount_won} VP because it achieved vitality growth since last check.", 'victory-point')

        if self._count_assets_of_type(self.board_state['teams']['blue']['assets'], 'defence') < self._count_assets_of_type(self.board_state['teams']['red']['assets'], 'attack'):
            entities['scs']['victory_points'] += 2
            self.log('Win the arms race - SCS gains 2 VPs because Russia has a better cyber arsenal than the UK.', 'victory-point')

        quarter_ends = get_ends_of_months(3, 6, 9, 12)
        if turn in quarter_ends:
            ros = entities['ros']
            gc = ros['traits']['grow_capacity']
            if gc['vitality'] > ros['vitality']:
                amount_won = 1 + 2 * gc['count']
                ros['victory_points'] += 1 + 2 * gc['count']
                gc['count'] += 1
                self.log(f"Grow capacity - Rosenergoatom gains {amount_won} VP because "
                         "it achieved vitality growth last {gc['count']} quarter(s).", 'victory-point')
            else:
                gc['count'] = 0
            gc['vitality'] = ros['vitality']

    def generate_bm_pool(self):
        pool = list()
        for k, v in Asset.assets.items():
            pool.extend([k] * v[-1])
        self.board_state['black_market_pool'] = pool

    def get_new_bm_asset(self):
        new_asset = choice(self.board_state['black_market_pool'])
        self.board_state['black_market_pool'].remove(new_asset)
        self.board_state['black_market'].append((new_asset, 0))

    def calculate_victory_points(self):
        turn = self.board_state['turn']
        teams = self.board_state['teams']
        entities = dict(**teams['red']['entities'], **teams['blue']['entities'])
        self.calculate_blue_victory_points(turn, entities)
        self.calculate_red_victory_points(turn, entities)

    def process_turn(self, inputs, timeout=False):
        self.player_inputs.update(inputs)

        if not timeout and not self.all_players_ready():
            return

        self.process_inputs()
        game_over = self.check_health()
        self.progress_time(game_over)
        self.board_state['teams']['blue']['assets'].append('attack_vector')

        if not self.victor:
            self.give_resources()

            turn = self.board_state['turn']
            if turn == end_of_month(1):
                self.enable_attacks()
            elif turn == end_of_month(12):
                self.determine_winner()

            # end of month
            if turn % 2 == 1:
                self.calculate_victory_points()
            else:
                self.process_event()
                self.get_new_bm_asset()

        self.ready_players.clear()
        self.player_inputs.clear()

        self.history.append(self.board_state)

    def process_event(self):
        event = Event(self.board_state)
        description = event.handle()
        self.log(description, 'event')
