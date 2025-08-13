import os
from datetime import date
from urllib.parse import urlparse

from flask import (
    abort,
    Flask,
    flash,
    url_for,
    render_template,
    request,
    redirect,
)
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from validators.url import url as is_valid_url
from bs4 import BeautifulSoup
import requests


load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
MAX_URL_LEN = 255


class DataBase:
    def __init__(self, db_url: str=DATABASE_URL):
        self.conn = psycopg2.connect(db_url)

    def __del__(self):
        self.conn.close()
    
    def get_id(self, url: str) -> int | None:
        query = "SELECT id FROM urls WHERE name=(%s);"
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(query, (url,))
                url_id = curs.fetchone() # returns None if empty or tuple otherwise
                if url_id:
                    url_id = url_id[0]
        return url_id
    
    def get_url(self, id: int) -> dict | None:
        query = "SELECT * FROM urls WHERE id=(%s);"
        with self.conn:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute(query, (id,))
                url = curs.fetchone()
        return url

    def add_url(self, url: str) -> int:
        insert_query = "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id;"
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (url, date.today()))
                new_url_id = curs.fetchone()[0]
        return new_url_id

    def get_urls(self) -> list:
        query = """
        with cte as
        (select url_id,
                status_code,
                created_at,
                row_number() over (partition by url_id order by created_at desc) as rn
        from url_checks)
            SELECT
                u.id,
                u.name,
                coalesce(cast(cte.created_at as text),'') as created_at,
                coalesce(cast(cte.status_code as text),'') as status_code
            FROM
                urls u
            left join cte
                on u.id = cte.url_id
                    and cte.rn = 1
            order by u.id desc;
        """
        
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(query)
            urls = curs.fetchall()
        return urls
    
    def add_check(self, check: dict) -> int:
        insert_query = """
            INSERT INTO url_checks (url_id, status_code, h1, title, description, created_at) VALUES
            (%s, %s, %s, %s, %s, %s) RETURNING id;
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (check['url_id'], check['status_code'], 
                                            check['h1'], check['title'], 
                                            check['description'], date.today()))
                new_check_id = curs.fetchone()[0]
        return new_check_id

    def get_checks(self, url_id: int) -> list:
        query = """
            SELECT * from url_checks
            WHERE url_id=(%s)
            ORDER BY id DESC;
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(query, (url_id,))
            checks = curs.fetchall()
        return checks

    def get_check(self, check_id: int) -> dict | None:
        query = "SELECT * FROM url_checks WHERE id=(%s);"
        with self.conn:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute(query, (check_id,))
                check = curs.fetchone()
        return check

url_repo = DataBase()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


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
    url = url_repo.get_url(id)
    if url:
        checks = url_repo.get_checks(id)
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
        return render_template("index.html", url=url)
    
    if len(url) > MAX_URL_LEN:
        flash("URL превышает 255 символов", "danger")
        return render_template("index.html", url=url)
    
    parse_result = urlparse(url)
    scheme = parse_result.scheme
    hostname = parse_result.hostname
    name = scheme + "://" + hostname

    id = url_repo.get_id(name)
    if id:
        flash("Страница уже существует", "info")
        return redirect(url_for("urls_show", id=id), code=302)
    
    new_id = url_repo.add_url(name)
    flash("Страница успешно добавлена", "success")
    return redirect(url_for("urls_show", id=new_id), code=302)


@app.post('/urls/<int:id>/checks')
def check_post(id):
    url = url_repo.get_url(id)
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
    except:
        flash("Произошла ошибка при проверке", "danger")
    return redirect(url_for("urls_show", id=id), code=302)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404