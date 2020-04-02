import copy
import lxml
from memorious.helpers import search_results_last_url

"""
Gets the page no. of the last page so all pages
can be generated in sequence.
"""
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

"""
Parses the table of gifts declarations on one page
"""
def parse_gifts(context, data):
    parsed_row = {}
    with context.http.rehash(data) as result:
        if result.html is not None:
            table = result.html.findall(".//div[@class='view-content']/table")[0]
            for row in table.findall(".//tbody/tr"):
                parsed_row["source"] = result.url
                cells = row.findall(".//td")

                recipient = cells[0].find(".//a")
                parsed_row["recipient"] = recipient.text.strip()
                parsed_row["recipient_url"] = recipient.get("href")

                parsed_row["recipient_role"] = cells[1].text.strip()
                parsed_row["date_gifted"] = cells[2].find(".//span").get("content")
                parsed_row["details"] = cells[3].text.strip()
                parsed_row["donor"] = cells[4].text.strip()

                context.emit(rule="store", data=parsed_row)

"""
Parses the sitemap to find all the people
"""
def get_members(context, data):
    base_url = context.get("base")
    sitemap_url = context.get("url")
    sitemap = context.http.get(sitemap_url)
    people = sitemap.html.find(".//div[@id='block-gla-key-person-profile-people-sitemap']")
    links = people.findall(".//div/ul/li/div/ul/li/a")
    for link in links:
        if link.text.strip().lower() == 'register of interests':
            context.emit(data={"url": "{}{}".format(base_url, link.get("href"))})

"""
Parses a declaration of interest
"""
def parse_declaration(context, data):
    declaration_mapping = {
        "employment": "1.",
        "payment_for_duties": "2.",
        "contract": "3(a).",
        "contract_with_firm": "3(b).",
        "contract_with_corporate": "3(c).",
        "contract_beneficial": "3(d).",
        "land": "4.",
        "land_occupancy_licence": "5.",
        "tenancy": "6.",
        "beneficial_interests_body": "7.",
        "nonprofit_positions": "8.",
        "other_positions": "9.",
        "other_directorships": "10.",
        "other_interest": "11."
    }
    parsed_row = {}
    with context.http.rehash(data) as result:
        if result.html is not None:
            
            # Get name
            nav = result.html.findall(".//nav[@class='breadcrumb']//a")
            profile = nav[-1]
            person_name = profile.text.strip().strip("More about ")
            person_url = profile.get("href")

            holders = result.html.findall(".//div[@class='content']/div/div[@class='field__items']/div")

            # Get date
            # At the bottom of the page, in the final content block
            last_block = holders[2]
            try:
                date = last_block.findall(".//p")[-1]
                if "date:" in date.text.lower():
                    date = date.text.strip('Date:').strip()
                else:
                    # different way of presenting date on some types of page
                    blob = date.text_content().split("\n")
                    date = blob[-1].strip("Original declaration date:").strip()
            except:
                date = "not found"

            base_declaration = {
                "source": result.url,
                "name": person_name,
                "url": person_url,
                "date": date,
            }

            # Get declaration contents
            holder = holders[1] # Section B is always the second block of text
            content = holder.findall(".//*")
            declaration = copy.deepcopy(base_declaration)
            for element in content:
                # declarations are alternating <p> with the question and <ul> with the answer
                # ..except when it's not, and it's just all <p>s
                for field, number in declaration_mapping.items():
                    if element.tag == "p" and element.text is not None and number in element.text:
                        next_element = element.getnext()
                        if len(next_element) and next_element.tag == "ul":
                            
                            # This should be the answer
                            # There might be multiple things in the list
                            response = []
                            for li in next_element.findall(".//li"):
                                if li is not None and li.text is not None:
                                    response.append(li.text.strip())

                            if response:
                                declaration[field] = "|".join(response)

                        elif len(next_element) and next_element.tag == "p":
                            # This should be the answer
                            # multiple declarations are separated by newlines
                            # ..but sometimes the newlines don't actually denote a new declaration
                            if next_element.text:
                                lis = next_element.text_content().split("\n")
                                lis = [t.strip() for t in lis]
                                if len(lis):
                                    declaration[field] = "|".join(lis)
                
            
            context.emit(rule="store", data=declaration)

