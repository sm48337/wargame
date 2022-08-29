from flask import Blueprint
from flask_login import login_required


bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/')
@login_required
def hello_world():
    return '<p>Hello, World!</p>'
