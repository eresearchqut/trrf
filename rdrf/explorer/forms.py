from django.forms import ModelForm, Select, SelectMultiple, MultipleChoiceField, CheckboxSelectMultiple
from .models import Query


class QueryForm(ModelForm):

    class Meta:
        model = Query
        fields = [
            'id',
            'title',
            'description',
            'registry',
            'access_group',
            'collection',
            'criteria',
            'projection',
            'aggregation',
            'mongo_search_type',
            'sql_query',
            'max_items',
            'created_by'
        ]

class ReportDesignerForm(ModelForm):

    # demographic_fields = MultipleChoiceField(widget=CheckboxSelectMultiple)

    class Meta:
        model = Query
        fields = [
            'id',
            'title',
            'description',
            'registry',
            'access_group'
        ]
        widgets = {
            'registry': Select(attrs={'class': 'form-select'}),
            'access_group': SelectMultiple(attrs={'class': 'form-select'})
        }
