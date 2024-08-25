class FormChangesExtractor:
    CDE_SEPARATOR = "____"

    def __init__(self, registry_form, previous_data, dynamic_data):
        self.registry_form = registry_form
        self.previous_data = previous_data
        self.dynamic_data = dynamic_data
        self.allowed_cde = []
        self.form_changes = {}
        self.previous_values = {}

    def extract_cde(self, value):
        return value.split(self.CDE_SEPARATOR)[-1]

    def _extract_cdes_from_multi_section_values(self, multi_section_values):
        result = set()
        for vals in multi_section_values.values():
            for d in vals:
                result.update([self.extract_cde(r) for r in d])
        return list(result)

    def determine_form_changes(self):
        if not self.previous_data:
            return

        self.form_changes = {
            k: v
            for k, v in self.previous_data.items()
            if k in self.dynamic_data and self.dynamic_data[k] != v
        }
        self.allowed_cdes = [
            self.extract_cde(k)
            for k in self.form_changes.keys()
            if self.CDE_SEPARATOR in k
        ]
        self.previous_values = {
            self.extract_cde(k): v
            for k, v in self.previous_data.items()
            if self.CDE_SEPARATOR in k
        }
        sections = [s.code for s in self.registry_form.section_models]
        multi_section_values = {
            k: v for k, v in self.form_changes.items() if k in sections
        }
        self.previous_values.update(multi_section_values)
        self.allowed_cdes.extend(
            self._extract_cdes_from_multi_section_values(multi_section_values)
        )
