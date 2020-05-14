import copy

"""
bristol_register
Get the register of interest and some data from a council member page
"""
def get_register(context, data):
    with context.http.rehash(data) as result:
        if result.html is not None:
            holder = result.html.find(".//div[@id='modgov']")
            h1 = holder.find(".//h1")
            name = h1.text
            links = holder.findall(".//li/a")
            for link in links:
                if "register of interest" in link.text.lower():
                    url = "{}{}".format(context.get("base"), link.get("href"))
                    context.emit(data={"member_name": name, "member_url": result.url, "url": url})


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
def parse_register(context, data):

    declaration_mapping = {
        "1.": "employment_and_earnings",
        "2.": "donations_sponsorship",
        "3.": "contracts",
        "4.": "land_and_property",
        "5.": "contracts",
        "6.": "contracts",
        "7.": "securities_and_shareholdings",
        "8.": "positions",
        "9.": "gifts",
    }

    notes_mapping = {
        "5.": "Contract type: licenses to occupy land",
        "6.": "Contract type: corporate tenancies",
        "8.": "Position type: membership of organisations"
    }

    with context.http.rehash(data) as result:
        output_base = {
            "source": result.url,
            "member_name": data.get("member_name"),
            "member_url": data.get("member_url"),
            "declared_to": "Bristol City Council",
        }
        if result.html is not None:
            holder = result.html.find(".//div[@id='modgov']")

            bullets = holder.findall(".//div[@class='mgLinks']//li")
            output_base["declared_date"] = bullets[0].text

            content = holder.find(".//div[@class='mgDeclarations']")
            declarations = content.findall(".//table")
            for declaration in declarations:
                question = declaration.find(".//caption").text
                for number, field in declaration_mapping.items():
                    if number in question:
                        output = copy.deepcopy(output_base)

                        output["interest_type"] = declaration_mapping.get(number)
                        if notes_mapping.get(number) is not None:
                            output["notes"] = notes_mapping.get(number)

                        if field == "gifts":
                            # Gifts are in a two-column table with "donor/description" and "date"
                            rows = declaration.findall(".//tr")
                            for row in rows:
                                cells = row.findall(".//td")
                                if len(cells):
                                    output["description"] = cells[0].text_content()
                                    output["interest_date"] = cells[1].text_content()

                                    context.emit(rule="store", data=output)
                        else:
                            # All other tables are just rows with a single cell
                            answers = declaration.findall(".//td")
                            for answer in answers:
                                output["description"] = answer.text_content().replace("\r","").replace("\n","").strip()
                                context.emit(rule="store", data=output)

