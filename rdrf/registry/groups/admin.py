from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from .admin_forms import UserChangeForm, RDRFUserCreationForm
from .models import WorkingGroup
from useraudit.models import UserDeactivation

import logging

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
            return self.superuser_fieldsets
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
         'fields': ('is_active', 'require_2_fact_auth', 'prevent_self_unlock', 'is_staff', 'groups', 'registry', 'working_groups')}))

    # only superusers are allowed to make users superuser
    superuser_fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal information', {'fields': ('first_name', 'last_name', 'title', 'email', 'preferred_language')}),
        ('Permissions', {
         'fields': ('is_active', 'require_2_fact_auth', 'prevent_self_unlock', 'is_staff', 'is_superuser', 'groups', 'registry', 'working_groups')}),
    )

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


admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.register(WorkingGroup, WorkingGroupAdmin)
