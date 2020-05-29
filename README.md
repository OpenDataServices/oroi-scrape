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

The scrapers mostly parse their sources into a common set of table columns, but there are some variations between them.

| Column name | Description |
| ----------- | ----------- |
| source | the url the data was scraped from |
| declared_to | the body to which the interest was declared |
| declared_date | the date on which the interest was registered |
| member_name | the name of the person declaring the interest |
| member_url | a url for the person declaring the interest |
| member_party | role or job description of person declaring the interest | 
| member_party | the party affiliation of the person declaring the interest | 
| interest_type | the category of interest being declared - see below |
| description | the contents of the declaration, which may contain other semi-structured data that can be parsed (or not) |
| interest_from | provider of the benefit, eg. donor of a gift, or company as employer |
| interest_date | date the benefit was received or took place, eg. date of donation (not date of declaration of interest) |
| interest_value | value of the benefit |
| notes | notes about the interest_type, eg. if the source was more specific than the value of interest_type captures

The following table summarises which scrapers populate which columns. See notes on individual scrapers below for more information about the actual values.

| Scraper | source | declared_to | declared_date | member_name | member_url | member_role | member_party | interest_type | description | interest_from | interest_date | interest_value |
| ------- | ------ | ---------------- | --------------- | ----------- | ---------- | ----------- | ------------ | ------------- | ----------- | ------------- | ------------- | -------------- |
| `ukparl_twfy` | X | X | X | X | X | | | X | X | | | |
| `ukparl_ministers` | n/a (downloads PDFs) |
| `ukparl_groups` | X | X | X | X | X | X | X | X | X | X | X | X |
| `gla_gifts` | X | X | | X | X | X | | X | X | X | X | |
| `gla_register` | X | X | X | X | X | | | X | X | | | |
| `bristol_register` | X | X | X | X | X | | | X | X | | (X) | |
| `bristol_meetings` | X | X | X | X | X | | | X | X | | | |
| `southglos_register` | X | X | X | X | X | | | X | X | X | | |

The value of `interest_type` is one of a set of slugs derived from various source data. The sources vary slightly in how they describe different types of interest, so the mapping of each interest_type to text at the source is listed per-scraper below.

### UK Parliament TWFY

`ukparl_twfy` takes the XML data already scraped from https://publications.parliament.uk by TheyWorkForYou and parses it into our database.

`ukparl_twfy` table columns notes:

* `source`: xml file the data came from, *not* the original source on the parliament website
* `member_url`: URI from publicwhip - not their official profile
* `declared_to`: "House of Commons"
* `declared_date`: date of the publication of the register, may not be the actual date of disclosure (in which case, it's in the description)
* `description`: contents of the interest declaration, aka the interest being declared. Sometimes semi-structured (by a human) and may be parsed further in some cases; sometimes has line spacings.

What this is missing:

* Link back to the actual source on the UK parliament website
* Member roles / party / constituency data which may appear in the source
* Some years have 'part 2' of the register filled with 'category 12' which is family members employed. Not sure if this is coming through.
* Older registers use different category numbering! Need to look at this and improve interest_type mapping.

**Interest types**

| interest_type | Source mappings |
| ------------- | --------------- |
| employment_and_earnings | "1. Employment and earnings" |
| employed_family | "9. Family members employed and paid from parliamentary expenses" |
| gift | "3. Gifts, benefits and hospitality from UK sources", "5. Gifts and benefits from sources outside the UK" |
| overseas_visit | "4. Visits outside the UK" |
| land_and_property | "6. Land and property portfolio: (i) value over £100,000 and/or (ii) giving rental income of over £10,000 a year" |
| securities_and_shareholding | "7.(i) Shareholdings: over 15% of issued share capital", "7.(ii) Other shareholdings, valued at more than £70,000" |
| donations_sponsorship | "2.(a) Support linked to an MP but received by a local party organisation or indirectly via a central party organisation", "2.(b) Any other support not included in Category 2(a)" |
| lobbying | "10. Family members engaged in lobbying the public sector on behalf of a third party or client" |
| other | "8. Miscellaneous" |

### UK Parliament ministers

`ukparl_ministers` fetches PDFs from [gov.uk list of ministers interests](https://www.gov.uk/government/publications/list-of-ministers-interests). They are stored in `MEMORIOUS_BASE_PATH/scraped_files/ukparl_ministers`.

### UK Parliament All-Party Parliamentary Groups

`ukparl_groups` gets the [All-Party Parliamentary Groups](https://publications.parliament.uk/pa/cm/cmallparty/200408/contents.htm) and for each benefit registered for a group, creates a declaration for each member of the group in the 'other' category, with the note "via role as {} in the {} All-Party Parliamentary Group" added to the `description`.

Note: Politician membership of groups that have no benefits declared do not get recorded.

`ukparl_groups` table column notes:

* `declared_to`: "UK Parliament"
* `member_name`: name of the group member
* `member_role`: role in group and name of group, eg. "Treasurer of Blockchain All Party Parliamentary Group"
* `interest_type`: "other"

**Interest types**

They are all "other".

### Greater London Assembly: Gifts

`gla_gifts` table column notes:

* `declared_to`: "Greater London Assembly"
* `interest_type`: "gift"
* `interest_date`: date gift was given, in ATOM format
* `interest_from`: free text, person or organisation that donated or provided gift

Missing:

* `declared_date` or anything that could be used to infer it (like last updated) is not provided at the source

**Interest types**

They are all "gift".

### Greater London Assembly: Register

`gla_register` table column notes:

* `declared_to`: "Greater London Assembly"
* `notes`: contains disambiguation information for contracts and positions, to take into account the subsections of these interest types in the source

Each person's declaration contains a response to one of a set of questions. Multi-line or bulleted responses are kept in their original form, because being split over lines doesn't guarantee that each line is actually a different interest; sometimes it's just poor formatting. If the response was "None" or "N/A" this is retained.

**Interest types**

| interest_type | Source mappings |
| ------------- | --------------- |
| employment_and_earnings | "1. Details of any employment, office, trade, profession or vocation carried on for profit or gain by me or my partner. [Partner means spouse, civil partner, a person with whom you live as husband or wife, or a person with whom you live as if you are civil partners]" |
| land_and_property | "4. Details of any beneficial interest that I or my partner has in land within Greater London that entitles me or my partner to occupy (alone or jointly with another) that land, or to receive income from it." |
| securities_and_shareholding | "7. Details of beneficial interest that I or my partner has in the securities of a body where (a) that body (to my knowledge) has a place of business or land in Greater London; and (b) either (i) the total nominal value of the securities that I or my partner has exceeds £25,000 or one hundredth of the total issued share capital of that body; or (ii) if the share capital of that body is of more than one class, the total nominal value of the shares of any one class in which I or my partner has a beneficial interest exceeds one hundredth of the total issued share capital of that class." |
| contracts | "3(a). Details of any contract which is made between (i) myself (or my partner) and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged.", "3(b). Details of any contract which is made between (i) a firm in which I (or my partner) is a partner and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged.", "3(c). Details of any contract which is made between (i) a body corporate of which I (or my partner) is a director and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged. [Director includes a member of the committee of management of an industrial and provident society]", "3(d). Details of any contract which is made between (i) a firm or a body corporate that in the securities of which I (or my partner) has a beneficial interest and (ii) the GLA under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged. [Securities means shares, debentures, debenture stock, loan stock, bonds, units of a collective investment scheme within the meaning of the Financial Services and Markets Act 2000 and other securities of any description, other than money deposited with a building society.", "3(e). Details of any contract which is made between (i) a firm in which I am (or my partner is)  an employee and the relevant body/bodies at Section A of this form OR (ii) a member of my close family and the relevant body/bodies specified at Section A of this form under which (a) goods or services are to be provided or works are to be executed and (b) which has not been fully discharged.", "5. Details of any licence that entitles me or my partner (alone or jointly with others) to occupy land in Greater London for a month or longer.", "6. Details of any tenancy where, to my knowledge, (a) the GLA is the landlord; and (b) the tenant is (i) a firm in which I (or my partner) is a partner, (ii) a body corporate of which I (or my partner) is a director, or (iii) (i) a firm or a body corporate that in the securities of which I (or my partner) has a beneficial interest." |
| donations_sponsorship | "2. Details of any payment or provision of any other financial benefit (other than from the GLA) made or provided within the last 12 months in respect of any expenses incurred by me in carrying out my duties as a member, or towards my election expenses. (This includes any payment or financial benefit from a trade union)." |
| positions | "8. Names and positions in non-profit making organisations with which a relevant body specified at Section A has dealings where I am or my partner is a trustee or participate(s) in management of that body and where not disclosed elsewhere in this form.", "9.  Any other office or position which I hold (including companies, trade associations and industry forums)  and where not already disclosed elsewhere in this form", "10. Any other directorships of companies which I hold, whether paid or not, and where not already disclosed elsewhere on this form" |
| other | "11. Any other Interest which I hold which might reasonably be likely to be perceived as affecting my conduct or influencing my actions in relation to my role on the relevant body/bodies specified at Section A of the form." |

### Bristol Register

`bristol_register` table columns notes:

* `declared_to` is "Bristol City Council"
* `interest_date` is present only the case of gifts.
* `notes` contains information to disambiguate contracts and positions.

In the cases where the response to each question in the register was a list, items in the list have been split into individual rows.

**Interest types**

| interest_type | Source mappings |
| ------------- | --------------- |
| employment_and_earnings | "Employment, trade, profession or vocation" |
| gift | "Gifts and hospitality" |
| land_and_property | "Land in the area of the authority" |
| securities_and_shareholding | "Securities" |
| contracts | "Contracts", "Licences to occupy land", "Corporate tenancies" |
| donations_sponsorship | "Sponsorship" |
| positions | "Membership of organisations" |

### Bristol Declarations of Interest

It runs a search over the minutes to get everything between 2000 and 2035. There are actually only minutes from 2016 and 2017 at the time of writing.

`bristol_meetings` table columns notes:

* `source` is a link to the meeting minutes
* `declared_to` is "Bristol City Council" followed by the name of the group meeting in parantheses

**Interest types**

They are all "positions". This is not scrapable, but from an artisanal interpretation (aka eyeball) of the source data, they more or less all seem to be.. This may need manual improvement at some point.

### South Gloucestershire Register of Interest

`southglos_register` table colunms notes:

* `description` sometimes contains a value where the spouse/partner/civil partner is the beneficiary - this is added in the `notes` field
* `declared_to` is South Gloucestershire City Council

**Interest types**

| interest_type | Source mappings |
| ------------- | --------------- |
| employment_and_earnings | "1. (Pecuniary Interest - Employment) You must provide details of ANY employment, office, trade, profession or vocation carried on for profit or gain." |
| donations_sponsorship | "2. (Pecuniary Interest - Sponsorship) You must provide details of any payment or provision of any other financial benefit (other than from the relevant authority) made or provided within the relevant period in respect of any expenses incurred by you as a Member of a relevant authority in carrying out duties as a member, or towards your election expenses. This includes any payment or financial benefit from a trade union within the meaning of the Trade Union and Labour Relations (Consolidation) Act 1992)." |
| contracts | "3. (Pecuniary Interest - Contracts) You must disclose details of any contract which is made between the relevant person (a relevant person is defined in the Act as a Member, or a body in which the relevant person has a beneficial interest) and the relevant authority (a) under which goods or services are to be provided or works are to be executed; and b) which has not been fully discharge" (sic) |
| land_and_property | "4. (Pecuniary Interest - Land) You must disclose the address of any beneficial interest in land which is within the area of the relevant authority." |
| contracts | "5. (Pecuniary Interest - Corporate Tenancies) You must disclose the address of any tenancy where (to your knowledge) a) the landlord is the relevant authority; and b) the tenant is a body in which the relevant person has a beneficial interest." |
| contracts | "6. (Pecuniary Interest - Licenses) You must give the address or describe the location of any land in which you have a licence (alone or jointly with others) to occupy for a month or more in the area of the relevant authority." |
| securities_and_shareholding | "7. (Pecuniary Interest - Securities) You should detail any beneficial interest in securities of a body which has to your knowledge a place of business or land in the area of your Council and either the total nominal value of the securities exceeds £25,000 or one hundredth of the total issued share capital, or one hundredth of the total issued share capital of any class of shares issued and that of your spouse/civil partner (or person with whom you are living as such) of which you are aware." |
| positions | "8. (Other Regsiterable Non Pecuniary Interest) You have a Non Disclosable Pecuniary interest in an item of business where a) a decision in relation to that business might reasonably be regarded as affecting the well-being or financial standing of you or a member of your family or a person or body with whom you have a close association to a greater extent than it would affect the majority of the Council Tax payers, ratepayers or inhabitants of the ward or electoral area for which you have been elected or otherwise of the authority’s administrative area, or b) it relates to or is likely to affect any of the interests listed in the Table in the Appendix to the Code, but in respect of a member of your family (other than a “relevant person”) or a person with whom you have a close association" |
| gift | "9. (Non-Pecuniary Interest - Gifts and Hospitality) Any gift or hospitality received or declined which is in excess of £100 in value" |

### North Somerset Council RoI

`nsomerset_register` fetches PDFs from [district councillors](https://www.n-somerset.gov.uk/my-council/councillors/councillor/membersinterests/registered-interests-district-councillors/), [town Parish councillors](https://www.n-somerset.gov.uk/my-council/councillors/councillor/membersinterests/registered-interests-town-parish-councillors/) and [co-opted members](https://www.n-somerset.gov.uk/my-council/councillors/councillor/membersinterests/registered-interests-co-opted-members/). They are stored in `MEMORIOUS_BASE_PATH/scraped_files/nsomerset_register`.