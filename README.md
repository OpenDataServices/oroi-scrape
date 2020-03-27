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