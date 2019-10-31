class CdeMappings:

    DATA_TYPE_MAPPING = {
        "Boolean": "boolean",
        "Calculated": "calculated",
        "calculation": "calculated",
        "Date": "date",
        "File": "file",
        "Float": "float",
        "Integer": "integer",
        "Range": "range",
        "String": "string",
        "text": "string"
    }

    WIDGET_NAME_MAPPING = {
        "TextArea": "Textarea",
        "TextAreaWidget": "Textarea",
        "PercentageWidget": "",
    }

    @classmethod
    def _case_insensitive_search(cls, key, target_dict):
        for k, v in target_dict.items():
            if k.lower() == key.lower():
                return v
        return key

    @classmethod
    def fix_data_type(cls, data_type):
        return cls._case_insensitive_search(data_type, cls.DATA_TYPE_MAPPING)

    @classmethod
    def fix_widget_name(cls, widget_name):
        return cls._case_insensitive_search(widget_name, cls.WIDGET_NAME_MAPPING)
