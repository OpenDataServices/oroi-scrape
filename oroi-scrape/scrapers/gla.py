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


def make_value(field, content_element):
    additional_content = {
        "contract_description": "a",
        "contract_partner_description": "b",
        "contract_director_description": "c",
        "contract_securities_description": "d",
        "contract_employee_description": "e",
    }

    # declarations are alternating <p> with the question and <ul> with the answer
    if content_element.tag == "ul":
        parsed_content = []

        for li in content_element.findall(".//li"):
            if li is not None and li.text is not None:
                parsed_content.append(li.text.strip())

        if len(parsed_content):
            contents = "|".join(response)

    # ..except when it's not, and it's just all <p>s
    elif next_element.tag == "p":
        if next_element.text:
            lis = next_element.text_content().split("\n")
            lis = [t.strip() for t in lis]
            if len(lis):
                contents = "|".join(lis)

    if field in additional_content:
        return "{} ({})".format(contents, additional_content[field])
    else:
        return contents


"""
Parses a declaration of interest
"""
def parse_declaration(context, data):
    declaration_mapping = {
        "employment_description": "1.",
        "payment_description": "2.",
        "contract_description": "3(a).",
        "contract_partner_description": "3(b).",
        "contract_director_description": "3(c).",
        "contract_securities_description": "3(d).",
        "contract_employee_description": "3(e).",
        "land_description": "4.",
        "contract_land_licence_description": "5.",
        "contract_tenancy_description": "6.",
        "securities_description": "7.",
        "position_nonprofit_description": "8.",
        "position_other_description": "9.",
        "position_directorships_description": "10.",
        "other_description": "11."
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
            last_block = holders[2] ## HERENOW sometimes otu of range .. maybe https://www.london.gov.uk/people/mayoral/munira-mirza-past-staff/register-of-interests
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
                "member_name": person_name,
                "member_url": person_url,
                "body_received_by": "Greater London Authority",
                "disclosure_date": date,
            }

            # Get declaration contents
            holder = holders[1] # Section B is always the second block of text
            content = holder.findall(".//*")
            declaration = copy.deepcopy(base_declaration)
            for element in content:
                for field, number in declaration_mapping.items():
                    if element.tag == "p" and element.text is not None and number in element.text:
                        next_element = element.getnext()
                        declaration[field] = make_value(field, next_element)
                
            
            context.emit(rule="store", data=declaration)

