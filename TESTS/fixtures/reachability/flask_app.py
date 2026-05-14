"""
Fixture: Flask app with reachable and unreachable functions.

Reachable via Flask routes:
  - process_input (called by /vuln route)
  - execute_query (called by process_input)

Unreachable (dead code):
  - orphan_function
  - dead_helper (only called by orphan_function)
"""

import sqlite3

from flask import Flask, request

app = Flask(__name__)


@app.route("/vuln")
def vuln_route():
    user_input = request.args.get("q", "")
    return process_input(user_input)


def process_input(data):
    return execute_query(data)


def execute_query(query):
    # ACR-QA-TEST: B608 sql injection (reachable)
    conn = sqlite3.connect(":memory:")
    conn.execute("SELECT * FROM users WHERE name = '" + query + "'")
    return "ok"


def orphan_function():
    # ACR-QA-TEST: dead code (unreachable)
    return dead_helper()


def dead_helper():
    # ACR-QA-TEST: dead code helper (unreachable, only called by orphan)
    import subprocess

    subprocess.run(["ls"], shell=True)  # noqa: S607
    return "dead"
