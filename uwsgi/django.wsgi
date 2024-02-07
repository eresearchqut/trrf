# Generic WSGI application
import os
import uwsgi
from io import BytesIO
from django.core.wsgi import get_wsgi_application
from urllib.parse import parse_qs
from werkzeug.wsgi import get_input_stream, LimitedStream

AUTH_USER = ''
def application(environ, start):
    global AUTH_USER
    def get_auth_user(environ):
        input_stream = get_input_stream(environ)
        content_bytes = bytearray()
        if isinstance(input_stream, LimitedStream):
            for chunk in input_stream:
                content_bytes.extend(chunk)
                if len(content_bytes) >= input_stream.limit:
                    break
        parsed_data = parse_qs(content_bytes.decode())
        environ['wsgi.input'] = BytesIO(content_bytes)

        return parsed_data.get('auth-username', [''])[0]

    user = get_auth_user(environ)
    uri = environ.get('REQUEST_URI', '')
    if 'login?' in uri and user != AUTH_USER:
        AUTH_USER = user
    elif 'logout?' in uri:
        AUTH_USER = ''

    uwsgi.set_logvar('auth_user', AUTH_USER)

    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    return get_wsgi_application()(environ,start)
