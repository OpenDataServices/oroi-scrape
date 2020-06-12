import copy

from memorious.helpers.key import make_id
from scrapers.bristol import improve_register_date


def make_hashes(output):
    output["source_id"] = make_id(output.get("source"), output.get("member_name"))
    output["registration_id"] = make_id(
        output.get("source"), output.get("member_name"), output.get("declared_date"),
    )
    output["declaration_id"] = make_id(
        output.get("source"), output.get("member_name"), output.get("interest_type"),
    )
    output["interest_hash"] = make_id(
        output.get("interest_type"),
        output.get("description"),
        output.get("interest_date"),
        output.get("interest_from"),
        output.get("member_name"),
    )

    return output


def parse_register(context, data):
    """southglos_register

    Parse the declaration page
    """
    base_url = "https://council.southglos.gov.uk/"

    declaration_mapping = {
        "1.": "employment_and_earnings",
        "2.": "donations_sponsorship",
        "3.": "contracts",
        "4.": "land_and_property",
        "5.": "contracts",
        "6.": "contracts",
        "7.": "securities_and_shareholding",
        "8.": "other",
        "9.": "gift",
    }

    notes_mapping = {
        "5.": "Contract type: licenses to occupy land",
        "6.": "Contract type: corporate tenancies",
        "8.": "Other Regsiterable Non Pecuniary Interest",
    }

    with context.http.rehash(data) as result:
        output_base = {
            "source": result.url,
            "member_name": data.get("member_name"),
            "declared_to": "South Gloucestershire City Council",
        }
        if result.html is not None:
            topbox = result.html.find(".//div[@id='content']//div[@class='mgLinks']")
            bullets = topbox.findall(".//ul/li")

            declared_date = None
            member_url = None

            for bullet in bullets:
                if (
                    "register of interests was published"
                    in bullet.text_content().lower()
                ):
                    declared_date = improve_register_date(bullet.text_content().strip())

                if "information about this councillor" in bullet.text_content().lower():
                    member_url = bullet.find(".//a").get("href")

            if declared_date is not None:
                output_base["declared_date"] = declared_date
            if member_url is not None:
                output_base["member_url"] = "{}{}".format(base_url, member_url)

            declaration_form = result.html.find(".//div[@id='content']//form")
            for entry in declaration_form.findall(".//table"):
                question = entry.find(".//caption").text
                answer = entry.findall(".//tr")
                for number, field in declaration_mapping.items():
                    if number in question:
                        output = copy.deepcopy(output_base)

                        output["interest_type"] = declaration_mapping.get(
                            number, "other"
                        )
                        if notes_mapping.get(number) is not None:
                            output["notes"] = notes_mapping.get(number)

                        if number == "8.":
                            # one column
                            lines = entry.findall(".//td")
                            for line in lines:
                                output["description"] = line.text_content().strip()

                                output = make_hashes(output)
                                context.emit(rule="store", data=output)

                        elif number == "9.":
                            # two columns: gift including date and donor
                            for row in answer:
                                cols = row.findall(".//td")
                                if cols:
                                    if (
                                        cols[0].text_content().lower().strip() != "none"
                                        and cols[0].text_content().strip() != "-"
                                        and cols[0].text_content().strip() != ""
                                    ):
                                        output["description"] = (
                                            cols[0].text_content().strip()
                                        )
                                        output["interest_from"] = (
                                            cols[1].text_content().strip()
                                        )

                                        output = make_hashes(output)
                                        context.emit(rule="store", data=output)
                        else:
                            # two columns: Your interest and Spouse/Civil partner interests
                            for row in answer:
                                cols = row.findall(".//td")
                                if cols:
                                    if (
                                        cols[0].text_content().lower().strip() != "none"
                                        and cols[0].text_content().strip() != "-"
                                        and cols[0].text_content().strip() != ""
                                    ):
                                        output["description"] = (
                                            cols[0].text_content().strip()
                                        )
                                        output = make_hashes(output)
                                        context.emit(rule="store", data=output)
                                    if (
                                        cols[1].text_content().lower().strip() != "none"
                                        and cols[1].text_content().strip() != "-"
                                        and cols[1].text_content().strip() != ""
                                    ):
                                        output["description"] = (
                                            cols[1].text_content().strip()
                                        )
                                        output[
                                            "notes"
                                        ] = "Spouse, Partner, Civil, Partner's Interests"

                                        output = make_hashes(output)
                                        context.emit(rule="store", data=output)
