import psycopg2
import psycopg2.extras


def connection(cursor_factory=None):
    def decorator(function):
        def wrapper(self, *args, **kwargs):
            conn = None
            try:
                conn = psycopg2.connect(getattr(self, 'db_url'))
                with conn:
                    with conn.cursor(cursor_factory=cursor_factory) as curs:
                        result = function(self, curs, *args, **kwargs)
                        return result
            except Exception as e:
                getattr(self, 'logger').error(f"{e}")
                raise
            finally:
                if conn:
                    conn.close()
        return wrapper
    return decorator


class DataBase:
    def __init__(self, db_url, logger):
        self.db_url = db_url
        self.logger = logger

    @connection()
    def get_url_id(self, curs, url: str) -> int | None:   
        query = "SELECT id FROM urls WHERE name=(%s);"
        curs.execute(query, (url,))
        url_id = curs.fetchone()
        if url_id:
            url_id = url_id[0]
        return url_id

    @connection(psycopg2.extras.DictCursor)
    def get_url_by_id(self, curs, id: int) -> dict | None:
        query = "SELECT * FROM urls WHERE id=(%s);"
        curs.execute(query, (id,))
        url = curs.fetchone()
        return url

    @connection()
    def add_url(self, curs, url: str) -> int:
        insert_query = "INSERT INTO urls (name) VALUES" \
            "(%s) RETURNING id;"
        curs.execute(insert_query, (url,))
        new_url_id = curs.fetchone()[0]
        return new_url_id

    @connection(psycopg2.extras.DictCursor)
    def get_urls(self, curs) -> list:
        query = """
            WITH cte AS
            (SELECT url_id,
                    status_code,
                    created_at,
                    row_number() OVER 
                    (PARTITION BY url_id ORDER BY id DESC) AS rn
            FROM url_checks)
            SELECT
                u.id,
                u.name,
                coalesce(cast(cte.created_at AS TEXT),'') AS created_at,
                coalesce(cast(cte.status_code AS TEXT),'') AS status_code
            FROM
                urls u
            LEFT JOIN cte
                ON u.id = cte.url_id
                    AND cte.rn = 1
            ORDER BY u.id DESC;
        """

        curs.execute(query)
        urls = curs.fetchall()
        return urls

    @connection()
    def add_check(self, curs, check: dict) -> int:
        insert_query = """
            INSERT INTO url_checks (
                url_id, 
                status_code, 
                h1, 
                title, 
                description
            ) VALUES
            (%s, %s, %s, %s, %s) RETURNING id;
        """
        curs.execute(insert_query, (check['url_id'], 
                                    check['status_code'], 
                                    check['h1'], 
                                    check['title'], 
                                    check['description'],))
        new_check_id = curs.fetchone()[0]
        return new_check_id

    @connection(psycopg2.extras.DictCursor)
    def get_url_checks(self, curs, url_id: int) -> list:
        query = """
            SELECT * from url_checks
            WHERE url_id=(%s)
            ORDER BY id DESC;
        """
        curs.execute(query, (url_id,))
        checks = curs.fetchall()
        return checks

    @connection(psycopg2.extras.DictCursor)
    def get_check_by_id(self, curs, check_id: int) -> dict | None:
        query = "SELECT * FROM url_checks WHERE id=(%s);"
        curs.execute(query, (check_id,))
        check = curs.fetchone()
        return check