import os
import time
from flask import Flask, request, render_template_string, redirect, url_for
import psycopg2
from prometheus_client import Counter, generate_latest

app = Flask(__name__)

# Prometheus metrics setup
REQUESTS = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint'])

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres-db'),
        database=os.getenv('DB_NAME', 'app_db'),
        user=os.getenv('DB_USER', 'db_user'),
        password=os.getenv('DB_PASSWORD', 'secure_password')
    )
    return conn

def init_db():
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            cur.close()
            conn.close()
            break
        except Exception as e:
            print(f"Waiting for database, retrying in 3 seconds... Error: {e}")
            retries -= 1
            time.sleep(3)

init_db()

@app.route('/')
def home():
    REQUESTS.labels(method='GET', endpoint='/').inc()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT name, status, created_at FROM servers ORDER BY created_at DESC;')
        servers = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return f"Database error: {e}", 500

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>DevOps Portfolio</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f6f9; }
            h1 { color: #333; }
            form { margin-bottom: 20px; }
            input[type="text"] { padding: 8px; width: 200px; }
            input[type="submit"] { padding: 8px 15px; background-color: #28a745; color: white; border: none; cursor: pointer; }
            table { width: 50%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
            th { background-color: #343a40; color: white; }
            .node { color: #007bff; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Infrastructure Control Panel</h1>
        <p>Request processed by container (node): <span class="node">{{ node_name }}</span></p>
        <form action="/add" method="POST">
            <input type="text" name="name" placeholder="Server Name" required>
            <input type="submit" value="Add Server">
        </form>
        <table>
            <tr><th>Server Name</th><th>Status</th><th>Added At</th></tr>
            {% for server in servers %}
            <tr>
                <td>{{ server[0] }}</td>
                <td>{{ server[1] }}</td>
                <td>{{ server[2] }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    node_name = os.getenv('HOSTNAME', 'Unknown Node')
    return render_template_string(html, servers=servers, node_name=node_name)

@app.route('/add', methods=['POST'])
def add_server():
    REQUESTS.labels(method='POST', endpoint='/add').inc()
    name = request.form.get('name')
    if name:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO servers (name) VALUES (%s);', (name,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            return f"Database error: {e}", 500
    return redirect(url_for('home'))

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
