# eScape MySQL Database

This folder contains the MySQL schema generated from `Onboarding ERD.pdf`.

## Start with Docker

From the repository root:

```bash
docker compose up -d mysql
```

MySQL will start with:

- database: from `MYSQL_DATABASE` in `.env`
- user: from `MYSQL_USER` in `.env`
- password: from `MYSQL_PASSWORD` in `.env`
- root password: from `MYSQL_ROOT_PASSWORD` in `.env`
- port: `3306`

The schema in `database/schema.sql` is mounted into MySQL's init directory and runs automatically the first time the container creates its data volume.

## Connect

```bash
mysql -h 127.0.0.1 -P 3306 -u <MYSQL_USER> -p <MYSQL_DATABASE>
```

Replace the placeholders with the values from your local `.env`. Use `MYSQL_PASSWORD` from `.env` when prompted.

## Recreate From Scratch

If you need to reset the local database:

```bash
docker compose down -v
docker compose up -d mysql
```
