import logging
import os

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .database import DataBase
from .parser import get_data
from .process_url import normalize_url, validate_url

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.logger.setLevel(logging.WARNING)

DATABASE_URL = os.getenv('DATABASE_URL')
MAX_URL_LEN = 255

url_repo = DataBase(DATABASE_URL, app.logger)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/urls')
def urls_index():
    urls = url_repo.get_urls()
    return render_template(
        'urls/index.html',
        urls=urls,
    )


@app.route('/urls/<int:id>')
def urls_show(id):
    url = url_repo.get_url_by_id(id)
    if url:
        checks = url_repo.get_url_checks(id)
        return render_template(
            'urls/show.html',
            url=url,
            checks=checks,
        )
    abort(404)


@app.post('/urls')
def urls_post():
    request_data = request.form.to_dict()
    url = request_data['url']

    errors = validate_url(url)
    if errors:
        flash(errors['url'], "danger")
        return render_template("index.html", url=url), 422
    
    url = normalize_url(url)

    id = url_repo.get_url_id(url)
    if id:
        flash("Страница уже существует", "info")
    else:
        id = url_repo.add_url(url)
        flash("Страница успешно добавлена", "success")
    return redirect(url_for("urls_show", id=id), code=302)


@app.post('/urls/<int:id>/checks')
def check_post(id):
    url = url_repo.get_url_by_id(id)
    if url is None:
        abort(404)
    site = url['name']

    try:
        response = requests.get(site)
        response.raise_for_status()

        check = get_data(response)
        check['url_id'] = id
        url_repo.add_check(check)
        flash("Страница успешно проверена", "success")
    except Exception:
        flash("Произошла ошибка при проверке", "danger")
    return redirect(url_for("urls_show", id=id), code=302)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404