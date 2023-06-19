from django.test import TestCase

from useraudit.middleware import get_request


class RequestToThreadLocalMiddlewareTest(TestCase):

    def test_request_is_saved(self):
        self.client.get('', X_TEST='middleware test')

        request = get_request()
        self.assertTrue(request is not None)
        self.assertEqual(request.META['X_TEST'], 'middleware test')
