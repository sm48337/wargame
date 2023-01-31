from datetime import timedelta
from functools import cache
from itertools import chain
from json import load
from random import choice
from re import match


class Event:

    descriptions = {
        "uneventful_month":     "Uneventful Month - Nothing out of the ordinary happens this month, continue playing.",
        "nuclear_meltdown":     "Nuclear Meltdown - Hinkley Point nuclear generator suffers a small but significant technical fault. "
                                "Uk Energy loses 1 vitality.",
        "clumsy_civil_servant": "Clumsy Civil Servant - A Civil Servant leaves a laptop with sensitive data on a train. "
                                "Electorate loses 1 vitality. UK Government loses 2 resource.",
        "software_update":      "Software Update - Government mandates that all companies must have the latest operating system. "
                                "UK PLC loses 2 resource.",
        "banking_error":        "Banking Error - A rounding error in the Bank of England computer system cripples transfer protocols. "
                                "UK cannot transfer any resources this month.",
        "embargoed":            "Embargoed - Russian foreign policy adventurism results in an international arms embargo. "
                                "SCS cannot bid on or receive Black Market items this month.",
        "lax_opsec":            "Lax OpSec - An Interior Ministry worker plugs in an unsanitised USB stick. "
                                "Russia Government loses 1 vitality and 1 resource.",
        "people_revolt":        "People's Revolt - People take to the streets to protest against Internet censorship. "
                                "Russia does not gain any resource this month.",
        "quantum_breakthrough": "Quantum Breakthrough - Google rolls out quantum computing across its services and devices. "
                                "ALL entities gain 1 resource and 1 vitality.",
    }

    def __init__(self, board_state):
        teams = board_state['teams']
        self.red_team = teams['red']['entities']
        self.blue_team = teams['blue']['entities']

    @staticmethod
    def events():
        return (*("uneventful_month",) * 8, "nuclear_meltdown", "clumsy_civil_servant", "software_update",
                "banking_error", "embargoed", "lax_opsec", "people_revolt", "quantum_breakthrough")

    def uneventful_month(self):
        pass

    def nuclear_meltdown(self):
        self.blue_team['energy']['vitality'] -= 1

    def clumsy_civil_servant(self):
        self.blue_team['elect']['vitality'] -= 1
        self.blue_team['uk_gov']['resource'] -= 2

    def software_update(self):
        self.blue_team['plc']['resource'] -= 2

    def banking_error(self):
        self.blue_team['uk_gov']['traits']['banking_error'] = True

    def embargoed(self):
        self.red_team['scs']['traits']['embargoed'] = True

    def lax_opsec(self):
        self.red_team['rus_gov']['vitality'] -= 1
        self.red_team['rus_gov']['resource'] -= 1

    def people_revolt(self):
        self.red_team['rus_gov']['traits']['people_revolt'] = True

    def quantum_breakthrough(self):
        for entity in chain(self.red_team.values(), self.blue_team.values()):
            entity['resource'] += 1
            entity['vitality'] += 1

    def handle(self):
        event = choice(self.events())
        getattr(self, event)()
        return self.descriptions[event]


@cache
def get_initial_board_state():
    with open('wargame/static/initial_state.json') as f:
        state = load(f)
        return state


def find_attack_targets(attacker, form):
    for field in form:
        if m := match(attacker + r'-([^-]+)__attack', field):
            yield m.groups()[0], field


def find_transfer_targets(source, form):
    for field in form:
        if m := match(source + r'-([^-]+)__transfer', field):
            yield m.groups()[0], field


attack_result_table = (
    (0, 0, 0, 0, 0, 0, 0),
    (0, 0, 1, 1, 1, 1, 2),
    (0, 0, 1, 1, 1, 2, 2),
    (0, -1, 0, 1, 2, 2, 3),
    (0, -1, 0, 1, 2, 3, 4),
    (0, -2, -1, 2, 3, 3, 4),
    (0, -2, -1, 0, 3, 5, 6),
)

months = (
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
)

teams = ('red', 'blue')

vitality_recovery_cost = [0, 1, 2, 4, 5, 6, 7]

# Ordered by type
entity_ids_by_team = {
    'red': ('rus_gov', 'bear', 'trolls', 'scs', 'ros'),
    'blue': ('uk_gov', 'plc', 'elect', 'gchq', 'energy'),
}

entity_types = (
    'government', 'industry', 'people', 'security', 'energy'
)

entity_id_to_name_map = {
    'bear': 'Energetic Bear',
    'ros': 'Rosenergoatom',
    'rus_gov': 'Russian Government',
    'scs': 'SCS',
    'trolls': 'Online Trolls',
    'elect': 'Electorate',
    'energy': 'UK Energy',
    'gchq': 'GCHQ',
    'plc': 'UK PLC',
    'uk_gov': 'UK Government',
}


def display_name(entity_id):
    return entity_id_to_name_map[entity_id]


def calculate_max_revitalization(available_resources):
    vitality_max_resource_cost = [0, 1, 2, 2, 4, 5, 6]
    if available_resources >= len(vitality_max_resource_cost):
        return vitality_max_resource_cost[-1]
    return vitality_max_resource_cost[available_resources]


def current_team(turn):
    return teams[turn % 2]


def opposing_team(turn):
    return teams[1 - turn % 2]


def end_of_month(month):
    return 2 * month - 1


def get_ends_of_months(*args):
    return tuple(map(end_of_month, args))


def turn_to_month(turn):
    month = turn // 2
    if month >= len(months):
        return 'Game Over'
    return f"{months[month]} / {current_team(turn).capitalize()} team's turn"


def total_vps(team):
    vps = 0
    for entity in team['entities'].values():
        vps += entity['victory_points']
    return vps


def turn_end(turn_start):
    return turn_start + timedelta(minutes=3)


def waiting_for_move(context, current_user):
    return context.board_state['turn'] % 2 == 0 and current_user in context.red_team.players


entity_type_mapping = {
    'uk_gov': 'government',
    'rus_gov': 'government',
    'plc': 'industry',
    'bear': 'industry',
    'scs': 'security',
    'gchq': 'security',
    'trolls': 'people',
    'elect': 'people',
    'energy': 'energy',
    'ros': 'energy',
}


class Asset:

    assets = {
        "attack_vector":    ('Attack Vector', 'attack', "Opens up one of the following attack vectors: GCHQ - Rosenergoatom, SCS - UK Energy, UK Government - Russia Government.",
                             ('gchq', 'scs', 'uk_gov')),
        "education":        ('Education', 'defensive', "Electorate suffers only half of any damage it receives for the next 3 turns.", ()),
        "recovery":         ('Recovery Management', 'defensive', "At the end of a turn, if UK PLC has sufferred any damage, they receive +1 vitality.", ()),
        "software_update":  ('Software Update', 'defensive', "Renders UK PLC or UK Energy or Rosenergoatom immune to direct attack for 2 turns.", ('plc', 'energy', 'ros')),
        "bargaining_chip":  ('Bargaining Chip', 'defensive', "Russia Government suffers only half of any damage it receives for the next 3 turns.", ()),
        "network_policy":   ('Network Policy', 'defensive', "Renders entity immune from splash damage, but only 2 resource can be transferred to or from it each turn.",
                             (entity_id_to_name_map.keys())),
        "stuxnet":          ('Stuxnet 2.0', 'attack', "Direct attack from GCHQ/SCS deals double damage to UK Energy or Rosenergoatom.", ('gchq', 'scs')),
        "ransomware":       ('Ransomware', 'attack', "When part of successful direct attack, paralyses UK PLC or Electorate for 2 turns unless 2 resource is paid to attacker.",
                             ('plc', 'elect')),
        "cyber_investment": ('Cyber Investment Programme', 'defensive', "Entity may regenerate vitality at 1 less resource cost than normal.", (entity_id_to_name_map.keys())),
    }

    def __init__(self, board_state):
        teams = board_state['teams']
        self.red_team = teams['red']['entities']
        self.blue_team = teams['blue']['entities']

    @classmethod
    def get_assets(cls, asset_ids):
        for asset_id in asset_ids:
            yield cls.assets[asset_id]

    def attack_vector(self, option):
        if option == 0:
            self.blue_team['gchq']['attacks'] = ['ros']
        elif option == 1:
            self.red_team['scs']['attacks'] = ['energy']
        elif option == 2:
            self.blue_team['uk_gov']['attacks'] = ['rus_gov']

    def education(self, _):
        self.blue_team['elect']['traits']['education'] = 3

    def recovery(self, _):
        self.blue_team['plc']['traits']['recovery'] = self.blue_team['plc']['vitality']

    def software_update(self, option):
        if option == 0:
            self.blue_team['plc']['traits']['software_update'] = 2
        elif option == 1:
            self.blue_team['energy']['traits']['software_update'] = 2
        elif option == 2:
            self.red_team['ros']['traits']['software_update'] = 2

    def bargaining_chip(self, _):
        self.red_team['rus_gov']['traits']['bargaining_chip'] = 3

    def network_policy(self, option):
        for entity in chain(self.red_team.values(), self.blue_team.values()):
            if entity == option:
                entity['traits']['network_policy'] = True
                break

    def stuxnet(self, option):
        if option == 0:
            self.red_team['ros']['traits']['stuxnet'] = True
        elif option == 1:
            self.blue_team['energy']['traits']['stuxnet'] = True

    def ransomware(self, option):
        for entity in self.blue_team.values():
            if entity == option:
                entity['traits']['ransomware'] = True
                break

    def cyber_investment(self, option):
        for entity in chain(self.red_team.values(), self.blue_team.values()):
            if entity == option:
                entity['traits']['cyber_investment'] = True
                break

    def resolve(self, asset_id, option=None):
        getattr(self, asset_id)(option)


def entity_controller(team, entity):
    entity_type = entity_type_mapping[entity]
    return getattr(team, entity_type + '_player')


def get_player_team(current_user, game):
    return 'red' if current_user in game.red_team.players else 'blue'


def helper_functions():
    return dict(
        turn_to_month=turn_to_month,
        current_team=current_team,
        vitality_recovery_cost=vitality_recovery_cost,
        calculate_max_revitalization=calculate_max_revitalization,
        display_name=display_name,
        total_vps=total_vps,
        turn_end=turn_end,
        waiting_for_move=waiting_for_move,
        teams=teams,
        entity_ids_by_team=entity_ids_by_team,
        entity_controller=entity_controller,
        get_assets=Asset.get_assets,
        get_player_team=get_player_team,
    )
