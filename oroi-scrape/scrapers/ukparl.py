import copy
import lxml
from datetime import datetime


def parse_twfy_xml(context, data):
    def get_interest_type(number, old=False):

        # After and including 2015-06-08
        interest_type_mapping = {
            "1": "employment_and_earnings",
            "2": "donations_sponsorship",
            "3": "gift",
            "4": "overseas_visit",
            "5": "gift",
            "6": "land_and_property",
            "7": "securities_and_shareholding",
            "8": "other",
            "9": "employed_family",
            "10": "lobbying",
        }

        # Up to and including 2015-03-30
        interest_type_mapping_old = {
            "1": "employment_and_earnings",
            "2": "employment_and_earnings",
            "3": "employment_and_earnings",
            "4": "donations_sponsorship",
            "5": "gift",
            "6": "overseas_visit",
            "7": "donations_sponsorship",
            "8": "land_and_property",
            "9": "securities_and_shareholdings",
            "10": "other",
            "11": "other",
        }

        if old:
            return interest_type_mapping_old.get(number, "other")
        else:
            return interest_type_mapping.get(number, "other")

    def get_notes(category_element, old=False):
        if old:
            if (
                category_element.get("type") == "1"
                or category_element.get("type") == "7"
                or category_element.get("type") == "10"
            ):
                return category_element.get("name")
            if category_element.get("type") == "5":
                return "Gifts, benefits and hospitality from UK sources"
        else:
            if category_element.get("type") == "2":
                if "(a)" in category_element.get("name"):
                    return "Support linked to an MP but received by a local party organisation or indirectly via a central party organisation"
                if "(b)" in category_element.get("name"):
                    return "Any other support not included in Category 2(a)"
            if category_element.get("type") == "3":
                return "Gifts, benefits and hospitality from UK sources"
            if category_element.get("type") == "5":
                return "Gifts and benefits from sources outside the UK"
            if category_element.get("type") == "7":
                if "(i)" in category_element.get("name"):
                    return "Shareholdings: over 15% of issued share capital"
                if "(ii)" in category_element.get("name"):
                    return "Other shareholdings, valued at more than £70,000"

        return None

    with context.http.rehash(data) as result:

        if result.xml is not None:
            try:
                entries = result.xml.findall(".//regmem")
            except AssertionError as e:
                entries = []
                context.log.warning("Could not parse {}: {}".format(result.url, e))

            for entry in entries:

                date = entry.get("date")

                # The category number to description mapping changes on 2015-06-08
                dateobj = datetime.strptime(date, "%Y-%m-%d")
                new_categories_date = datetime(2015, 6, 8)
                print(dateobj)
                if dateobj >= new_categories_date:
                    old = False
                else:
                    old = True

                base_declaration = {
                    "source": result.url,
                    "member_name": entry.get("membername"),
                    "disclosure_date": date,
                    "member_url": entry.get("personid"),
                    "body_received_by": "House of Commons",
                }

                sections = entry.findall(".//category")
                for section in sections:
                    category_declaration = copy.deepcopy(base_declaration)
                    category_declaration["interest_type"] = get_interest_type(
                        str(section.get("type")), old
                    )
                    notes = get_notes(section, old)
                    if notes is not None:
                        category_declaration["notes"] = notes

                    items = section.findall(".//item")
                    for item in items:
                        declaration = copy.deepcopy(category_declaration)
                        declaration["description"] = "\n".join(item.itertext())

                        context.emit(data=declaration)


"""
ukparl_groups
Parses the contents of the group pages
"""


def parse_group(context, data):
    declaration = {}

    with context.http.rehash(data) as result:
        if result.html is not None:
            content = result.html.findall(".//div[@id='mainTextBlock']//table")

            group_name = result.html.find(
                ".//div[@id='mainTextBlock']/h1/span"
            ).text_content()

            benefits_in_kind = None
            for table in content:
                rows = table.findall(".//tr")
                row_header = rows[0].text_content().strip().lower()
                if row_header == "officers":
                    officers = parse_group_officers(table)

                # TODO: does this table ever contain data or is it actually just
                #       a subheading?
                # if row_header == "registrable benefits received by the group":
                #     benefits = parse_group_benefits(table)

                if row_header == "benefits in kind":
                    benefits_in_kind = parse_group_benefits_in_kind(table)

            declaration_base = {
                "source": result.url,
                "declared_to": "UK Parliament",
                "interest_type": "other",
            }

            if benefits_in_kind is not None and len(benefits_in_kind) > 0:
                for benefit in benefits_in_kind:
                    declaration_benefit = copy.deepcopy(declaration_base)
                    for field in benefit.keys():
                        declaration_benefit[field] = benefit[field]

                    for officer in officers:
                        declaration = copy.deepcopy(declaration_benefit)
                        declaration["member_name"] = officer["name"]
                        declaration["member_party"] = officer["party"]
                        declaration[
                            "member_role"
                        ] = "{} of {} All-Party Parliamentary Group".format(
                            officer["role"], group_name
                        )

                        membership_string = "via role as {} in the {} All-Party Parliamentary Group".format(
                            officer["role"], group_name
                        )

                        declaration["description"] = "{} - {}".format(
                            declaration_benefit["description"], membership_string
                        )

                        if len(declaration) > 0:
                            context.emit(data=declaration)


"""
ukparl_groups
Parses the Officers table
"""


def parse_group_officers(table):
    officers = []
    for row in table.findall(".//tr"):
        cols = row.findall(".//td")
        if len(cols) == 3:
            officer = {}
            if cols[0].text_content().strip() != "Role":
                officer["role"] = cols[0].text_content().strip()

            if cols[1].text_content().strip() != "Name":
                officer["name"] = cols[1].text_content().strip()

            if cols[2].text_content().strip() != "Party":
                officer["party"] = cols[2].text_content().strip()

            if len(officer) > 0:
                officers.append(officer)

    return officers


"""
ukparl_groups
Parses the Registrable benefits table
TODO: find an example of one that is actually filled in, so we know
      what the headers are.. otherwise can't parse this (this might
      not really be a data table though)
"""


def parse_group_benefits(table):
    return []


"""
ukparl_groups
Parses the Benefits In Kind table
"""


def parse_group_benefits_in_kind(table):

    headings = {
        "0": "Source",
        "1": "Description",
        "2": "Value£sInbandsof£1,500",
        "3": "Received",
        "4": "Registered",
    }

    fields = {
        "0": "interest_from",
        "1": "description",
        "2": "interest_value",
        "3": "interest_date",
        "4": "disclosure_date",
    }

    benefits_in_kind = []
    for row in table.findall(".//tr"):
        cols = row.findall(".//td")

        if len(cols) == 5:
            benefit = {}
            for i, col in enumerate(cols):
                if col.text_content().strip().replace("\n", "").replace(
                    " ", ""
                ) != headings.get(str(i)):
                    benefit[fields[str(i)]] = col.text_content().strip()

            if len(benefit) > 0:
                benefits_in_kind.append(benefit)

    return benefits_in_kind
