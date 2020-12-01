import logging
import string

from .apis import TrialRandomisationAPI
from .models import NofOneTreatment, NofOneArm, NofOneCycle, NofOnePeriod

logger = logging.getLogger(__name__)


def _generate_n_of_1_arms(patients, cycles, treatments):
    api = TrialRandomisationAPI()
    response = api.post_n_of_1(patients, cycles, treatments).json()
    if not response.get("schedule"):
        raise KeyError("Response from server doesn't contain a schedule")
    return response["schedule"]


def setup_trial(patients, cycles, treatments, period_length, period_washout_duration, trial):
    arms = _generate_n_of_1_arms(
        patients,
        cycles,
        treatments
    )

    treatment_models = NofOneTreatment.objects.bulk_create(NofOneTreatment(
        title=f"Treatment {i}",
        blinded_title=string.ascii_uppercase[i],
        trial=trial
    ) for i in range(treatments))

    treatment_map = {string.ascii_uppercase[i]: treatment for i, treatment in enumerate(treatment_models)}

    arm_models = NofOneArm.objects.bulk_create(NofOneArm(
        trial=trial,
        sequence_index=i
    ) for i in range((len(arms))))

    for arm, arm_model in zip(arms, arm_models):
        cycle_models = NofOneCycle.objects.bulk_create(NofOneCycle(
            arm=arm_model,
            sequence_index=i
        ) for i in range(len(arm)))

        for cycle, cycle_model in zip(arm, cycle_models):
            NofOnePeriod.objects.bulk_create(NofOnePeriod(
                cycle=cycle_model,
                treatment=treatment_map[period],
                duration=period_length,
                washout=period_washout_duration,
                sequence_index=period_index,
            ) for period_index, period in enumerate(cycle))
