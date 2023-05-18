import operator
import re
from functools import reduce

from django.conf import settings
from django.core import validators
from django.contrib.auth.models import AbstractBaseUser, UserManager, PermissionsMixin, Group
from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.dispatch import receiver

from registration.signals import user_activated

from rdrf.helpers.utils import consent_check
from rdrf.models.definition.models import Registry, RegistryDashboard
from registry.groups import GROUPS as RDRF_GROUPS

import logging
logger = logging.getLogger(__name__)


class WorkingGroupType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class WorkingGroupTypeRule(models.Model):
    type = models.ForeignKey(WorkingGroupType, on_delete=models.CASCADE, related_name='rules')
    user_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    has_default_access = models.BooleanField(default=False,
                                             help_text=_('Indicates whether the user group automatically has access to '
                                                         'the working groups in this working group type'))


class WorkingGroupManager(models.Manager):
    UNALLOCATED_GROUP_NAME = 'Unallocated'

    def get_unallocated(self, registry):
        wg, _ = WorkingGroup.objects.get_or_create(name=self.UNALLOCATED_GROUP_NAME, registry=registry)
        return wg

    def get_by_user(self, user):
        if not user.is_superuser:
            filters = [Q(id__in=user.working_groups.all())]

            wg_rules = WorkingGroupTypeRule.objects.filter(user_group__in=user.groups.all(), has_default_access=True)
            for rule in wg_rules:
                filters.append(Q(id__in=rule.type.working_groups.all()))

            query = reduce(lambda a, b: a | b, filters)
            return self.model.objects.filter(query)
        else:
            return self.all()

    def get_by_user_and_registry(self, user, registry):
        return self.get_by_user(user).filter(registry=registry)


class WorkingGroup(models.Model):
    objects = WorkingGroupManager()

    name = models.CharField(max_length=100)
    type = models.ForeignKey(WorkingGroupType, null=True, blank=True, on_delete=models.SET_NULL, related_name='working_groups')
    registry = models.ForeignKey(Registry, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["registry__code", "name"]

    def __str__(self):
        if self.registry:
            return "%s %s" % (self.registry.code, self.name)
        else:
            return self.name

    @property
    def display_name(self):
        if self.registry:
            return "%s %s" % (self.registry.code, self.name)
        else:
            return self.name


class CustomUserManager(UserManager):
    def get_by_natural_key(self, username):
        return self.get(**{f'{self.model.USERNAME_FIELD}__iexact': username})


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _('username'),
        max_length=254,
        unique=True,
        help_text=_('Required. 254 characters or fewer. Letters, numbers and @/./+/-/_ characters'),
        validators=[
            validators.RegexValidator(
                re.compile(r'^[\w.@+-]+$'),
                _('Enter a valid username.'),
                _('invalid'))])
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    email = models.EmailField(_('email address'), max_length=254)
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_(
        'Designates that this user has elevated patient management permissions.'))
    is_active = models.BooleanField(_('active'), default=False, help_text=_(
        'Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    require_2_fact_auth = models.BooleanField(
        _('require two-factor authentication'),
        default=False,
        help_text=_('Requires this user to use two factor authentication to access the system.'))
    force_password_change = models.BooleanField(
        _('force password change'),
        default=False,
        help_text=_('Force this user to change their password to access the system.'))
    prevent_self_unlock = models.BooleanField(_('prevent self unlock'), default=False, help_text=_(
        'Explicitly prevent this user to unlock their account using the Unlock Account functionality.'))

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    working_groups = models.ManyToManyField(
        WorkingGroup, blank=True, related_name='working_groups')
    title = models.CharField(max_length=50, null=True, blank=True, verbose_name="position")
    registry = models.ManyToManyField(Registry, blank=True, related_name='registry')
    password_change_date = models.DateTimeField(auto_now_add=True, null=True)
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=20,
        default="en",
        help_text=_("Preferred language (code) for communications"))
    ethically_cleared = models.BooleanField(null=False, blank=False, default=False)

    USERNAME_FIELD = "username"

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    objects = CustomUserManager()

    @property
    def my_registry(self):
        if self.num_registries == 1:
            return self.registry.first()

    def get_full_name(self):
        full_name = f'{self.first_name} {self.last_name}'

        if self.is_parent:
            from registry.patients.models import ParentGuardian
            parent = ParentGuardian.objects.filter(user=self).first()
            if parent:
                full_name = f'{parent.first_name} {parent.last_name}'

        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    @property
    def num_registries(self):
        return self.registry.count()

    @property
    def registry_code(self):
        if self.num_registries == 1:
            return self.registry.first().code

    @property
    def can_archive(self):
        """
        can user soft delete patients
        """
        value = False

        if self.is_superuser:
            value = True
        else:
            value = self.has_perm("patients.delete_patient")
        return value

    @property
    def notices(self):
        from rdrf.models.definition.models import Notification
        return Notification.objects.filter(
            to_username=self.username,
            seen=False).order_by("-created")

    def in_registry(self, registry_model):
        return self.registry.filter(pk=registry_model.pk).exists()

    def in_group(self, *names):
        return self.groups.filter(reduce(operator.or_, ((Q(name__iexact=name) for name in names)))).exists()

    @property
    def is_patient(self):
        return self.in_group(RDRF_GROUPS.PATIENT)

    @property
    def is_parent(self):
        return self.in_group(RDRF_GROUPS.PARENT)

    @property
    def is_carrier(self):
        return self.in_group(RDRF_GROUPS.CARRIER)

    @property
    def is_carer(self):
        return self.in_group(RDRF_GROUPS.CARER)

    @property
    def is_patient_or_delegate(self):
        return self.in_group(RDRF_GROUPS.PATIENT, RDRF_GROUPS.PARENT, RDRF_GROUPS.CARRIER, RDRF_GROUPS.CARER)

    @property
    def is_clinician(self):
        return self.in_group(RDRF_GROUPS.CLINICAL)

    @property
    def is_working_group_staff(self):
        return self.in_group(RDRF_GROUPS.WORKING_GROUP_STAFF)

    @property
    def is_curator(self):
        return self.in_group(RDRF_GROUPS.WORKING_GROUP_CURATOR)

    @property
    def dashboards(self):
        return RegistryDashboard.objects.filter_user_parent_dashboards(self)

    @property
    def default_page(self):
        from django.urls import reverse

        if self.is_parent:
            if self.dashboards:
                return reverse('parent_dashboard_list')
            elif self.registry_code:
                return reverse("registry:parent_page", args=[self.registry_code])
            else:
                return reverse("landing")

        if self.is_patient or self.is_carrier:
            patient = self.user_object.first()
            registry = self.registry.first()
            if patient and registry:
                if consent_check(registry, self, patient, "see_patient"):
                    return reverse("registry:patient_page", args=[registry.code])
                else:
                    return reverse("consent_form_view", args=[registry.code, patient.id])
            else:
                return reverse("landing")

        return reverse('patientslisting')

    def get_groups(self):
        return self.groups.all()

    def get_working_groups(self):
        return self.working_groups.all()

    def get_registries(self):
        return self.registry.all()

    def get_registries_or_all(self):
        if not self.is_superuser:
            return self.get_registries()
        else:
            return Registry.objects.all().order_by("name")

    def can_view_patient_link(self, patient_model):
        # can this user view a link to this patient?
        if self.is_superuser:
            return True
        my_wgs = set([wg.id for wg in self.working_groups.all()])
        patient_wgs = set([wg.id for wg in patient_model.working_groups.all()])
        return my_wgs.intersection(patient_wgs)

    def has_feature(self, feature):
        if not self.is_superuser:
            return any([r.has_feature(feature) for r in self.registry.all()])
        else:
            return any([r.has_feature(feature) for r in Registry.objects.all()])

    def add_group(self, group_name):
        from django.contrib.auth.models import Group
        existing_groups = [g.name for g in self.groups.all()]
        if group_name not in existing_groups:
            group, __ = Group.objects.get_or_create(name=group_name)
            self.groups.add(group)

    def can_view(self, registry_form_model):
        if self.is_superuser:
            return True

        form_registry = registry_form_model.registry
        my_registries = [r for r in self.registry.all()]

        if form_registry not in my_registries:
            return False

        if registry_form_model.open:
            return True

        form_allowed_groups = [g for g in registry_form_model.groups_allowed.all()]

        for group in self.groups.all():
            if group in form_allowed_groups:
                return True

        return False

    def is_readonly(self, registry_form_model):
        return any(group in registry_form_model.groups_readonly.all() for group in self.groups.all())

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.force_password_change = False

    def _load_quick_links(self):
        valid_setting = hasattr(settings, 'QUICKLINKS_CLASS')
        if not valid_setting:
            logger.error("QUICKLINKS_CLASS setting is not configured !")
            return None
        setting_value = settings.QUICKLINKS_CLASS
        if not setting_value:
            logger.error("QUICKLINKS_CLASS setting need to have a value !")
            return None
        return import_string(setting_value)

    @property
    def menu_links(self):
        quick_links_class = self._load_quick_links()
        if not quick_links_class:
            return []
        qlinks = quick_links_class(self.get_registries_or_all())
        if self.is_superuser:
            links = qlinks.menu_links([RDRF_GROUPS.SUPER_USER])
        else:
            links = qlinks.menu_links([group.name for group in self.groups.all()])

        return links

    @property
    def settings_links(self):
        links = []
        if self.is_superuser:
            quick_links_class = self._load_quick_links()
            if not quick_links_class:
                return links
            qlinks = quick_links_class(self.get_registries_or_all())
            links = qlinks.settings_links()
        return links

    @property
    def admin_page_links(self):
        links = []
        if self.is_superuser:
            quick_links_class = self._load_quick_links()
            if not quick_links_class:
                return links
            qlinks = quick_links_class(self.get_registries_or_all())
            links = qlinks.admin_page_links()

        return links


@receiver(user_activated)
def user_activated_callback(sender, user, request, **kwargs):
    from rdrf.services.io.notifications.email_notification import process_notification
    from rdrf.events.events import EventType
    from registry.patients.models import Patient
    from registry.patients.models import ParentGuardian

    parent = patient = None
    email_notification_description = EventType.ACCOUNT_VERIFIED
    template_data = {}

    if user.is_patient:
        patient = Patient.objects.get(user=user)

    elif user.is_parent:
        # is the user is a parent they will have created 1 patient (only?)
        parent = ParentGuardian.objects.get(user=user)
        patients = [p for p in parent.patient.all()]
        if len(patients) >= 1:
            patient = patients[0]

    if patient:
        template_data["patient"] = patient

    if parent:
        template_data["parent"] = parent

    template_data["user"] = user

    for registry_model in user.registry.all():
        registry_code = registry_model.code
        process_notification(registry_code,
                             email_notification_description,
                             template_data)
