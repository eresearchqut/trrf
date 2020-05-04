from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.views.generic import View


class FileErrorHandlingView(LoginRequiredMixin, View):

    def with_error_handling(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement this !")

    def get(self, request, *args, **kwargs):
        try:
            return self.with_error_handling(request, *args, **kwargs)
        except PermissionError:
            raise PermissionDenied
        except IOError:
            raise Http404("File does not exist")
