import sqlite3


def names(database):
    with sqlite3.connect(database) as connection:
        return [row[0] for row in connection.execute("SELECT display_name FROM customer ORDER BY id")]
