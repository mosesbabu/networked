from flask import render_template

from app.blueprints.jobs.views import jobs


@jobs.app_errorhandler(403)
def forbidden(_):
    return render_template('errors/403.html'), 403


@jobs.app_errorhandler(404)
def page_not_found(_):
    return render_template('errors/404.html'), 404


@jobs.app_errorhandler(500)
def internal_server_error(_):
    return render_template('errors/500.html'), 500
