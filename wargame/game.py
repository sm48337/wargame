from flask import Blueprint, abort, flash, render_template, request, redirect, url_for
from flask_login import login_required, current_user

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

    new_game = Game(owner=current_user, red_team=red_team, blue_team=blue_team, board_state=state, description=description)
    db.session.add(new_game)
    db.session.commit()

    return redirect(url_for('game.board', game_id=new_game.id))


@bp.route('game/<int:game_id>/toggle_pause')
@login_required
def toggle_pause(game_id):
    game = Game.query.get_or_404(game_id)
    if current_user != game.owner:
        abort(403)
    game.toggle_pause()
    db.session.commit()
    return {
        'paused': game.is_paused
    }


@bp.route('game/<int:game_id>/time_left')
@login_required
def time_left(game_id):
    game = Game.query.get_or_404(game_id)
    return {
        'turn': game.board_state['turn'],
        'secondsLeft': game.time_left(),
        'isStarting': game.is_starting,
        'isPaused': game.is_paused,
        'startingDelay': game.starting_delay if game.is_starting else 0,
    }


@bp.route('game/<int:game_id>/board', methods=['GET', 'POST'])
@login_required
def board(game_id):
    game = Game.query.get_or_404(game_id)

    if request.method == 'POST':
        if errors := game.perform_checks(request.form, current_user):
            for message, category in errors:
                flash(message, category)
            return redirect(url_for('game.board', game_id=game.id))

        game.ready_player(current_user)
        game.process_turn(request.form)
        db.session.commit()
        return redirect(url_for('game.board', game_id=game.id))

    elif not game.is_paused and game.time_left() < -5:
        game.process_turn(dict(), timeout=True)
        db.session.commit()

    return render_template('board.html', context=game)
