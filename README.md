# Open Registers of Interest Scrapers

Scrapers to get data about politicians interest declarations from public registers, using [memorious](https://memorious.readthedocs.io).

## Running with docker

```
(host) sudo docker-compose up -d
```

(First time, might take a while to build.)

The scrapers run in the `worker` which you can access with `docker-compose run --rm worker /bin/sh`.

Logs can be seen with `docker-compose logs worker` (replace `redis`, `ui` or `datastore`).

Interact with the crawlers on the commandline:

```
(worker) memorious list

(worker) memorious run crawler_name
```

The UI is available at localhost:8000.

## Development

To get output in the console when you run the crawlers, make sure the `MEMORIOUS_DEBUG` environment variable (set in the `worker` in `docker-compose.yml`) is 'true'. Turn this off for production.

If you're not running this with docker-compose, make sure the following environment variables are set for memorious:

* `MEMORIOUS_CONFIG_PATH`: path to scraper config (the yaml files)
* `MEMORIOUS_DEBUG`: 'true' for development, disables threading and outputs to console
* `REDIS_URL`: redis://..etc. Uses a temporary `FakeRedis` if missing.
* `MEMORIOUS_DATASTORE_URI`: postgresql://..etc. If not set, defaults to a local `datastore.sqllite3`.
* `MEMORIOUS_BASE_PATH`: scraper outputs base path where scraped data, intermediate data, logs, etc are stored; defaults to `data`
* `ARCHIVE_PATH`: where intermediate data is stored during scraping; defaults to base path / `archive`

See also: [memorious env vars docs](https://memorious.readthedocs.io/en/latest/installation.html#environment-variables).

### Scrapers

The scraper pipeline stages are defined in `config/{scraper_dir}` as yaml files.

Stages either use a built in memorious method, or custom ones for particular scrapers. The additional scraper Python functions live in `src/{scraper_dir}`.

### Poking around in the database

You can connect to the postgres database where the crawler results go through the `datastore` container:

```
(host) sudo docker-compose run datastore psql -h datastore -U datastore -d datastore
```

(The password is also `datastore` - configured in `docker-compose.yml`).

The table schema are set per-scraper (see the final stage in the yaml configs), and in addition to the columns there all also contain `__last_seen` and `__first_seen` columns which store when the row was updated or inserted.