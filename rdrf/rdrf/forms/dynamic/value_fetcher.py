class DynamicValueFetcher:
    def __init__(self, dynamic_data):
        self.dynamic_data = dynamic_data

    def find_cde_values(self, form_name, section_code, cde_code):
        if self.dynamic_data is None:
            return []
        for form_dict in self.dynamic_data["forms"]:
            if form_dict["name"] == form_name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section_code:
                        if not section_dict["allow_multiple"]:
                            return [
                                cde_dict["value"]
                                for cde_dict in section_dict["cdes"]
                                if cde_dict["code"] == cde_code
                            ]
                        else:
                            return [
                                cde_dict["value"]
                                for section_item in section_dict["cdes"]
                                for cde_dict in section_item
                                if cde_dict["code"] == cde_code
                            ]
        return []

    def get_value_from_dynamic_data(self, form_name, section_code, cde_code):
        values = self.find_cde_values(form_name, section_code, cde_code)
        return values[0] if values else None

    def get_values_from_multisection(self, form_name, section_code, cde_code):
        return self.find_cde_values(form_name, section_code, cde_code)
