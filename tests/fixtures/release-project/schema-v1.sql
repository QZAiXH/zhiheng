CREATE TABLE customer(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE migrations(version TEXT PRIMARY KEY);
INSERT INTO customer(id, name) VALUES (1, 'Ada'), (2, 'Lin');
