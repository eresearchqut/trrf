import logging

from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.utils.translation import ugettext_lazy as _

from rdrf.models.definition.models import Registry
from rdrf.security.mixins import SuperuserRequiredMixin
from registry.groups.models import CustomUser


logger = logging.getLogger(__name__)


class MatrixRow(object):

    def __init__(self, permission, groups):
        self.permission = permission
        self.groups = groups   # auth groups

    @property
    def name(self):
        return _(self.permission.name)

    @property
    def columns(self):
        cols = []

        for group in self.groups:
            if self.has_permission(group):
                cols.append(True)
            else:
                cols.append(False)

        return cols

    def has_permission(self, group):
        return self.permission in [p for p in group.permissions.all()]


class PermissionMatrix(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.groups = self._get_groups()
        self.permissions = self._get_permissions()

    def _get_groups(self):
        return Group.objects.all().order_by("name")

    def _get_permissions(self):
        return [p for p in Permission.objects.all().order_by("name")]

    def _get_users(self):
        return [u for u in CustomUser.objects.all().order_by("username")]

    @property
    def headers(self):
        return ["Permission"] + [_(group.name) for group in self.groups]

    @property
    def rows(self):
        row_objects = []
        for permission in self.permissions:
            row_objects.append(MatrixRow(permission, self.groups))
        return row_objects


class MatrixWrapper(object):

    def __init__(self, registry_model):
        self.matrix = PermissionMatrix(registry_model)
        self.name = _("Permission Matrix for %(registry)s") % {"registry": registry_model.name}


class PermissionMatrixView(SuperuserRequiredMixin, TemplateView):
    template_name = "rdrf_cdes/permission_matrix.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        registry_model = get_object_or_404(Registry, code=kwargs.get('registry_code'))
        context.update({
            "location": "Permissions",
            "matrix_wrapper": MatrixWrapper(registry_model),
        })
        return context
