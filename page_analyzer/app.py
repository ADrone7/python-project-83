import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
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
from validators.url import url as is_valid_url

from .database import DataBase

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
MAX_URL_LEN = 255

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
url_repo = DataBase(DATABASE_URL)


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

    if not is_valid_url(url):
        flash("Некорректный URL", "danger")
        return render_template("index.html", url=url), 422
    
    if len(url) > MAX_URL_LEN:
        flash("URL превышает 255 символов", "danger")
        return render_template("index.html", url=url), 422
    
    parse_result = urlparse(url)
    scheme = parse_result.scheme
    hostname = parse_result.hostname
    name = scheme + "://" + hostname

    id = url_repo.get_url_id(name)
    if id:
        flash("Страница уже существует", "info")
        return redirect(url_for("urls_show", id=id), code=302)
    
    new_id = url_repo.add_url(name)
    flash("Страница успешно добавлена", "success")
    return redirect(url_for("urls_show", id=new_id), code=302)


@app.post('/urls/<int:id>/checks')
def check_post(id):
    url = url_repo.get_url_by_id(id)
    if url is None:
        abort(404)
    site = url['name']

    try:
        response = requests.get(site)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        desc = soup.find('meta', {'name': 'description'})

        check = {
            'url_id': id,
            'status_code': response.status_code,
            'h1': soup.h1.text if soup.h1 else '',
            'title': soup.title.text if soup.title else '',
            'description': desc.get('content') if desc else '',
        }
        url_repo.add_check(check)
        flash("Страница успешно проверена", "success")
    except Exception:
        flash("Произошла ошибка при проверке", "danger")
    return redirect(url_for("urls_show", id=id), code=302)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404