import os
from datetime import date

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def connection(cursor_factory=None):
    def decorator(function):
        def wrapper(*args, **kwargs):
            conn = psycopg2.connect(DATABASE_URL, sslmode="disable")
            with conn:
                with conn.cursor(cursor_factory=cursor_factory) as curs:
                    result = function(curs, *args, **kwargs)
            if conn:
                conn.close()
            return result
        return wrapper
    return decorator


@connection()
def get_url_id(curs, url: str) -> int | None:   
    query = "SELECT id FROM urls WHERE name=(%s);"
    curs.execute(query, (url,))
    url_id = curs.fetchone()
    if url_id:
        url_id = url_id[0]
    return url_id


@connection(psycopg2.extras.DictCursor)
def get_url_by_id(curs, id: int) -> dict | None:
    query = "SELECT * FROM urls WHERE id=(%s);"
    curs.execute(query, (id,))
    url = curs.fetchone()
    return url


@connection()
def add_url(curs, url: str) -> int:
    insert_query = "INSERT INTO urls (name, created_at) VALUES" \
        "(%s, %s) RETURNING id;"
    curs.execute(insert_query, (url, date.today()))
    new_url_id = curs.fetchone()[0]
    return new_url_id


@connection(psycopg2.extras.DictCursor)
def get_urls(curs) -> list:
    query = """
        with cte as
        (select url_id,
                status_code,
                created_at,
                row_number() over 
                (partition by url_id order by id desc) as rn
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

    curs.execute(query)
    urls = curs.fetchall()
    return urls


@connection()
def add_check(curs, check: dict) -> int:
    insert_query = """
        INSERT INTO url_checks (
            url_id, 
            status_code, 
            h1, 
            title, 
            description, 
            created_at
        ) VALUES
        (%s, %s, %s, %s, %s, %s) RETURNING id;
    """
    curs.execute(insert_query, (check['url_id'], 
                                check['status_code'], 
                                check['h1'], 
                                check['title'], 
                                check['description'], 
                                date.today()))
    new_check_id = curs.fetchone()[0]
    return new_check_id


@connection(psycopg2.extras.DictCursor)
def get_url_checks(curs, url_id: int) -> list:
    query = """
        SELECT * from url_checks
        WHERE url_id=(%s)
        ORDER BY id DESC;
    """
    curs.execute(query, (url_id,))
    checks = curs.fetchall()
    return checks


@connection(psycopg2.extras.DictCursor)
def get_check_by_id(curs, check_id: int) -> dict | None:
    query = "SELECT * FROM url_checks WHERE id=(%s);"
    curs.execute(query, (check_id,))
    check = curs.fetchone()
    return check