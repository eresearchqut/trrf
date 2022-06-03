import logging

from graphene_django.views import GraphQLView
from graphql import GraphQLError
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class PublicGraphQLError(GraphQLError):
    pass


class TrrfGraphQLView(GraphQLView):

    @staticmethod
    def format_error(error):
        super_class = super(TrrfGraphQLView, TrrfGraphQLView)

        if hasattr(error, 'original_error') and isinstance(error.original_error, PublicGraphQLError):
            return super_class.format_error(error)
        else:
            # Generify the error
            logger.error(error)
            return super_class.format_error(GraphQLError(message=_('An unexpected error has occurred.'), path=error.path))
