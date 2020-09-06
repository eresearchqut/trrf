from rest_framework.pagination import CursorPagination


class PatientListPagination(CursorPagination):
    page_size = 10
    ordering = "last_updated_overall_at"
