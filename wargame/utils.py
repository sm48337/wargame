from functools import cache
from json import load
from re import match


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


def turn_to_month(turn):
    return f"{months[turn // 2]} / {current_team(turn).capitalize()} team's turn"


def helper_functions():
    return dict(
        turn_to_month=turn_to_month,
        current_team=current_team,
        vitality_recovery_cost=vitality_recovery_cost,
        calculate_max_revitalization=calculate_max_revitalization,
        display_name=display_name,
    )
