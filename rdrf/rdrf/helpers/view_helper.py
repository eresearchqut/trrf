from django.core.exceptions import PermissionDenied
from django.http import Http404


class FileErrorHandlingMixin:

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionError:
            raise PermissionDenied
        except IOError:
            raise Http404("File does not exist")
