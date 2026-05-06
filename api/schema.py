SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
  group_id TEXT PRIMARY KEY,
  password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  name TEXT NOT NULL,
  group_id TEXT NOT NULL,
  PRIMARY KEY (name, group_id),
  CONSTRAINT users_group_fk FOREIGN KEY (group_id) REFERENCES accounts(group_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS foods (
  name TEXT PRIMARY KEY,
  cal_100g REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS meal_logs (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  label TEXT NOT NULL,
  "user" TEXT NOT NULL,
  calories REAL NOT NULL,
  group_id TEXT NOT NULL,
  CONSTRAINT meal_group_fk FOREIGN KEY (group_id) REFERENCES accounts(group_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_spend (
  date DATE NOT NULL,
  "user" TEXT NOT NULL,
  depense REAL NOT NULL,
  group_id TEXT NOT NULL,
  PRIMARY KEY (date, "user", group_id),
  CONSTRAINT spend_group_fk FOREIGN KEY (group_id) REFERENCES accounts(group_id) ON DELETE CASCADE
);
"""

