import pathlib
import sqlite3
import sys


def main():
    target = pathlib.Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target / "app.sqlite") as connection:
        connection.executescript((pathlib.Path(__file__).parent / "schema-v1.sql").read_text())
    (target / "VERSION").write_text("v1\n")
    (target / "app.py").write_text("def display_name(row):\n    return row['name']\n")


if __name__ == "__main__":
    main()
