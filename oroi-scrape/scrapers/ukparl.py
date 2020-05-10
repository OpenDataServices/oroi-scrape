import copy
import lxml

def parse_twfy_xml(context, data):
    # Category 1: Employment and earnings 
    # Category 2(a): support received by a local party organisation or indirectly via a central party organisation
    # Category 2(b): any other support received by a Member.
    # Category 3: Gifts, benefits and hospitality from UK sources
    # Category 4: Visits outside the UK
    # Category 5: Gifts and benefits from sources outside the UK
    # Category 6: Land and property 
    # Category 7: Shareholdings 
    # Category 8: Miscellaneous 
    # Category 9: Family members employed 
    # Category 10: Family members engaged in lobbying 
    
    with context.http.rehash(data) as result:
        
        if result.xml is not None:
            entries = result.xml.findall(".//regmem")
            
            for entry in entries:
                base_declaration = {
                    "source": result.url,
                    "member_name": entry.get("membername"),
                    "disclosure_date": entry.get("date"),
                    "member_url": entry.get("personid"),
                    "body_received_by": "House of Commons"
                }

                sections = entry.findall(".//category")
                for section in sections:
                    category_declaration = copy.deepcopy(base_declaration)
                    category_declaration["interest_type"] = section.get("name")

                    items = section.findall(".//item")
                    for item in items:
                        declaration = copy.deepcopy(category_declaration)
                        declaration["description"] = "\n".join(item.itertext())

                        context.emit(data=declaration)