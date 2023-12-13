import logging

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField, UserChangeForm as OldUserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ChoiceField
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from rdrf.helpers.utils import get_all_language_codes
from registry.groups import GROUPS as RDRF_GROUPS
from registry.groups.forms import working_group_optgroup_choices
from registry.groups.models import WorkingGroup

logger = logging.getLogger(__name__)


class UserMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.restrict_registries_and_working_groups(self.user)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if self.instance is not None and username == self.instance.username:
            return username
        if get_user_model().objects.filter(username__iexact=username.lower()).exists():
            raise forms.ValidationError("There is already a user with that username!")
        return username

    def clean(self):
        # When the registry and/or working groups are selected, validate the selection is consistent.
        # We will prevent having a user who:
        # a) has been assigned a registry but not assigned to a working group of that registry
        # b) has been assigned to a working group but not assigned to the owning registry
        #    of that working group.
        registry_models = self.cleaned_data.get("registry", [])
        working_group_models = self.cleaned_data.get("working_groups", [])

        if len(registry_models) == 0 and len(working_group_models) == 0:
            # Registries and working groups not selected. Don't check for consistency.
            return self.cleaned_data

        if len(registry_models) == 0:
            raise ValidationError("Choosing a registry is mandatory if you selected a working group")

        if len(working_group_models) == 0:
            raise ValidationError("Choosing a working group is mandatory if you selected a registry")

        for working_group_model in working_group_models:
            if working_group_model.registry not in registry_models:
                msg = "Working Group '%s' not in any of the assigned registries" % working_group_model.display_name
                raise ValidationError(msg)

        for registry_model in registry_models:
            if registry_model not in [
                    working_group_model.registry for working_group_model in working_group_models]:
                msg = "You have added the user into registry %s but not assigned the user " \
                      "to working group of that registry" % registry_model
                raise ValidationError(msg)

        return self.cleaned_data

    def restrict_registries_and_working_groups(self, user):
        # Enforce that non-admin users can create users only in their own registries and working groups
        wg_queryset = WorkingGroup.objects.none()
        if user:
            if user.is_superuser:
                wg_queryset = WorkingGroup.objects.all()
            else:
                if self.instance.id:
                    instance_wgs = self.instance.working_groups.all()
                    user_wgs = user.working_groups.all()
                    wg_queryset = WorkingGroup.objects.filter(Q(id__in=instance_wgs) | Q(id__in=user_wgs))
                else:
                    wg_queryset = user.working_groups.all()

                self.fields['registry'].queryset = user.registry.all()
                self.fields['registry'].required = True
                self.fields['working_groups'].required = True

        self.fields['working_groups'].choices = working_group_optgroup_choices(wg_queryset)


class RDRFUserCreationForm(UserMixin, forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ('username',)

    def clean_password2(self):
        password2 = self.cleaned_data.get("password2")

        validate_password(password2)
        return password2

    def save(self, commit=True):
        user = super(RDRFUserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(UserMixin, forms.ModelForm):
    model = get_user_model()

    password = ReadOnlyPasswordHashField(
        help_text=(OldUserChangeForm.base_fields['password'].help_text.format('../password/')))

    preferred_language = ChoiceField(choices=get_all_language_codes())

    class Meta:
        fields = "__all__"
        model = get_user_model()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            contains_clinician = any(RDRF_GROUPS.CLINICAL == g.name.lower() for g in self.instance.groups.all())
            if 'ethically_cleared' in self.fields and not contains_clinician:
                self.fields['ethically_cleared'].widget = forms.HiddenInput()

        change_email_url = reverse("user_email_change", kwargs={"user_id": self.instance.id})
        sync_email_help_text = f'{_("Synchronised email address changes can be made using")}: ' \
                               f'<a href="{change_email_url}">{_("Change email address form")}</a>.'
        self.fields['username'].help_text += mark_safe(f'<br/>{sync_email_help_text}')
        self.fields['email'].help_text = mark_safe(f'{sync_email_help_text}')

    def clean_password(self):
        return self.initial["password"]

    def clean_is_superuser(self):
        is_superuser = self.cleaned_data['is_superuser']
        if is_superuser and not self.user.is_superuser:
            raise ValidationError("Can't make user a superuser unless you are one!")
        return is_superuser

    def clean_groups(self):
        group_names = [g.name for g in self.cleaned_data['groups']]
        errors = [self._validate_group(gr) for gr in group_names]
        if any(errors):
            raise ValidationError([err for err in errors if err])

        return self.cleaned_data['groups']

    def clean_ethically_cleared(self):
        cleared = self.cleaned_data['ethically_cleared']
        group_names = [g.name for g in self.cleaned_data.get('groups', [])]
        contains_clinician = any(RDRF_GROUPS.CLINICAL == g.lower() for g in group_names)
        if not contains_clinician and cleared:
            raise ValidationError('You can enable ethical clearance only for clincians !')
        return self.cleaned_data['ethically_cleared']

    def _validate_group(self, group_name):
        def group_error_msg(rdrf_group):
            group_member = rdrf_group.rstrip('s')
            return ValidationError(f"You can't assign this user to the {group_name} group because it isn't associated with a {group_member}")

        if RDRF_GROUPS.PARENT == group_name.lower() and not self.instance.parent_user_object.exists():
            return group_error_msg(RDRF_GROUPS.PARENT)
