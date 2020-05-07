from django.urls import re_path
from rdrf.services.rest.views import api_views
from rdrf.routing.custom_rest_router import DefaultRouterWithSimpleViews


router = DefaultRouterWithSimpleViews()
router.register(r'countries', api_views.ListCountries, basename='country')
router.register(r'users', api_views.CustomUserViewSet)
router.register(r'registries/(?P<registry_code>\w+)/indices',
                api_views.LookupIndex, basename='index')

urlpatterns = [
    re_path(r'registries/(?P<registry_code>\w+)/patients/(?P<pk>\d+)/$',
            api_views.PatientDetail.as_view(), name='patient-detail'),
    re_path(r'^countries/(?P<country_code>[A-Z]{2})/states/$',
            api_views.ListStates.as_view(), name="state_lookup"),
    re_path(r'registries/(?P<registry_id>\d+)/forms/$',
            api_views.RegistryForms.as_view(), name='registry-forms'),
    re_path(r'registries/(?P<registry_id>\d+)/stages/$',
            api_views.PatientStages.as_view(), name='patient-stages'),

] + router.urls
