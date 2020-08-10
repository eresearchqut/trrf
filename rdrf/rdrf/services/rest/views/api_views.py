from functools import cached_property
from operator import attrgetter
import pycountry

from django.db.models import Q
from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, BasePermission
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.views import APIView

from registry.patients.models import Patient, Registry, PatientStage, NextOfKinRelationship
from registry.groups.models import CustomUser
from rdrf.models.definition.models import RegistryForm
from rdrf.services.rest.serializers import CustomUserSerializer, PatientSerializer, NextOfKinRelationshipSerializer
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.security.security_checks import security_check_user_patient


import logging
logger = logging.getLogger(__name__)


class BadRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser


class NextOfKinRelationshipDetail(generics.RetrieveAPIView):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class NextOfKinRelationshipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class PatientDetail(generics.RetrieveAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = (IsAuthenticated,)

    def _get_registry_by_code(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise BadRequestError("Invalid registry code '%s'" % registry_code)

    def check_object_permissions(self, request, patient):
        """We're always filtering the patients by the registry code form the url and the user's working groups"""
        super().check_object_permissions(request, patient)
        security_check_user_patient(request.user, patient)


class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsSuperUser, )
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class ListCountries(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, format=None):
        countries = sorted(pycountry.countries, key=attrgetter('name'))

        def to_dict(country):
            # wanted_fields = ('name', 'alpha_2', 'alpha_3', 'numeric', 'official_name')
            wanted_fields = ('name', 'numeric', 'official_name')
            aliases = {
                'alpha_2': 'country_code',
                'alpha_3': 'country_code3',
            }

            d = dict([(k, getattr(country, k, None)) for k in wanted_fields])
            for attr, alias in aliases.items():
                d[alias] = getattr(country, attr)
            d['states'] = reverse('state_lookup', args=[country.alpha_2], request=request)

            return d

        return Response(list(map(to_dict, countries)))


class ListStates(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, country_code, format=None):
        try:
            states = sorted(pycountry.subdivisions.get(
                country_code=country_code), key=attrgetter('name'))
        except KeyError:
            # For now returning empty list because the old api view was doing the same
            # raise BadRequestError("Invalid country code '%s'" % country_code)
            states = []

        wanted_fields = ('name', 'code', 'type', 'country_code')

        def to_dict(x):
            return dict([(k, getattr(x, k)) for k in wanted_fields])

        return Response(list(map(to_dict, states)))


class LookupIndex(APIView):
    queryset = Patient.objects.none()

    def get(self, request, registry_code, format=None):
        term = ""
        try:
            term = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")
        registry = Registry.objects.get(code=registry_code)

        if not registry.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            return Response([])

        query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
            Q(working_groups__in=request.user.working_groups.all(), active=True)

        def to_dict(patient):
            return {
                'pk': patient.pk,
                "class": "Patient",
                'value': patient.pk,
                'label': "%s" % patient,
            }

        return Response(
            list(map(to_dict, [p for p in Patient.objects.filter(query) if p.is_index])))


class RegistryFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistryForm
        fields = ('id', 'name', 'nice_name')


class RegistryForms(generics.ListAPIView):
    serializer_class = RegistryFormSerializer

    def get_queryset(self):
        return RegistryForm.objects.get_by_registry(self.kwargs.get('registry_id'))


class PatientStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientStage
        fields = ('id', 'name')


class PatientStages(generics.ListAPIView):
    serializer_class = PatientStageSerializer

    @cached_property
    def registry(self):
        registry_id = self.kwargs.get('registry_id')
        registry = Registry.objects.filter(pk=registry_id).first()
        if registry is None or not registry.has_feature(RegistryFeatures.STAGES):
            raise NotFound
        return registry

    def check_permissions(self, request):
        user = request.user
        if user.is_superuser:
            return
        if not user.in_registry(self.registry):
            raise PermissionDenied

    def get_queryset(self):
        return PatientStage.objects.filter(registry=self.registry)
