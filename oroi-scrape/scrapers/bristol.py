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
        "1.": "employment_description",
        "2.": "sponsorship_description",
        "3.": "contract_description",
        "4.": "land_description",
        "5.": "contract_land_licence_description",
        "6.": "contract_tenancy_description",
        "7.": "securities_description",
        "8.": "position_membership_description",
        "9.": "gifts",
    }

    with context.http.rehash(data) as result:
        output = {
            "source": result.url,
            "member_name": data.get("member_name"),
            "member_url": data.get("member_url"),
            "body_received_by": "Bristol City Council",
        }
        if result.html is not None:
            holder = result.html.find(".//div[@id='modgov']")
            
            bullets = holder.findall(".//div[@class='mgLinks']//li")
            output["disclosure_date"] = bullets[0].text
            
            content = holder.find(".//div[@class='mgDeclarations']")
            declarations = content.findall(".//table")
            for declaration in declarations:
                for number, field in declaration_mapping.items():
                    question = declaration.find(".//caption").text
                    if number in question:
                        parsed = []
                        if field == "gifts":
                            # Gifts are in a two-column table with "donor/description" and "date"
                            rows = declaration.findall(".//tr")
                            for row in rows:
                                cells = row.findall(".//td")
                                if len(cells):
                                    output["gift_reason"] = cells[0].text_content()
                                    output["gift_date"] = cells[1].text_content()
                        else:
                            # All other tables are just rows with a single cell
                            answers = declaration.findall(".//td")
                            for answer in answers:
                                parsed.append(answer.text_content())

                            output[field] = "|".join([ans.replace("\r","").replace("\n","").strip() for ans in parsed])

            context.emit(rule="store", data=output)
