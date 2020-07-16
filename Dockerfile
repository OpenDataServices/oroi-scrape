FROM alephdata/memorious:1.8.0

COPY setup.py /oroi-scrape/
COPY oroi-scrape/scrapers /oroi-scrape/scrapers
RUN pip3 install -q -e /oroi-scrape
COPY oroi-scrape/config /oroi-scrape/config
