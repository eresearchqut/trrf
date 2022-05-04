from rest_framework import serializers
from rest_framework.reverse import reverse

from rdrf.models.definition.models import ClinicalData
from registry.patients.models import Patient, Registry, NextOfKinRelationship
from registry.groups.models import CustomUser


class NextOfKinRelationshipHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = "nextofkinrelationship-detail"


class NextOfKinRelationshipSerializer(serializers.HyperlinkedModelSerializer):
    url = NextOfKinRelationshipHyperlinkId(read_only=True, source='*')

    class Meta:
        model = NextOfKinRelationship
        fields = "__all__"


# Needed so we can display the URL to the patient that also has the registry code in it
class PatientHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = 'patient-detail'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'pk': obj.pk,
            'registry_code': request.resolver_match.kwargs['registry_code'],
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class CustomUserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = CustomUser
        # TODO add groups and user_permissions as well?
        exclude = ('groups', 'user_permissions', 'password', 'working_groups', 'registry', 'url')
        extra_kwargs = {
            'registry': {'lookup_field': 'code'},
        }


class PatientSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    url = PatientHyperlinkId(read_only=True, source='*')
    user = CustomUserSerializer(required=False)
    stage = serializers.StringRelatedField()
    clinical_data = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        extra_kwargs = {
            'rdrf_registry': {'required': False, 'lookup_field': 'code'},
            'consent': {'required': True},
        }
        exclude = ('rdrf_registry', 'working_groups', 'created_by')

    def get_clinical_data(self, instance):
        entry = ClinicalData.objects\
            .filter(django_model="Patient", django_id=instance.id, collection="cdes")\
            .order_by("last_updated_at").first()
        return entry.data if entry else None


class RegistryHyperlink(serializers.HyperlinkedRelatedField):

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'registry_code': obj.code,
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request, format=format)


class CliniciansHyperlink(RegistryHyperlink):
    view_name = 'clinician-list'


class PatientsHyperlink(RegistryHyperlink):
    view_name = 'patient-list'


class RegistrySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Registry
        fields = (
            'pk',
            'name',
            'code',
            'desc',
            'version',
            'url',
        )
        extra_kwargs = {
            'url': {'lookup_field': 'code'},
        }
