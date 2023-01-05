from functools import cache
from json import load


@cache
def get_initial_board_state():
    with open('wargame/static/initial_state.json') as f:
        state = load(f)
        return state


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

teams = ('Red', 'Blue')


def helper_functions():
    def turn_to_month(turn):
        return f"{months[turn // 2]} / {teams[turn % 2]} team's turn"

    return dict(turn_to_month=turn_to_month)
