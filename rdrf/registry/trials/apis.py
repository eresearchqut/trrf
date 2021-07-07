import requests
from django.conf import settings


class TrialRandomisationAPI:
    base_url = settings.TRIAL_RANDOMISATION_API

    def post_n_of_1(self, patients, cycles, treatments):
        return requests.post(self.base_url, json={
            "patients": patients,
            "cycles": cycles,
            "treatments": treatments
        })
