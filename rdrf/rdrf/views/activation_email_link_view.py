from django.shortcuts import render
from django.views.generic.base import View
from django.urls import reverse

from rdrf.helpers.utils import make_full_url

import logging

logger = logging.getLogger(__name__)


class ActivationEmailLinkView(View):

    def get(self, request, activation_key):
        activation_url = reverse(
            "registration_activate",
            kwargs={"activation_key": activation_key})

        return render(request, "registration/activation_email_link.html", {'activation_url': make_full_url(activation_url)})
