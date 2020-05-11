import logging

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.utils.encoding import force_text
from django.utils.translation import gettext as _

from useraudit.admin import LogAdmin
from useraudit.models import FailedLoginLog, LoginLog, UserDeactivation

from rdrf.helpers.registry_features import RegistryFeatures

from .admin_forms import UserChangeForm, RDRFUserCreationForm
from .models import WorkingGroup


logger = logging.getLogger(__name__)


class WorkingGroupAdmin(admin.ModelAdmin):
    search_fields = ["name"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return WorkingGroup.objects.all()

        user = request.user

        return WorkingGroup.objects.filter(id__in=user.working_groups.all())


class CustomUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = RDRFUserCreationForm

    list_display = ('username', 'email', 'get_working_groups', 'get_registries', 'status')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.user = request.user
        return form

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        if request.user.is_superuser:
            return self.superuser_fieldsets(obj)
        return super().get_fieldsets(request, obj)

    def get_queryset(self, request):
        from django.db.models import Q

        if request.user.is_superuser:
            return get_user_model().objects.all()

        filter1 = Q(working_groups__in=request.user.working_groups.all()) | Q(
            working_groups__isnull=True)
        filter2 = Q(registry__in=request.user.registry.all())

        filtered = get_user_model().objects.filter(filter1).filter(
            filter2).distinct().filter(is_superuser=False)

        return filtered

    def get_working_groups(self, user):
        return ", ".join(wg.name for wg in user.working_groups.all())

    def get_registries(self, user):
        return ", ".join(reg.name for reg in user.registry.all())

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'registry', 'working_groups')}
         ),
    )

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal information', {'fields': ('first_name', 'last_name', 'title', 'email', 'preferred_language')}),
        ('Permissions', {
         'fields': ('is_active', 'require_2_fact_auth', 'force_password_change', 'prevent_self_unlock', 'is_staff', 'groups', 'registry', 'working_groups')}))

    # only superusers are allowed to make users superuser
    def superuser_fieldsets(self, user):
        def get_permision_fields(user):
            base_fields = ['is_active', 'require_2_fact_auth', 'force_password_change', 'prevent_self_unlock', 'is_staff', 'is_superuser',
                           'groups', 'registry', 'working_groups']
            show_ethically_cleared = any(r.has_feature(RegistryFeatures.CLINICIAN_ETHICAL_CLEARANCE) for r in user.registry.all())
            if show_ethically_cleared:
                base_fields.append('ethically_cleared')
            return tuple(base_fields)

        fieldset = (
            (None, {'fields': ('username', 'password')}),
            ('Personal information', {'fields': ('first_name', 'last_name', 'title', 'email', 'preferred_language')}),
            ('Permissions', {
                'fields': get_permision_fields(user)
            }),
        )
        return fieldset

    get_working_groups.short_description = "Working Groups"
    get_registries.short_description = "Registries"

    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

    def status(self, user):
        if user.is_active:
            return 'Active'
        choices = dict(UserDeactivation.DEACTIVATION_REASON_CHOICES)
        last_deactivation = UserDeactivation.objects.filter(
            username=user.username).order_by('-timestamp').first()
        if last_deactivation is None or last_deactivation.reason not in choices:
            return 'Inactive'

        reason = choices[last_deactivation.reason]

        return 'Inactive (%s)' % reason


class CustomLoginLogFilter(admin.SimpleListFilter):
    title = _('Users')

    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        return (
            ('all', _('All')),
            ('regular', _('Regular users')),
            ('other', _('Other')),
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            value_text = force_text(self.value())
            lookup_text = force_text(lookup)
            yield {
                'selected': value_text == lookup_text if self.value() else 'regular' == lookup_text,
                'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        value = self.value()
        is_default_value = not value or value == 'regular'
        if is_default_value:
            return queryset.exclude(username__in=settings.LOGIN_LOG_FILTERED_USERS)
        elif value == 'other':
            return queryset.filter(username__in=settings.LOGIN_LOG_FILTERED_USERS)
        return queryset


class CustomLoginLogAdmin(LogAdmin):
    list_filter = ['timestamp', CustomLoginLogFilter]


admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.register(WorkingGroup, WorkingGroupAdmin)

admin.site.unregister(LoginLog)
admin.site.register(LoginLog, CustomLoginLogAdmin)

admin.site.unregister(FailedLoginLog)
admin.site.register(FailedLoginLog, CustomLoginLogAdmin)
