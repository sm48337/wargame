from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('game', __name__, url_prefix='/game')


@bp.route('/')
def home():
    return render_template('home.html')


@bp.route('/board')
@login_required
def board():
    context = dict()
    context['red'] = {
        'entities': [
            {
                'name': 'Energetic Bear',
                'image': '/static/entities/russia-bear.jpg'
            },
            {
                'name': 'Online Trolls',
                'image': '/static/entities/russia-troll.jpg'
            },
            {
                'name': 'Government',
                'image': '/static/entities/russia-gov.jpg'
            },
            {
                'name': 'Special Communications Service',
                'image': '/static/entities/russia-scs.png'
            },
            {
                'name': 'Rosenergoatom',
                'image': '/static/entities/russia-energy.png'
            },
        ]
    }
    context['blue'] = {
        'entities': [
            {
                'name': 'GCHQ',
                'image': '/static/entities/uk-gchq.png'
            },
            {
                'name': 'UK Energy',
                'image': '/static/entities/uk-energy.png'
            },
            {
                'name': 'Government',
                'image': '/static/entities/uk-gov.jpg'
            },
            {
                'name': 'UK PLC',
                'image': '/static/entities/uk-plc.png'
            },
            {
                'name': 'Electorate',
                'image': '/static/entities/uk-voters.jpg'
            },
        ]
    }
    return render_template('board.html', context=context)
