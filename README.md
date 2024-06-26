# Simple URL checker
A simple site availability monitor coding challenge.

## Problem
Implement a program that monitors the availability of many websites over the network, produces metrics about these and stores the metrics into a PostgreSQL database.

The website monitor should perform the checks periodically and collect the request timestamp, the response time, the HTTP status code, as well as optionally checking the returned page contents for a regex pattern that is expected to be found on the page. Each URL should be checked periodically, with the ability to configure the interval (between 5 and 300 seconds) and the regexp on a per-URL basis. The monitored URLs can be anything found online.
In case the check fails the details of the failure should be logged into the database.

## Installation
First, set up DB and add its credentials using one of:
- create a `db/.pgpass` file (https://www.postgresql.org/docs/15/libpq-pgpass.html) with database credentials and uncomment `passfile` option in the `db` section of [settings.toml](settings.toml)
- set environment variable `PGPASSWORD` with database password
- add `password` to the `db` section of [settings.toml](settings.toml)

also don't forget to set `host`, `user`, and if needed, `port` and `cafile` options in the `db` section of [settings.toml](settings.toml)

### Manual
- checkout project code to some path (e.g. `/home/user/url_checker`)
- create and activate virtualenv `python3 -m venv .venv && source .venv/bin/activate`
- install dependendencies `pip install -r requirements.txt`
- run `service.py`

For systemd management:
- edit included `url-checker.service` file: on line `ExecStart=/path/to/project/.venv/bin/python3 /path/to/project/service.py` replace `/path/to/project/` with a real path (e.g. `/home/user/url_checker`)
- install the unit (preferrably to `~/.config/systemd/user/`), reload daemon and start the service
### Using Docker
- Build a container `docker build -t url-checker .`
- Run it `docker run url-checker`

## CLI
A simple UI to the service.
Usage: `cli.py` _action_
Actions:
- `list` -- show list of all scheduled urls and their parameters
- `show` -- show details for single url, parameter:
  - `id` -- record id
- `add`  -- add new url to watch list, parameters:
  - `url`
  - `interval`
  - `content_rx`
- `remove` -- remove url from watch list and all it's log records, parameter:
  - `id` -- record id
- `update` -- modify url parameters:
  - `-e` -- enable checking
  - `-d` -- disable checking
  - `-r regex` -- update content regex to new value
  - `-R` -- remove content regex
  - `-i value` -- update interval


## Limitations & what could be better
- Server response always loaded in memory -- may cause problems with large responses
  - this might be handled by using HEAD requests, when content check is not needed (unreliable though -- not all servers correctly handle them)
  - response can be streamed to a temp file for use with external tool like `ripgrep` for regex checking
- Results are written to DB 1-by-1, by worker coroutine
  - implementing result queue and watcher coroutine/thead to save results in bulk would increase throughput as well as complexity
- _Time To First Byte_ is not precise and may be less than actual, due to the way `*.receive_response_headers.started` events in `httpcore` imlpemented
- `check_log` DB table is created as a plain table without partitions -- no use for them in this demonstration, but for production usage it's better to have partitioning by month over `start` field. This also implies necessity of partition maintanance:
  - by adding and configuring [pg_partman](https://github.com/pgpartman/pg_partman) extension
  - or some trigger function for automatic partition creation
  - or at least some cron job


## Configuration
A single configuration file is used: [settings.toml](settings.toml)
- `db` section is used for database connection:
  - `cafile` - should be a path to root CA certificate file
  - see the [create_pool() reference](https://magicstack.github.io/asyncpg/current/api/index.html#connection-pools) for other available options
- `timeouts` -- to specify HTTP request timeouts
  - `readwrite` -- read and write timeout, seconds
  - `connection` -- connection timeout, seconds
- `scheduler`
  - `max_concurrency` -- maximal number of concurrent requests; if higher than `db.max_size`, may cause performance drop
  - `interval` -- in seconds, defines scheduler tick interval as well as minimal execution period


## Application structure
```mermaid
flowchart TB
    db[(Database)]
    cli[[CLI tool]]
    sh{{Scheduler}}
    w1[Worker 1]
    w2[Worker 2]
    w3[Worker n]
    db --> cli
    cli --> db
    db --> sh
    sh -.-> w1
    sh -.-> w2
    sh -.-> w3
    w1 --> db
    w2 --> db
    w3 --> db
```

## Scheduler implementation
### Main loop
```mermaid
flowchart TB
  a["Get next tick time (NTT)"]
  b[/"Get records from `watchlist` which have `last_start` empty, or `last_start` + `interval` < NTT"/]
  c["For each record spawn a worker"]
  d["Worker 1"]
  e["Worker 2"]
  f["Worker n"]
  g["Sleep until the end of tick (NTT)"]
  a --> b
  b --> c
  c -.-> d
  c -.-> e
  c -.-> f
  c --> g
  g --> a

```
### Worker
```mermaid
flowchart TB
  a("Wait on semaphore (concurrency limit)")
  b("Sleep until exact run time")
  c[["Perform HTTP request"]]
  d[/"Save log record to DB"/]
  a --> b
  b --> c
  c --> d
```


## DB structure
```mermaid
erDiagram
    watchlist {
        SERIAL id PK
        bool enable
        varchar url
        varchar content_rx "optional content regex"
        unsigned interval "run interval in seconds"
        timestamp last_start "simple scheduling helpers"
    }
    check_log {
        int wl_id PK, FK
        timestamp start PK "check start"
        timestamp end "check end"
        int connect "connect time (ms)"
        int ttfb "time to first byte (ms)"
        int response "total response time (ms)"
        int status_code
        bool content_check "content regex run result"
        varchar error_message
    }
    watchlist ||--o{ check_log : results
```
