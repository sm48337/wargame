from itertools import chain
from operator import itemgetter

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required

from .models import db, User, Game

bp = Blueprint('game', __name__, url_prefix='/game')


@bp.route('/')
@login_required
def home():
    return render_template('home.html')


def get_initial_state():
    state = dict()
    state['turn'] = 1
    state['month'] = 'January'
    state['teams'] = dict()

    state['teams']['red'] = {
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
    state['teams']['blue'] = {
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
            map(itemgetter('entities'), state['teams'].values())
    ):
        entity['resource'] = 3
        entity['vitality'] = 4

    return state


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'GET':
        context = {
            'players': User.query.filter(User.active),
        }
        return render_template('new.html', context=context)

    first_player = User.query.get(request.form.get('first_player'))
    second_player = User.query.get(request.form.get('second_player'))

    new_game = Game(first_player=first_player, second_player=second_player)
    db.session.add(new_game)
    db.session.commit()

    return redirect(url_for('game.board', game_id=new_game.id))


@bp.route('/<int:game_id>/board')
@login_required
def board(game_id):
    state = get_initial_state()
    return render_template('board.html', context=state)
