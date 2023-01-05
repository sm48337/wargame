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

    first_player = User.query.get(request.form.get('first_player'))
    second_player = User.query.get(request.form.get('second_player'))
    state = get_initial_board_state()

    new_game = Game(first_player=first_player, second_player=second_player, board_state=state)
    db.session.add(new_game)
    db.session.commit()

    return redirect(url_for('game.board', game_id=new_game.id))


@bp.route('/<int:game_id>/board', methods=['GET', 'POST'])
@login_required
def board(game_id):
    game = Game.query.get_or_404(game_id)
    if request.method == 'POST':
        if errors := game.perform_checks(request.form):
            for message, category in errors:
                flash(message, category)
            return render_template('board.html', context=game)

        game.process_turn(request.form)
        db.session.commit()

    return render_template('board.html', context=game)
