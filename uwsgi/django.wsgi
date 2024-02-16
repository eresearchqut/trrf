# Generic WSGI application
import os
import uwsgi
from django.core.wsgi import get_wsgi_application

def application(environ, start):
    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    response = get_wsgi_application()(environ,start)
    user_id = str(response.user_id) if hasattr(response, 'user_id') else ''
    app = uwsgi.workers()[0]['apps'][0]['id']
    current_req = uwsgi.request_id() + 1
    total_req = uwsgi.total_requests() + 1

    uwsgi.set_logvar('user_id', user_id)
    uwsgi.set_logvar('app', str(app))
    uwsgi.set_logvar('current_req', str(current_req))
    uwsgi.set_logvar('total_req', str(total_req))

    return response
