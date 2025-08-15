from contextlib import contextmanager
from datetime import date


import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool


class DataBase:
    def __init__(self, db_url: str, min_conn: int=1, max_conn: int=8):
        self.db_url = db_url
        self.pool = ThreadedConnectionPool(min_conn, max_conn, db_url)

    def __del__(self):
        self.pool.closeall()

    @contextmanager
    def get_db_connection(self, cursor_factory=None):
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=cursor_factory) as curs:
                    yield curs
        finally:
            self.pool.putconn(conn)

    def get_url_id(self, url: str) -> int | None:   
        query = "SELECT id FROM urls WHERE name=(%s);"
        with self.get_db_connection() as curs:
            curs.execute(query, (url,))
            url_id = curs.fetchone()
            if url_id:
                url_id = url_id[0]
        return url_id
        
    def get_url_by_id(self, id: int) -> dict | None:
        query = "SELECT * FROM urls WHERE id=(%s);"
        with self.get_db_connection(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(query, (id,))
            url = curs.fetchone()
        return url

    def add_url(self, url: str) -> int:
        insert_query = "INSERT INTO urls (name, created_at) VALUES" \
            "(%s, %s) RETURNING id;"
        with self.get_db_connection() as curs:
            curs.execute(insert_query, (url, date.today()))
            new_url_id = curs.fetchone()[0]
        return new_url_id

    def get_urls(self) -> list:
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
        
        with self.get_db_connection(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(query)
            urls = curs.fetchall()
        return urls
    
    def add_check(self, check: dict) -> int:
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

        with self.get_db_connection() as curs:
            curs.execute(insert_query, (check['url_id'], 
                                        check['status_code'], 
                                        check['h1'], 
                                        check['title'], 
                                        check['description'], 
                                        date.today()))
            new_check_id = curs.fetchone()[0]
        return new_check_id

    def get_url_checks(self, url_id: int) -> list:
        query = """
            SELECT * from url_checks
            WHERE url_id=(%s)
            ORDER BY id DESC;
        """
        with self.get_db_connection(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(query, (url_id,))
            checks = curs.fetchall()
        return checks

    def get_check_by_id(self, check_id: int) -> dict | None:
        query = "SELECT * FROM url_checks WHERE id=(%s);"
        with self.get_db_connection(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(query, (check_id,))
            check = curs.fetchone()
        return check