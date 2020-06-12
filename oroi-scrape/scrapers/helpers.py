from memorious.helpers.key import make_id


def improve_register_date(datestring):
    """
    Some dates are so terribly formatted that generic fuzzy date
    parsing can't handle them. This doesn't parse them completely,
    (because we don't want to mess with the source data too much)
    just makes them a little less awful for future processing.

    ie. "This register of interests was published on Wednesday, 22nd June, 2016, 12.16 pm."
    """
    datestring = datestring.replace("This register of interests was published on ", "")
    datestring = datestring.replace(" pm.", "PM").replace(" pm", "PM")
    datestring = datestring.replace(" am.", "AM").replace(" am", "AM")
    datestring = datestring.replace(".", ":")
    return datestring


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
