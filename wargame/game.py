from itertools import chain
from operator import itemgetter

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('game', __name__, url_prefix='/game')


@bp.route('/')
@login_required
def home():
    return render_template('home.html')


def get_initial_state():
    state = dict()
    state['red'] = {
        'entities': [
            {
                'id': 'bear',
                'name': 'Energetic Bear',
                'image': '/static/entities/russia-bear.jpg',
                'connections': [
                    'rus-gov',
                ],
                'attacks': [
                    'plc',
                ]
            },
            {
                'id': 'trolls',
                'name': 'Online Trolls',
                'image': '/static/entities/russia-troll.jpg',
                'connections': [],
                'attacks': [
                    'elect',
                ]
            },
            {
                'id': 'rus-gov',
                'name': 'Government',
                'image': '/static/entities/russia-gov.jpg',
                'connections': [
                    'bear',
                    'ros',
                    'scs',
                    'trolls',
                ],
            },
            {
                'id': 'scs',
                'name': 'SCS',  # 'Special Communications Service',
                'image': '/static/entities/russia-scs.png',
                'connections': [
                    'bear',
                    'rus-gov',
                ],
            },
            {
                'id': 'ros',
                'name': 'Rosenergoatom',
                'image': '/static/entities/russia-energy.png',
                'connections': [
                    'rus-gov',
                ],
            },
        ]
    }
    state['blue'] = {
        'entities': [
            {
                'id': 'gchq',
                'name': 'GCHQ',
                'image': '/static/entities/uk-gchq.png',
                'connections': [
                    'uk-gov',
                ],
            },
            {
                'id': 'energy',
                'name': 'UK Energy',
                'image': '/static/entities/uk-energy.png',
                'connections': [
                    'elect',
                    'uk-gov',
                ],
            },
            {
                'id': 'uk-gov',
                'name': 'Government',
                'image': '/static/entities/uk-gov.jpg',
                'connections': [
                    'elect',
                    'energy',
                    'gchq',
                    'plc',
                ],
            },
            {
                'id': 'plc',
                'name': 'UK PLC',
                'image': '/static/entities/uk-plc.png',
                'connections': [
                    'gchq',
                    'uk-gov',
                ],
            },
            {
                'id': 'elect',
                'name': 'Electorate',
                'image': '/static/entities/uk-voters.jpg',
                'connections': [
                    'energy',
                    'plc',
                    'uk-gov',
                ]
            },
        ]
    }
    for entity in chain.from_iterable(
            map(itemgetter('entities'), state.values())
    ):
        entity['resource'] = 3
        entity['vitality'] = 4

    return state


@bp.route('/board')
@login_required
def board():
    state = get_initial_state()
    return render_template('board.html', context=state)
