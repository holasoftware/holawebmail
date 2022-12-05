import urllib

from django.urls import reverse as reverse_url, path as urlpattern_path, get_resolver
from django.urls.resolvers import URLResolver
from django.utils.functional import lazy as lazy_func
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect


_mailbox_view_names = set()

def add_query_string(url, query_params):
    query_string = urllib.parse.urlencode(query_params)
    url += "?" + query_string
    return url


def mailbox_url(path, view, name=None):
    _mailbox_view_names.add(name)
    return urlpattern_path('mail/mbox/<int:mbox>/' + path, view, name=name)


def reverse_url_ex(view_name, kwargs=None, query_params=None, lazy=False):
    if lazy:
        #url = lazystr(lambda: reverse_url_ex(view_name, kwargs=kwargs, query_params=query_params))
        url = lazy_func(reverse_url_ex, str)(view_name, kwargs=kwargs, query_params=query_params)
    else:
        url = reverse_url(view_name, kwargs=kwargs)

        if query_params:
            url = add_query_string(url, query_params)

    return url


def reverse_webmail_url(view_name, mbox=None, kwargs=None, query_params=None, mailbox=None, lazy=False):
    if mbox is None and mailbox is not None:
        mbox = mailbox.id

    if view_name in _mailbox_view_names:
        if mbox is None:
            raise Exception("View name '%s' requires mbox parameter." % view_name)

        if kwargs is None:
            kwargs = {}

        kwargs["mbox"] = mbox
        if query_params is not None and "mbox" in query_params:
            query_params = dict(query_params)
            del query_params["mbox"]
    else:
        if mbox is not None:
            if query_params is None:
                query_params = {}

            query_params["mbox"] = str(mbox)

    url = reverse_url_ex("webmail:"+view_name, kwargs=kwargs, query_params=query_params, lazy=lazy)
    return url


def get_folder_url(mailbox, folder_name):
    url = reverse_url("webmail:show_folder", kwargs={"folder_name": folder_name, "mbox": mailbox.id})
    return url


_url_path_regex_dict = None

def get_url_patterns_string_formats():
    global _url_path_regex_dict
    if _url_path_regex_dict is None:

        url_resolver = get_resolver()
        webmail_url_resolver = None

        for url_pattern in url_resolver.url_patterns:
            # url_pattern.urlconf_name.__name__
            if isinstance(url_pattern, URLResolver) and url_pattern.app_name  == 'webmail':
                webmail_url_resolver = url_pattern
                break

        if webmail_url_resolver is None:
            raise Exception("'webmail_url_resolver' not found!")

        _url_path_regex_dict = {}
        for viewname in webmail_url_resolver.reverse_dict:
            if not isinstance(viewname, str):
                continue

            _url_path_regex_dict[viewname] = webmail_url_resolver.reverse_dict[viewname][0][0][0]

    return _url_path_regex_dict


def redirect(to, *args, permanent=False, **kwargs):
    redirect_class = HttpResponsePermanentRedirect if permanent else HttpResponseRedirect
    return redirect_class(reverse_webmail_url(to, *args, **kwargs))

