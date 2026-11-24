# Distributed Database Project Template

This is a template meant to help students to tackle the distributed database course final project

## Docker compose
- Start the cluster using `docker compose up -d`
- Stop the cluster using `docker compose down`
- Fully reset the cluster using `docker compose down -v` this will delete all data

## Default Ports / URLs Set
- Default SQL connection string `postgresql://root@localhost:26257/defaultdb?sslmode=disable`
- HAProxy stats page `localhost:8404`
