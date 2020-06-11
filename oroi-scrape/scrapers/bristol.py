import copy
import lxml

from memorious.helpers.key import make_id


def improve_register_date(datestring):
    """
    These dates are so terribly formatted that generic fuzzy date
    parsing can't handle them. This doesn't parse them completely,
    (because we don't want to mess with the source data too much)
    just makes them a little less awful for future processing.

    ie. "This register of interests was published on Wednesday, 22nd June, 2016, 12.16 pm."
    """
    datestring = datestring.replace("This register of interests was published on ", "")
    datestring = datestring.replace(" pm.", "PM")
    datestring = datestring.replace(" am.", "AM")
    datestring = datestring.replace(".", ":")
    return datestring


def get_register(context, data):
    """
    bristol_register
    Get the register of interest and some data from a council member page
    """
    with context.http.rehash(data) as result:
        if result.html is not None:
            holder = result.html.find(".//div[@id='modgov']")
            h1 = holder.find(".//h1")
            name = h1.text
            links = holder.findall(".//li/a")
            for link in links:
                if "register of interest" in link.text.lower():
                    url = "{}{}".format(context.get("base"), link.get("href"))
                    context.emit(
                        data={"member_name": name, "member_url": result.url, "url": url}
                    )


def parse_register(context, data):
    """
    bristol_register
    Parse the declarations from the register of interest page
    Sections are:
        1. Employment, trade, profession or vocation
        2. Sponsorship
        3. Contracts
        4. Land in the area of the authority
        5. Licences to occupy land
        6. Corporate tenancies
        7. Securities
        8. Membership of organisations
        9. Gifts and hospitality
    """

    declaration_mapping = {
        "1.": "employment_and_earnings",
        "2.": "donations_sponsorship",
        "3.": "contracts",
        "4.": "land_and_property",
        "5.": "contracts",
        "6.": "contracts",
        "7.": "securities_and_shareholdings",
        "8.": "positions",
        "9.": "gift",
    }

    notes_mapping = {
        "5.": "Contract type: licenses to occupy land",
        "6.": "Contract type: corporate tenancies",
        "8.": "Position type: membership of organisations",
    }

    with context.http.rehash(data) as result:
        output_base = {
            "source": result.url,
            "source_id": make_id(result.url, data.get("member_name")),
            "member_name": data.get("member_name"),
            "member_url": data.get("member_url"),
            "declared_to": "Bristol City Council",
        }

        if result.html is not None:
            holder = result.html.find(".//div[@id='modgov']")

            bullets = holder.findall(".//div[@class='mgLinks']//li")
            declared_date = improve_register_date(bullets[0].text)
            output_base["declared_date"] = declared_date
            output_base["registration_id"] = make_id(
                result.url, data.get("member_name"), output_base.get("declared_date")
            )

            content = holder.find(".//div[@class='mgDeclarations']")
            declarations = content.findall(".//table")
            for declaration in declarations:
                question = declaration.find(".//caption").text
                for number, field in declaration_mapping.items():
                    if number in question:
                        output = copy.deepcopy(output_base)

                        output["interest_type"] = declaration_mapping.get(number)
                        output["declaration_id"] = make_id(
                            result.url,
                            data.get("member_name"),
                            output.get("interest_type"),
                        )
                        if notes_mapping.get(number) is not None:
                            output["notes"] = notes_mapping.get(number)

                        if field == "gift":
                            # Gifts are in a two-column table with "donor/description" and "date"
                            rows = declaration.findall(".//tr")
                            for row in rows:
                                cells = row.findall(".//td")
                                if len(cells):
                                    output["description"] = cells[0].text_content()
                                    output["interest_date"] = cells[1].text_content()

                                    output["interest_hash"] = make_id(
                                        output.get("interest_type"),
                                        output.get("description"),
                                        output.get("interest_date"),
                                        output.get("interest_from"),
                                        output.get("member_name"),
                                    )

                                    context.emit(rule="store", data=output)

                        else:
                            # All other tables are just rows with a single cell
                            answers = declaration.findall(".//td")
                            for answer in answers:
                                output["description"] = (
                                    answer.text_content()
                                    .replace("\r", "")
                                    .replace("\n", "")
                                    .strip()
                                )
                                output["interest_hash"] = make_id(
                                    output.get("interest_type"),
                                    output.get("description"),
                                    output.get("interest_date"),
                                    output.get("interest_from"),
                                    output.get("member_name"),
                                )

                                context.emit(rule="store", data=output)


def parse_meetings(context, data):
    """
    bristol_meetings
    Parse the listing of meetings
    """
    url_base = "https://democracy.bristol.gov.uk/"
    with context.http.rehash(data) as result:
        if result.html is not None:
            content = result.html.find(".//div[@id='modgov']/div[@class='mgContent']")
            declaration_lists = content.findall(".//ul")
            for declaration_list in declaration_lists:
                meeting_section_ele = declaration_list.getprevious()
                meeting_ele = meeting_section_ele.getprevious()

                meeting_link = "{}{}".format(
                    url_base, meeting_ele.find(".//a").get("href")
                )
                meeting_info = meeting_ele.find(".//a").text_content().split(" - ")
                meeting_date = meeting_info[0].strip()
                meeting_group = meeting_info[1].strip()

                declaration_eles = declaration_list.findall(".//li")
                for item in declaration_eles:
                    person_ele = item.find(".//a")
                    member_name = person_ele.text.strip()
                    member_url = "{}{}".format(url_base, person_ele.get("href"))
                    description = item.text_content()
                    description = description.replace(
                        "{} - ".format(member_name), ""
                    ).strip()

                    output = {
                        "source": meeting_link,
                        "source_id": make_id(meeting_link, member_name),
                        "declared_date": meeting_date,
                        "declared_to": "Bristol City Council ({})".format(
                            meeting_group
                        ),
                        "member_name": member_name.strip(),
                        "member_url": member_url,
                        "registration_id": make_id(
                            meeting_link, member_name, meeting_date
                        ),
                        "declaration_id": make_id(
                            meeting_link, member_name, "positions"
                        ),
                        "interest_type": "positions",
                        "description": description,
                        "interest_hash": make_id("positions", description, member_name),
                    }

                    context.emit(data=output)
