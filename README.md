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

The table schema are set per-scraper (see below), and in addition to the columns there all also contain `__last_seen` and `__first_seen` columns which store when the row was updated or inserted.

## Scrapers

### GLA

Two scrapers, one to fetch the gifts/hospitality, and one for the declarations themselves.

`gla_gifts` table columns:

* `source`: url of the page the data came from
* `member_name`: name of person
* `member_url`: url of the person's profile on the website
* `member_role`: person's role
* `gift_date`: in ATOM format
* `gift_reason`: free text information about the gift
* `gift_donor`: free text, person or organisation that donated or provided gift

`gla_register` table columns:

* `source`: url of the page the data came from
* `member_name`: name of person making declaration
* `member_url`: url of the person's profile on the website
* `disclosure_date`: date on the declaration

The declaration fields contain the text for each response to the following questions. In the cases where the response was a bulleted list, items in the list have been joined with a `|`.

* `employment_description`: "1. Details of any employment, office, trade, profession or vocation carried on for profit or gain by me or my partner. [Partner means spouse, civil partner, a person with whom you live as husband or wife, or a person with whom you live as if you are civil partners]"
* `sponsorship_description`: "2. Details of any payment or provision of any other financial benefit (other than from the GLA) made or provided within the last 12 months in respect of any expenses incurred by me in carrying out my duties as a member, or towards my election expenses. (This includes any payment or financial benefit from a trade union)."
* `contract_description`: Covers all of the following:
    * "3(a). Details of any contract which is made between (i) myself (or my partner) and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged."
    * "3(b). Details of any contract which is made between (i) a firm in which I (or my partner) is a partner and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged."
    * "3(c). Details of any contract which is made between (i) a body corporate of which I (or my partner) is a director and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged. [Director includes a member of the committee of management of an industrial and provident society]"
    * "3(d). Details of any contract which is made between (i) a firm or a body corporate that in the securities of which I (or my partner) has a beneficial interest and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged. [Securities means shares, debentures, debenture stock, loan stock, bonds, units of a collective investment scheme within the meaning of the Financial Services and Markets Act 2000 and other securities of any description, other than money deposited with a building society."
    * "3(e). Details of any contract which is made between (i) a firm in which I am (or my partner is)  an employee and the relevant body/bodies at Section A of this form OR (ii) a member of my close family and the relevant body/bodies specified at Section A of this form under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged."
* `land_description`: "4. Details of any beneficial interest that I or my partner has in land within Greater London that entitles me or my partner to occupy (alone or jointly with another) that land, or to receive income from it."
* `contract_land_licence_description`: "5. Details of any licence that entitles me or my partner (alone or jointly with others) to occupy land in Greater London for a month or longer."
* `contract_tenancy_description`: "6. Details of any tenancy where, to my knowledge, (a) the GLA is the landlord; and (b) the tenant is (i) a firm in which I (or my partner) is a partner, (ii) a body corporate of which I (or my partner) is a director, or (iii) (i) a firm or a body corporate that in the securities of which I (or my partner) has a beneficial interest."
* `securities`: "7. Details of beneficial interest that I or my partner has in the securities of a body where (a) that body (to my knowledge) has a place of business or land in Greater London; and (b) either (i) the total nominal value of the securities that I or my partner has exceeds £25,000 or one hundredth of the total issued share capital of that body; or (ii) if the share capital of that body is of more than one class, the total nominal value of the shares of any one class in which I or my partner has a beneficial interest exceeds one hundredth of the total issued share capital of that class."
* `position_nonprofit_description`: "8. Names and positions in non-profit making organisations with which a relevant body specified at Section A has dealings where I am or my partner is a trustee or participate(s) in management of that body and where not disclosed elsewhere in this form."
* `position_other_description`: "9.  Any other office or position which I hold (including companies, trade associations and industry forums)  and where not already disclosed elsewhere in this form"
* `position_directorship_description`: "10. Any other directorships of companies which I hold, whether paid or not, and where not already disclosed elsewhere on this form"
* `other_description`: "11. Any other Interest which I hold which might reasonably be likely to be perceived as affecting my conduct or influencing my actions in relation to my role on the relevant body/bodies specified at Section A of the form."

### Bristol

`bristol_register` table columns:

* `source`: URL of the page the data came from
* `member_name`: Name of the councillor making the declaration
* `member_url`: URL of the profile page of the councillor making the declaration

The declaration fields as described on the webpage. In the cases where the response was a list, items in the list have been joined with a `|`.

* `employment_description`: "Employment, trade, profession or vocation"
* `sponsorship_description`: "Sponsorship"
* `contract_description`: "Contracts"
* `land_description`: "Land in the area of the authority"
* `contract_land_licence_description`: "Licences to occupy land"
* `contract_tenancy_description`: "Corporate tenancies"
* `securities_description`: "Securities"
* `position_membership_description`: "Membership of organisations"
* `gift_description` and `gift_date`: From "Gifts and hospitality" under headings "Name of Donor/Nature of gift or hospitality" and "Date of registration" respectively
