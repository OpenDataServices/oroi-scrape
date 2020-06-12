import copy
import json

from memorious.helpers.key import make_id


def get_data(context, data):
    data = """
[
{
    "member_name": "Dr Elizabeth Weir",
    "member_url": "https://data.example/person/elizabeth",
    "source": "https://data.example/roi/1",
    "declared_to": "Test",
    "declared_date": "2020-01-01",
    "declarations": [
        {
            "interest_type": "employment_and_earnings",
            "notes": "",
            "description": ["Head of SGC", "Lead Negotiator"]
        }
    ]
},
{
    "member_name": "Dr Daniel Jackson",
    "member_url": "https://data.example/person/daniel",
    "source": "https://data.example/roi/3",
    "declared_to": "Test",
    "declared_date": "2020-01-01",
    "declarations": [
        {
            "interest_type": "positions",
            "notes": "",
            "description": ["Ascended being", "Archaeologist at SGC", "Member of SG1"]
        },
        {
            "interest_type": "contracts",
            "notes": "",
            "description": ["Agreement with the ancients not to meddle"]
        }
    ]
},
{
    "member_name": "Ba'al",
    "member_url": "https://data.example/person/baal",
    "source": "https://data.example/roi/4",
    "declared_to": "Test",
    "declared_date": "2020-01-01",
    "declarations": [
        {
            "interest_type": "employed_family",
            "notes": "",
            "description": ["I have several clones"]
        },
        {
            "interest_type": "contracts",
            "notes": "",
            "description": ["Agreement with SGC to protect me from murderous clones"]
        }
    ]
},
{
    "member_name": "Dr Elizabeth Weir",
    "member_url": "https://data.example/person/elizabeth",
    "source": "https://data.example/roi/1",
    "declared_to": "Test",
    "declared_date": "2020-04-01",
    "declarations": [
        {
            "interest_type": "employment_and_earnings",
            "notes": "",
            "description": ["Head of Atlantis Expedition", "Lead Negotiator"]
        },
        {
            "interest_type": "donations_sponsorship",
            "notes": "",
            "description": ["Asgard cloaking device", "Lost City of Atlantis", "Rodney made me a sandwich"]
        }
    ]
},
{
    "member_name": "Major General Hank Landry",
    "member_url": "https://data.example/person/hank",
    "source": "https://data.example/roi/2",
    "declared_to": "Test",
    "declared_date": "2020-04-01",
    "declarations": [
        {
            "interest_type": "employed_family",
            "notes": "",
            "description": ["My daughter Carolyn Lam is the Chief Medical Officer at SG1"]
        },
        {
            "interest_type": "employment_and_earnings",
            "notes": "",
            "description": ["Head of SGC"]
        }
    ]
},
{
    "member_name": "Dr Daniel Jackson",
    "member_url": "https://data.example/person/daniel",
    "source": "https://data.example/roi/3",
    "declared_to": "Test",
    "declared_date": "2020-04-01",
    "declarations": [
        {
            "interest_type": "positions",
            "notes": "",
            "description": ["Archaeologist at SGC", "Member of SG1"]
        }
    ]
},
{
    "member_name": "Ba'al",
    "member_url": "https://data.example/person/baal",
    "source": "https://data.example/roi/4",
    "declared_to": "Test",
    "declared_date": "2020-04-01",
    "declarations": [
        {
            "interest_type": "contracts",
            "notes": "",
            "description": ["An army of loyal Jaffa"]
        }
    ]
}
]
    """

    response = json.loads(data)
    for register in response:
        output_base = {
            "source": register.get("source"),
            "declared_to": register.get("declared_to"),
            "declared_date": register.get("declared_date"),
            "member_name": register.get("member_name"),
            "member_url": register.get("member_url"),
            "source_id": make_id(register.get("source"), register.get("member_name")),
            "registration_id": make_id(
                register.get("source"),
                register.get("member_name"),
                register.get("declared_date"),
            ),
        }
        for declaration in register.get("declarations"):
            for interest in declaration.get("description"):
                output = copy.deepcopy(output_base)
                output["interest_type"] = declaration.get("interest_type")
                output["notes"] = declaration.get("notes")
                output["description"] = interest

                output["declaration_id"] = make_id(
                    register.get("source"),
                    declaration.get("interest_type"),
                    register.get("member_name"),
                )
                output["interest_hash"] = make_id(
                    register.get("member_name"),
                    declaration.get("interest_type"),
                    declaration.get("interest_from"),
                    declaration.get("interest_date"),
                    interest,
                )

                context.emit(data=output)
