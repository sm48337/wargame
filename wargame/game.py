from datetime import datetime, timedelta

from flask import Blueprint, flash, render_template, request, redirect, url_for
from flask_login import login_required

from .models import db, User, Game, Team
from .utils import get_initial_board_state, entity_ids_by_team, entity_types

bp = Blueprint('game', __name__, url_prefix='/')


@bp.route('/')
@login_required
def home():
    return render_template('home.html')


def form_team(team):
    new_team = Team()
    new_team.name = request.form.get(f'{team}-team-name')
    for entity_id, entity_type in zip(entity_ids_by_team[team], entity_types):
        setattr(new_team, entity_type + '_player', User.query.get(request.form.get(entity_id)))
    return new_team


@bp.route('game/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'GET':
        context = {
            'players': User.query.filter(User.active),
        }
        return render_template('new.html', context=context)

    red_team = form_team('red')
    blue_team = form_team('blue')
    description = request.form.get('description')
    state = get_initial_board_state()

    new_game = Game(red_team=red_team, blue_team=blue_team, board_state=state, description=description)
    db.session.add(new_game)
    db.session.commit()

    return redirect(url_for('game.board', game_id=new_game.id))


@bp.route('game/<int:game_id>/turn_start')
@login_required
def turn_start(game_id):
    game = Game.query.get_or_404(game_id)
    return {
        'turn': game.board_state['turn'],
        'start': game.turn_start.isoformat(),
    }


@bp.route('game/<int:game_id>/board', methods=['GET', 'POST'])
@login_required
def board(game_id):
    game = Game.query.get_or_404(game_id)

    if request.method == 'POST':
        if errors := game.perform_checks(request.form):
            for message, category in errors:
                flash(message, category)
            return redirect(url_for('game.board', game_id=game.id))

        game.process_turn(request.form)
        db.session.commit()
        return redirect(url_for('game.board', game_id=game.id))

    elif (game.turn_start + timedelta(minutes=3, seconds=5)) < datetime.now():
        game.process_turn(dict())
        db.session.commit()

    return render_template('board.html', context=game)
