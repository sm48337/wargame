from datetime import datetime, timedelta

from flask import Blueprint, flash, render_template, request, redirect, url_for
from flask_login import login_required

from .models import db, User, Game
from .utils import get_initial_board_state

bp = Blueprint('game', __name__, url_prefix='/game')


@bp.route('/')
@login_required
def home():
    return render_template('home.html')


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'GET':
        context = {
            'players': User.query.filter(User.active),
        }
        return render_template('new.html', context=context)

    red_player = User.query.get(request.form.get('red_player'))
    blue_player = User.query.get(request.form.get('blue_player'))
    state = get_initial_board_state()

    new_game = Game(red_player=red_player, blue_player=blue_player, board_state=state)
    db.session.add(new_game)
    db.session.commit()

    return redirect(url_for('game.board', game_id=new_game.id))


@bp.route('/<int:game_id>/turn_start')
@login_required
def turn_start(game_id):
    game = Game.query.get_or_404(game_id)
    return {
        'turn': game.board_state['turn'],
        'start': game.turn_start.isoformat(),
    }


@bp.route('/<int:game_id>/board', methods=['GET', 'POST'])
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
