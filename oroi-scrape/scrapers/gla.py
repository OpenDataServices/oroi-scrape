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

    xpath = ".//div/ul[@class='pager']/li[@class='pager__item pager__item--last pager__item--special']"
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
                parsed_row["recipient"] = recipient.text.strip()
                parsed_row["recipient_url"] = recipient.get("href")

                parsed_row["recipient_role"] = cells[1].text.strip()
                parsed_row["date_gifted"] = cells[2].find(".//span").get("content")
                parsed_row["details"] = cells[3].text.strip()
                parsed_row["donor"] = cells[4].text.strip()

                context.emit(rule="store", data=parsed_row)


"""
gla_register - helper
Some fields need a string appended to them to keep context after it's parsed.
"""
def get_extra_data():
    return {
        "contract_description": "Contract is with member/partner/family",
        "contract_partner_description": "Contract is with a firm of which member/partner/family is a partner",
        "contract_director_description": "Contract is with a corporate body of which member/partner/family is a director",
        "contract_securities_description": "Contract is with a firm or corporate body in which member/partner/family has a beneficial interest in securities thereof",
        "contract_employee_description": "Contract is with a firm in which member/partner/family is an employee",
    }


"""
gla_register - helper
Assembles the actual value of a field depending on the surrounding html structure.
"""
def make_value(field, content_element):
    additional_content = get_extra_data()

    # declarations are alternating <p> with the question and <ul> with the answer
    parsed_content = []
    if content_element.tag == "ul":

        for li in content_element.findall(".//li"):

            if li is not None and li.text_content() is not None:
                
                content = li.text_content().strip()
                if content != "None" and content != "N/A" and field in additional_content:
                    content = "{} ({})".format(content, additional_content[field])
                
                parsed_content.append(content)

    # ..except when it's not, and it's just all <p>s
    elif content_element.tag == "p":
        if content_element.text_content():
            lis = content_element.text_content().split("\n")
            
            if len(lis):
                for li in lis:
                    content = li.strip()
                    if content != "None" and content != "N/A" and field in additional_content:
                        content = "{} ({})".format(content, additional_content[field])
                    
                    parsed_content.append(content)

    if len(parsed_content):
        return "|".join(parsed_content)
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
            context.emit(rule="debug", data={"url": url})
            context.emit(data={"url": url})


"""
gla_register - parse
Parses a declaration of interest
"""
def parse_declaration(context, data):
    declaration_mapping = {
        "1.": "employment_description",
        "2.": "payment_description",
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

    # These all get merged into one field after they've been parsed
    contract_fields = [
        "contract_description",
        "contract_partner_description",
        "contract_director_description",
        "contract_securities_description",
        "contract_employee_description"
    ]

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
                try:
                    last_block_contents = last_block.findall(".//*")
                    for ele in last_block_contents:
                        if "date:" in ele.text_content().lower():
                            date = ele.text_content()
                except Exception as e:
                    print(result.url)
                    print(e)

            else:
                # Special BoJo layout
                section_responses = holders[0]
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
                "body_received_by": "Greater London Authority",
                "disclosure_date": date,
            }

            additional_content = get_extra_data()

            try:
                # Get declaration contents
                content = section_responses.findall(".//div[@class='field__items']//*")
                declaration = copy.deepcopy(base_declaration)

                for element in content:

                    for number, field in declaration_mapping.items():
                        
                        # This works for pages with some semblence of structure
                        if element.tag == "p" and element.text_content() is not None:
                            
                            if number in element.text_content():
                                
                                next_element = element.getnext()
                                if next_element is not None:
                                    value = make_value(field, next_element)
                                    if declaration.get(field):
                                        declaration[field] = "{}|{}".format(declaration[field], value)
                                    else:
                                        declaration[field] = value

                        # This catches pages where everything is just <p>s
                        # for number, field in alt_declaration_mapping.items():
                    for number, field in alt_declaration_mapping.items():
                        if element.text is not None and number in element.text:
                            
                            ps = []
                            p = element.getnext()

                            while part_of_answer(alt_declaration_mapping, p):
                                if field in additional_content:
                                    answer = "{} ({})".format(p.text_content().strip(), additional_content[field])
                                else:
                                    answer = p.text_content().strip()
                                ps.append(answer)
                                p = p.getnext()
                            
                            value = "|".join(ps)
                            if declaration.get(field):
                                declaration[field] = "{}|{}".format(declaration[field], value)
                            else:
                                declaration[field] = value
                
                # Merge the contract fields together now they've had context strings attached
                contracts = [declaration.get(contract_field) for contract_field in contract_fields if declaration.get(contract_field) is not None]
                for contract_field in contract_fields:
                    if declaration.get(contract_field):
                        declaration.pop(contract_field)

                declaration["contract_description"] = "|".join(contracts)

                context.emit(rule="store", data=declaration)
            
            except Exception as e:
                print('-----------------------------------')
                print(person_url)
                print('e {}'.format(e))
                print(contracts)
                print('-----------------------------------')


def part_of_answer(mapping, element):
    for number, field in mapping.items():
        if element is None or (element.tag == "p" and number in element.text):
            return False
        
    return True