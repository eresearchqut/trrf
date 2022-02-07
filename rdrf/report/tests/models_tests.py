from django.contrib.auth.models import Group
from django.test import TestCase

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from registry.groups import GROUPS as RDRF_GROUPS
from registry.groups.models import CustomUser
from report.models import ReportDesign


class ReportDesignTestCase(TestCase):

    def get_reports_for_user(self, user):
        return list(ReportDesign.objects.reports_for_user(user).all())

    def test_reports_for_user(self):
        group_curator = Group.objects.create(name=RDRF_GROUPS.WORKING_GROUP_CURATOR)
        group_clinician = Group.objects.create(name=RDRF_GROUPS.CLINICAL)

        registry_1 = Registry.objects.create(code='TEST1')
        registry_1.add_feature(RegistryFeatures.CLINICIAN_ETHICAL_CLEARANCE)
        registry_1.save()
        report_1 = ReportDesign.objects.create(title='Report 1', registry=registry_1)
        report_1.access_groups.add(group_clinician)
        report_2 = ReportDesign.objects.create(title='Report 2', registry=registry_1)
        report_2.access_groups.add(group_clinician)
        report_3 = ReportDesign.objects.create(title='Report 3', registry=registry_1)
        report_3.access_groups.add(group_curator)

        registry_2 = Registry.objects.create(code='TEST2')
        report_4 = ReportDesign.objects.create(title='Report 4', registry=registry_2)

        user_no_permissions = CustomUser.objects.create(username='standarduser')
        user_is_superuser = CustomUser.objects.create(username='superuser', is_superuser=True)
        user_curator = CustomUser.objects.create(username='registry1-curator')
        user_curator.registry.add(registry_1)
        user_curator.groups.add(group_curator)
        user_clinician_1 = CustomUser.objects.create(username='clinician1', ethically_cleared=False)
        user_clinician_1.registry.add(registry_1)
        user_clinician_1.groups.add(group_clinician)
        user_clinician_2 = CustomUser.objects.create(username='clinician2', ethically_cleared=True)
        user_clinician_2.registry.add(registry_1)
        user_clinician_2.groups.add(group_clinician)

        # Assertions ->
        # user with no remarkable attributes does not have access to any reports
        self.assertEqual([], self.get_reports_for_user(user_no_permissions))

        # super user has access to all reports
        self.assertEqual([report_1, report_2, report_3, report_4], self.get_reports_for_user(user_is_superuser))

        # curator can access reports in their registry that they have been given access to
        self.assertEqual([report_3], self.get_reports_for_user(user_curator))

        # clinician can only access clinician reports in their registry if they have ethical clearance
        self.assertEqual([], self.get_reports_for_user(user_clinician_1))
        self.assertEqual([report_1, report_2], self.get_reports_for_user(user_clinician_2))
