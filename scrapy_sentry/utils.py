import os
import time
from logging.config import dictConfig
from importlib import import_module

from twisted.python import log

try:
    from scrapy.utils.project import get_project_settings
except ImportError:
    from scrapy.conf import settings
else:
    settings = get_project_settings()

from scrapy.http import Request, Headers  # noqa
from scrapy.utils.reqser import request_to_dict, request_from_dict  # noqa
from scrapy.responsetypes import responsetypes

from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

SENTRY_DSN = os.environ.get("SENTRY_DSN", None)


def import_member(path):
    """
    Loads a value from a module specified by an absolute path.

    E.g.:

    >>> import_object('raven.Client')
    <class 'raven.base.Client'>
    """
    try:
        module_path, member_name = path.rsplit('.', 1)
    except ValueError:
        raise ValueError("Import path {} doesn\'t include a dot.".format(path))

    module = import_module(module_path)

    try:
        member = getattr(module, member_name)
    except AttributeError:
        raise NameError("Module {} doesn't define {}".format(module_path, member_name))

    return member


def get_client(dsn=None):
    """gets a scrapy client"""
    sentry_client_path = settings.get('SENTRY_CLIENT', 'raven.Client')
    Client = import_member(sentry_client_path)
    return Client(dsn or settings.get("SENTRY_DSN", SENTRY_DSN))


def init(dsn=None):
    """Redirect Scrapy log messages to standard Python logger"""

    observer = log.PythonLoggingObserver()
    observer.start()

    dict_config = settings.get("LOGGING")
    if dict_config is not None:
        assert isinstance(dict_config, dict)
        dictConfig(dict_config)

    sentry_loglevel = settings.get("SENTRY_LOGLEVEL")

    if sentry_loglevel:
        handler_kwargs = {'level': sentry_loglevel}
    else:
        handler_kwargs = {}

    handler = SentryHandler(get_client(dsn), **handler_kwargs)
    setup_logging(handler)


def response_to_dict(response, spider, include_request=True, **kwargs):
    """Returns a dict based on a response from a spider"""
    d = {
        'time': time.time(),
        'status': response.status,
        'url': response.url,
        'headers': dict(response.headers),
        'body': response.body,
      }
    if include_request:
        d['request'] = request_to_dict(response.request, spider)
    return d


def response_from_dict(response, spider=None, **kwargs):
    """Returns a dict based on a response from a spider"""
    url = response.get("url")
    status = response.get("status")
    headers = Headers([(x, list(map(str, y))) for x, y in
                       response.get("headers").items()])
    body = response.get("body")

    respcls = responsetypes.from_args(headers=headers, url=url)
    response = respcls(url=url, headers=headers, status=status, body=body)
    return response
