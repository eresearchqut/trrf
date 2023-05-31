from django.contrib.auth.models import Group
from django.test import TestCase

from registry.groups.models import CustomUser, WorkingGroupType, WorkingGroup, WorkingGroupTypeRule


class GroupModelTest(TestCase):

    def setUp(self):
        self.group_clinician = Group.objects.create(name='Clinical Staff')
        self.group_research = Group.objects.create(name='Research Staff')

        self.user_superuser = CustomUser.objects.create(username='superuser', is_superuser=True, is_active=True)
        self.user_clinician = CustomUser.objects.create(username='clinician', is_active=True)
        self.user_researcher = CustomUser.objects.create(username='researcher', is_active=True)

        self.user_clinician.groups.set([self.group_clinician])
        self.user_researcher.groups.set([self.group_research])

        self.type_facility = WorkingGroupType.objects.create(name='Facility')
        self.type_condition = WorkingGroupType.objects.create(name='Condition')
        self.type_unit = WorkingGroupType.objects.create(name='Unit')

        self.wg_mater = WorkingGroup.objects.create(name='Mater Hospital Brisbane', type=self.type_facility)
        self.wg_royal = WorkingGroup.objects.create(name='Royal Brisbane Hospital', type=self.type_facility)
        self.wg_greenslopes = WorkingGroup.objects.create(name='Greenslopes Hospital', type=self.type_facility)

        self.wg_arrythmia = WorkingGroup.objects.create(name='Arrhythmia', type=self.type_condition)
        self.wg_coronary = WorkingGroup.objects.create(name='Coronary artery disease', type=self.type_condition)
        self.wg_stroke = WorkingGroup.objects.create(name='Stroke', type=self.type_condition)

        self.wg_cardiology = WorkingGroup.objects.create(name='Cardiology', type=self.type_unit)
        self.wg_neurology = WorkingGroup.objects.create(name='Neurology', type=self.type_unit)
        self.wg_outpatients = WorkingGroup.objects.create(name='Outpatients', type=self.type_unit)

        self.wg_unassigned = WorkingGroup.objects.create(name='Unassigned')
        self.wg_teaching = WorkingGroup.objects.create(name='Teaching')

    def _list_working_groups(self, user):
        return list(WorkingGroup.objects.get_by_user(user))

    def test_get_by_user_for_super_user(self):
        self.assertEqual(self._list_working_groups(self.user_superuser),
                         [self.wg_arrythmia,
                          self.wg_coronary,
                          self.wg_stroke,
                          self.wg_greenslopes,
                          self.wg_mater,
                          self.wg_royal,
                          self.wg_cardiology,
                          self.wg_neurology,
                          self.wg_outpatients,
                          self.wg_teaching,
                          self.wg_unassigned])

    def test_get_by_user(self):
        # clinician, nor researcher has not been assigned to any working groups yet
        self.assertEqual(self._list_working_groups(self.user_clinician), [])
        self.assertEqual(self._list_working_groups(self.user_researcher), [])

        # assign working groups directly to users
        self.user_clinician.working_groups.set([self.wg_royal, self.wg_teaching])
        self.user_researcher.working_groups.set([self.wg_arrythmia, self.wg_stroke])
        self.assertEqual(self._list_working_groups(self.user_clinician), [self.wg_royal, self.wg_teaching])
        self.assertEqual(self._list_working_groups(self.user_researcher), [self.wg_arrythmia, self.wg_stroke])

        # create a rule for clinicians and working group type conditions, but don't enable default access
        rule_condition_clinician = WorkingGroupTypeRule.objects.create(type=self.type_condition, user_group=self.group_clinician)
        self.assertEqual(self._list_working_groups(self.user_clinician), [self.wg_royal, self.wg_teaching])
        self.assertEqual(self._list_working_groups(self.user_researcher), [self.wg_arrythmia, self.wg_stroke])

        # Turn on default access for clinician's access to unit working groups
        rule_condition_clinician.has_default_access = True
        rule_condition_clinician.save()
        self.assertEqual(self._list_working_groups(self.user_clinician), [self.wg_arrythmia,
                                                                          self.wg_coronary,
                                                                          self.wg_stroke,
                                                                          self.wg_royal,
                                                                          self.wg_teaching])
        self.assertEqual(self._list_working_groups(self.user_researcher), [self.wg_arrythmia, self.wg_stroke])

        # Turn on default access for researcher's access to facility working groups
        WorkingGroupTypeRule.objects.create(type=self.type_facility, user_group=self.group_research, has_default_access=True)
        self.assertEqual(self._list_working_groups(self.user_clinician), [self.wg_arrythmia,
                                                                          self.wg_coronary,
                                                                          self.wg_stroke,
                                                                          self.wg_royal,
                                                                          self.wg_teaching])
        self.assertEqual(self._list_working_groups(self.user_researcher), [self.wg_arrythmia,
                                                                           self.wg_stroke,
                                                                           self.wg_greenslopes,
                                                                           self.wg_mater,
                                                                           self.wg_royal])

        # Turn on a second default access rule for researcher's to access all units
        WorkingGroupTypeRule.objects.create(type=self.type_unit, user_group=self.group_research, has_default_access=True)
        self.assertEqual(self._list_working_groups(self.user_clinician), [self.wg_arrythmia,
                                                                          self.wg_coronary,
                                                                          self.wg_stroke,
                                                                          self.wg_royal,
                                                                          self.wg_teaching])
        self.assertEqual(self._list_working_groups(self.user_researcher), [self.wg_arrythmia,
                                                                           self.wg_stroke,
                                                                           self.wg_greenslopes,
                                                                           self.wg_mater,
                                                                           self.wg_royal,
                                                                           self.wg_cardiology,
                                                                           self.wg_neurology,
                                                                           self.wg_outpatients])
