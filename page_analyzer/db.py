import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime


def get_connection(dsn):
    return psycopg2.connect(dsn, cursor_factory=DictCursor)


def insert_url(conn, name):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO urls (name, created_at) "
            "VALUES (%s, %s) RETURNING id",
            (name, datetime.now())
        )
        return cur.fetchone()['id']


def find_url_by_name(conn, name):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM urls WHERE name = %s",
            (name,)
        )
        return cur.fetchone()


def get_url_by_id(conn, id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, created_at FROM urls WHERE id = %s",
            (id,)
        )
        return cur.fetchone()


def get_url_checks(conn, id):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, status_code, h1, title, description, created_at
            FROM url_checks
            WHERE url_id = %s
            ORDER BY id DESC
            """,
            (id,)
        )
        return cur.fetchall()


def get_all_urls(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.name, u.created_at,
                   MAX(c.created_at) AS last_check,
                   MAX(c.status_code) AS status_code
            FROM urls u
            LEFT JOIN url_checks c ON u.id = c.url_id
            GROUP BY u.id
            ORDER BY u.id DESC
            """
        )
        return cur.fetchall()


def insert_check(conn, url_id, status_code, h1, title, description):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO url_checks
            (url_id, status_code, h1, title, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (url_id, status_code, h1, title, description, datetime.now())
        )
