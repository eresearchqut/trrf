from rdrf.helpers.cde_data_types import CDEDataTypes


class CdeMappings:

    DATA_TYPE_MAPPING = {
        "Boolean": CDEDataTypes.BOOL,
        "Calculated": CDEDataTypes.CALCULATED,
        "calculation": CDEDataTypes.CALCULATED,
        "Date": CDEDataTypes.DATE,
        "File": CDEDataTypes.FILE,
        "Float": CDEDataTypes.FLOAT,
        "Integer": CDEDataTypes.INTEGER,
        "Range": CDEDataTypes.RANGE,
        "String": CDEDataTypes.STRING,
        "text": CDEDataTypes.STRING,
        "Email": CDEDataTypes.EMAIL,
    }

    WIDGET_NAME_MAPPING = {
        "TextArea": "TextAreaWidget",
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
