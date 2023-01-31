from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, login_user, logout_user

from .models import db, User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.verify_password(password):
        login_user(user)
        next = request.args.get('next')
        return redirect(next or url_for('game.home'))
    flash('Wrong username or password!', 'error')
    return render_template('login.html', form=request.form)


@bp.route('/logout', methods=['GET'])
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    flash('You have successfully logged out!', 'info')

    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    username = request.form.get('username')
    password = request.form.get('password')
    password_repeat = request.form.get('password_repeat')

    if password != password_repeat:
        flash('Passwords do not match!', 'error')
        return render_template('register.html')

    new_user = User(username, password)

    db.session.add(new_user)
    db.session.commit()

    login_user(new_user)

    return redirect(url_for('game.home'))
