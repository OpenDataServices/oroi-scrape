import copy
import lxml
from memorious.helpers import search_results_last_url

"""
gla_gifts
Gets the page no. of the last page so all pages
can be generated in sequence.
"""
def last_page_no(context, data):
    init_url = context.get("url")
    response = context.http.get(init_url)

    # emit this page to parse stage as it gets skipped by the sequence
    # (it has no page no)
    context.emit(rule="parse", data=response.serialize())

    xpath = ".//div/ul[@class='pager']/li"
    last_url = search_results_last_url(response.html, xpath, "last")
    page_no = last_url.split("?page=")[-1]
    context.emit(data={"number": int(page_no)})


"""
gla_gifts
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
                parsed_row["member_name"] = recipient.text.strip()
                parsed_row["member_url"] = recipient.get("href")
                parsed_row["member_role"] = cells[1].text.strip()

                parsed_row["description"] = cells[3].text.strip()
                parsed_row["interest_date"] = cells[2].find(".//span").get("content")
                parsed_row["interest_from"] = cells[4].text.strip()

                parsed_row["interest_type"] = "gift"
                parsed_row["declared_to"] = "Greater London Assembly"
                parsed_row["declared_date"] = "not provided"

                context.emit(rule="store", data=parsed_row)


"""
gla_register - helper
Some fields need disambiguation notes.
"""
def get_extra_data():
    return {
        "contract_description": "Contract is with member/partner/family",
        "contract_partner_description": "Contract is with a firm of which member/partner/family is a partner",
        "contract_director_description": "Contract is with a corporate body of which member/partner/family is a director",
        "contract_securities_description": "Contract is with a firm or corporate body in which member/partner/family has a beneficial interest in securities thereof",
        "contract_employee_description": "Contract is with a firm in which member/partner/family is an employee",
        "position_nonprofit_description": "Position is that of declaree or partner, with a nonprofit, as a trustee or participate(s) in management",
        "position_other_description": "Position is any other office or position held not already disclosed elsewhere",
        "position_directorships_description": "Position is a directorship, whether paid or not",
    }


"""
gla_register - helper
Assembles the actual value of a field depending on the surrounding html structure.
"""
def make_value(field, content_element):

    # declarations are alternating <p> with the question and <ul> with the answer
    parsed_content = []
    if content_element.tag == "ul":

        for li in content_element.findall(".//li"):

            if li is not None and li.text_content() is not None:

                content = li.text_content().strip()
                parsed_content.append(content)

    # ..except when it's not, and it's just all <p>s
    elif content_element.tag == "p":
        if content_element.text_content():
            lis = content_element.text_content().split("\n")

            if len(lis):
                for li in lis:
                    content = li.strip()
                    parsed_content.append(content)

    if len(parsed_content):
        return "\n".join(parsed_content)
    else:
        return None


"""
gla_register - init
Parses the sitemap to find all the people
"""
def get_members(context, data):
    base_url = context.get("base")
    sitemap_url = context.get("url")
    sitemap = context.http.get(sitemap_url)
    people = sitemap.html.find(".//div[@id='block-gla-key-person-profile-people-sitemap']")
    links = people.findall(".//div/ul/li/div/ul/li/a")
    for link in links:
        if link.text.strip().lower() == "register of interests":
            url = "{}{}".format(base_url, link.get("href"))
            # context.emit(rule="debug", data={"url": url})
            context.emit(data={"url": url})


"""
gla_register - parse
Parses a declaration of interest
"""
def parse_declaration(context, data):
    declaration_mapping = {
        "1.": "employment_description",
        "2.": "sponsorship_description",
        "3(a).": "contract_description",
        "3(b).": "contract_partner_description",
        "3(c).": "contract_director_description",
        "3(d).": "contract_securities_description",
        "3(e).": "contract_employee_description",
        "4.": "land_description",
        "5.": "contract_land_licence_description",
        "6.": "contract_tenancy_description",
        "7.": "securities_description",
        "8.": "position_nonprofit_description",
        "9.": "position_other_description",
        "10.": "position_directorships_description",
        "11.": "other_description"
    }

    # Some data has evidently come from an entirely different form, with slightly different
    # questions and numbers.
    alt_declaration_mapping = {
        "1(a)(ii)(aa) – ": "position_other_description",
        "1(a)(i) – ": "position_other_description",
        "1(a)(ii)(bb) – ": "position_nonprofit_description",
        "1(a)(ii)(cc) – ": "position_other_description",
        "1(a)(vi) – ": "land_description",
        "1(a)(vii) – ": "contract_description",
        "1(a)(viii) – ": "gifts",
        "1(a)(ix) – ": "land_description",
        "1(a)(x) – ": "contract_tenancy_description",
        "1(a)(xi) – ": "contract_land_licence_description"
    }

    interest_type_mapping = {
        "employment_description": "employment_and_earnings",
        "sponsorship_description": "donations_sponsorships",
        "contract_description": "contracts",
        "contract_partner_description": "contracts",
        "contract_director_description": "contracts",
        "contract_securities_description": "contracts",
        "contract_employee_description": "contracts",
        "land_description": "land_and_property",
        "contract_land_licence_description": "contracts",
        "contract_tenancy_description": "contracts",
        "securities_description": "securities_and_shareholding",
        "position_nonprofit_description": "positions",
        "position_other_description": "positions",
        "position_directorships_description": "positions",
        "other_description": "other"
    }

    parsed_row = {}
    with context.http.rehash(data) as result:
        if result.html is not None:

            # Get name
            nav = result.html.findall(".//nav[@class='breadcrumb']//a")
            profile = nav[-1]
            person_name = profile.text.replace("More about", "").strip()
            person_url = profile.get("href")

            holders = result.html.findall(".//div[@class='content']")
            section_responses = None
            last_block = None
            date = None
            retry_date = False
            if len(holders) > 1:

                for holder in holders:

                    h2 = holder.find(".//h2")
                    if h2 is None:
                        # Sometimes the declaration section has no subheading
                        last_block = holder
                    elif "section b" in h2.text.lower():
                        section_responses = holder
                    elif "declaration" in h2.text.lower():
                        last_block = holder

                # Get the date string from the 'declaration' block
                if last_block is not None:
                    last_block_contents = last_block.findall(".//*")
                    for ele in last_block_contents:

                        if ele.text is not None and ("date" in ele.text.lower() or "declaration:" in ele.text.lower()):
                            date = ele.text

                        if ele.text is None and ("date" in ele.text_content().lower() or "declaration:" in ele.text_content().lower()):
                            lines = ele.text_content().split("\n")

                            for line in lines:
                                if "date" in line.lower() or "declaration:" in line.lower():
                                    date = line

                if date is None:
                    retry_date = True

            else:
                section_responses = holders[0]
                retry_date = True

            if retry_date:
                ps = section_responses.findall(".//p")
                date = ps[-1].text_content()

            try:
                date = date.replace("Date:", "").replace("Declaration date:", "").replace("Original declaration date:", "").strip()
            except Exception as e:
                date = "not found"

            base_declaration = {
                "source": result.url,
                "member_name": person_name,
                "member_url": person_url,
                "declared_to": "Greater London Assembly",
                "declared_date": date,
            }

            try:
                # Get declaration contents
                content = section_responses.findall(".//div[@class='field__items']//*")
                declaration = {}

                for element in content:

                    for number, field in declaration_mapping.items():

                        # This works for pages with some semblence of structure
                        if element.tag == "p" and element.text_content() is not None:

                            if number in element.text_content():

                                next_element = element.getnext()
                                if next_element is not None:
                                    value = make_value(field, next_element)
                                    if declaration.get(field):
                                        declaration[field] = "{}\n{}".format(declaration[field], value)
                                    else:
                                        declaration[field] = value

                    for number, field in alt_declaration_mapping.items():
                        # This catches pages where everything is just <p>s
                        if element.text is not None and number in element.text:

                            ps = []
                            p = element.getnext()

                            while part_of_answer(alt_declaration_mapping, p):
                                answer = p.text_content().strip()

                                ps.append(answer)
                                p = p.getnext()

                            value = "\n".join(ps)
                            if declaration.get(field):
                                declaration[field] = "{}\n{}".format(declaration[field], value)
                            else:
                                declaration[field] = value

            except Exception as e:
                print('-----------------------------------')
                print(person_url)
                print('e {}'.format(e))
                print('-----------------------------------')

            # Parse the declaration into rows for storage
            notes_data = get_extra_data()
            for field, value in declaration.items():
                output = copy.deepcopy(base_declaration)
                output["interest_type"] = interest_type_mapping[field]
                output["description"] = value
                if notes_data.get(field) is not None:
                    output["notes"] = notes_data[field]

                context.emit(rule="store", data=output)



def part_of_answer(mapping, element):
    for number, field in mapping.items():
        if element is None or (element.tag == "p" and number in element.text):
            return False

    return True