import logging

from registry.patients.models import PatientStage

logger = logging.getLogger(__name__)


class PatientStageChanges:
    def __init__(self, stages_data, registry):
        self.stages = stages_data
        self.registry = registry
        self.existing_stages = {}
        self.import_stages = {}
        self.stages_mapping = {}
        self.reverse_stages_mapping = {}
        self.added_stages = []
        self.renamed_stages = {}
        self.removed_stages = []
        self._compute_changes()

    def _create_compare_structures(self):
        for s in PatientStage.objects.filter(registry=self.registry):
            self.existing_stages[s.name] = {
                "next_stages": set(
                    ns.name for ns in s.allowed_next_stages.all()
                ),
                "prev_stages": set(
                    ns.name for ns in s.allowed_prev_stages.all()
                ),
            }
        for stage_dict in self.stages:
            self.stages_mapping[stage_dict["id"]] = stage_dict["name"]
            self.reverse_stages_mapping[stage_dict["name"]] = stage_dict["id"]

        for stage_dict in self.stages:
            prev_stages = stage_dict["prev_stages"]
            next_stages = stage_dict["next_stages"]
            self.import_stages[stage_dict["name"]] = {
                "next_stages": set(
                    self.stages_mapping[sid] for sid in next_stages
                ),
                "prev_stages": set(
                    self.stages_mapping[sid] for sid in prev_stages
                ),
            }

    def _compute_changes(self):
        self._create_compare_structures()
        possible_deleted_stages = (
            self.existing_stages.keys() - self.import_stages.keys()
        )
        possible_new_stages = (
            self.import_stages.keys() - self.existing_stages.keys()
        )
        logger.info(
            f"possible deleted: {possible_deleted_stages}, possible new: {possible_new_stages}"
        )
        for deleted_stage in possible_deleted_stages:
            for new_stage in possible_new_stages:
                import_new_stage = self.import_stages.get(new_stage, {})
                existing_deleted_stage = self.existing_stages.get(
                    deleted_stage, {}
                )
                same_prev_stages = import_new_stage.get(
                    "prev_stages", []
                ) == existing_deleted_stage.get("prev_stages", [])
                same_next_stages = import_new_stage.get(
                    "next_stages", []
                ) == existing_deleted_stage.get("next_stages", [])
                if same_next_stages and same_prev_stages:
                    self.renamed_stages[deleted_stage] = new_stage
        self.removed_stages = [
            p for p in possible_deleted_stages if p not in self.renamed_stages
        ]
        self.added_stages = [
            p
            for p in possible_new_stages
            if p not in self.renamed_stages.values()
        ]
        logger.info(
            f"To remove: {self.removed_stages}, renamed: {self.renamed_stages}, new: {self.added_stages}"
        )

    def get_stages_mapping(self, key):
        return self.stages_mapping[key]

    def get_reverse_mapping(self, key):
        return self.reverse_stages_mapping[key]

    def add_stage_mapping(self, key, value):
        self.stages_mapping[key] = value
        self.reverse_stages_mapping[value] = key

    def has_stage_mapping(self, key):
        return key in self.stages_mapping

    def contains_stage_mappings(self):
        return bool(self.stages_mapping)

    def get_added_stages(self):
        return self.added_stages

    def get_renamed_stages(self):
        return self.renamed_stages

    def get_removed_stages(self):
        return self.removed_stages
