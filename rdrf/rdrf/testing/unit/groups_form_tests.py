import json

from django.test import TestCase
from registry.groups.forms import working_group_optgroup_choices
from registry.groups.models import WorkingGroup, WorkingGroupType

from rdrf.models.definition.models import Registry


class GroupFormTest(TestCase):
    def setUp(self):
        self.reg_arrk = Registry.objects.create(code="arrk")
        self.reg_other = Registry.objects.create(code="other")

        self.type_hospital = WorkingGroupType.objects.create(name="Hospital")
        self.type_scg = WorkingGroupType.objects.create(
            name="Specific Condition Group"
        )

    def test_working_group_optgroup_choices_no_types(self):
        WorkingGroup.objects.create(
            id=1, name="Hospital A", registry=self.reg_arrk
        )
        WorkingGroup.objects.create(
            id=2, name="Hospital B", registry=self.reg_arrk
        )
        WorkingGroup.objects.create(
            id=3, name="Hospital C", registry=self.reg_other
        )
        WorkingGroup.objects.create(
            id=4, name="Kidney condition A", registry=self.reg_arrk
        )
        WorkingGroup.objects.create(
            id=5, name="Kidney condition B", registry=self.reg_arrk
        )
        WorkingGroup.objects.create(
            id=6, name="Sunshine Clinic", registry=self.reg_other
        )

        choices = working_group_optgroup_choices(WorkingGroup.objects.all())

        self.assertEqual(
            choices,
            [
                (
                    None,
                    [
                        (1, "arrk Hospital A"),
                        (2, "arrk Hospital B"),
                        (4, "arrk Kidney condition A"),
                        (5, "arrk Kidney condition B"),
                        (3, "other Hospital C"),
                        (6, "other Sunshine Clinic"),
                    ],
                )
            ],
        )

    def test_working_group_optgroup_choices_with_types(self):
        WorkingGroup.objects.create(
            id=1,
            name="Hospital A",
            registry=self.reg_arrk,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=2,
            name="Hospital B",
            registry=self.reg_arrk,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=3,
            name="Hospital C",
            registry=self.reg_other,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=4,
            name="Kidney condition A",
            registry=self.reg_arrk,
            type=self.type_scg,
        )
        WorkingGroup.objects.create(
            id=5,
            name="Kidney condition B",
            registry=self.reg_arrk,
            type=self.type_scg,
        )
        WorkingGroup.objects.create(
            id=6,
            name="Sunshine Clinic",
            registry=self.reg_other,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=7, name="Unallocated", registry=self.reg_arrk
        )
        WorkingGroup.objects.create(
            id=8, name="Unallocated", registry=self.reg_other
        )
        WorkingGroup.objects.create(
            id=9, name="Teaching", registry=self.reg_arrk
        )

        choices = working_group_optgroup_choices(
            WorkingGroup.objects.filter(registry=self.reg_arrk)
        )

        self.assertEqual(
            choices,
            [
                ("Hospital", [(1, "arrk Hospital A"), (2, "arrk Hospital B")]),
                (
                    "Specific Condition Group",
                    [
                        (4, "arrk Kidney condition A"),
                        (5, "arrk Kidney condition B"),
                    ],
                ),
                (None, [(9, "arrk Teaching"), (7, "arrk Unallocated")]),
            ],
        )

    def test_working_Group_optgroup_choices_with_custom_make_option_fn(self):
        WorkingGroup.objects.create(
            id=1,
            name="Hospital A",
            registry=self.reg_arrk,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=2,
            name="Hospital B",
            registry=self.reg_arrk,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=3,
            name="Hospital C",
            registry=self.reg_other,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=4,
            name="Kidney condition A",
            registry=self.reg_arrk,
            type=self.type_scg,
        )
        WorkingGroup.objects.create(
            id=5,
            name="Kidney condition B",
            registry=self.reg_arrk,
            type=self.type_scg,
        )
        WorkingGroup.objects.create(
            id=6,
            name="Sunshine Clinic",
            registry=self.reg_other,
            type=self.type_hospital,
        )
        WorkingGroup.objects.create(
            id=7, name="Unallocated", registry=self.reg_arrk
        )
        WorkingGroup.objects.create(
            id=8, name="Unallocated", registry=self.reg_other
        )
        WorkingGroup.objects.create(
            id=9, name="Teaching", registry=self.reg_arrk
        )

        def custom_make_option_fn(working_group):
            return json.dumps(
                {
                    "id": working_group.id,
                    "registry": working_group.registry.code,
                }
            ), f"{working_group.name}"

        choices = working_group_optgroup_choices(
            WorkingGroup.objects.all(), custom_make_option_fn
        )
        self.assertEqual(
            choices,
            [
                (
                    "Hospital",
                    [
                        ('{"id": 1, "registry": "arrk"}', "Hospital A"),
                        ('{"id": 2, "registry": "arrk"}', "Hospital B"),
                        ('{"id": 3, "registry": "other"}', "Hospital C"),
                        ('{"id": 6, "registry": "other"}', "Sunshine Clinic"),
                    ],
                ),
                (
                    "Specific Condition Group",
                    [
                        ('{"id": 4, "registry": "arrk"}', "Kidney condition A"),
                        ('{"id": 5, "registry": "arrk"}', "Kidney condition B"),
                    ],
                ),
                (
                    None,
                    [
                        ('{"id": 9, "registry": "arrk"}', "Teaching"),
                        ('{"id": 7, "registry": "arrk"}', "Unallocated"),
                        ('{"id": 8, "registry": "other"}', "Unallocated"),
                    ],
                ),
            ],
        )
