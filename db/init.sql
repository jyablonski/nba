-- Empty schemas only. Alembic owns source DDL (`make db-migrate` /
-- compose migrate). dbt owns silver (staging + intermediate) and gold (marts).
-- This file runs only on first volume init.

CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
