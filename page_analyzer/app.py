import os
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
import validators
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, flash, url_for

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

DATABASE_URL = os.getenv('DATABASE_URL')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url')

    # Валидация
    if not url or not validators.url(url) or len(url) > 255:
        flash('Invalid URL', 'danger')
        return redirect(url_for('index'))

    # Нормализация
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Проверка на уникальность
    cur.execute("SELECT id FROM urls WHERE name = %s;", (normalized_url,))
    exists = cur.fetchone()

    if exists:
        flash('Page already exists', 'info')
    else:
        created_at = datetime.utcnow()
        cur.execute(
            "INSERT INTO urls (name, created_at) VALUES (%s, %s);",
            (normalized_url, created_at)
        )
        flash('Page added successfully', 'success')

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('index'))
