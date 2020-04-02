import lxml
from memorious.helpers import search_results_last_url


def last_page_no(context, data):
    init_url = context.get("url")

    response = context.http.get(init_url)

    # emit this page to parse stage as it gets skipped by the sequence
    # (it has no page no)
    context.emit(rule="parse", data=response.serialize())

    xpath = ".//div/ul[@class='pager']/li[@class='pager__item pager__item--last pager__item--special']"
    last_url = search_results_last_url(response.html, xpath, "last")
    page_no = last_url.split("?page=")[-1]
    context.emit(data={"number": int(page_no)})


def parse_gifts(context, data):
    parsed_row = {}
    with context.http.rehash(data) as result:
        if result.html is not None:
            table = result.html.findall(".//div[@class='view-content']/table")[0]
            for row in table.findall(".//tbody/tr"):
                parsed_row["source"] = result.url
                cells = row.findall(".//td")
                # Table columns:
                #  0 Recipient -> recipient, recipient_url
                #  1 Role type -> recipient_role
                #  2 Date gifted -> date_gifted
                #  3 Details -> details
                #  4 Donor / provider -> donor

                recipient = cells[0].find(".//a")
                parsed_row["recipient"] = recipient.text.strip()
                parsed_row["recipient_url"] = recipient.get("href")

                parsed_row["recipient_role"] = cells[1].text.strip()
                parsed_row["date_gifted"] = cells[2].find(".//span").get("content")
                parsed_row["details"] = cells[3].text.strip()
                parsed_row["donor"] = cells[4].text.strip()

                context.emit(rule="store", data=parsed_row)
