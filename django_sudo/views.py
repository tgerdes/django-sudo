"""
django_sudo.views
~~~~~~~~~~~~~~~~~

:copyright: (c) 2014 by Matt Robenolt.
:license: BSD, see LICENSE for more details.
"""
try:
    from urllib.parse import urlparse, urlunparse
except ImportError:     # Python 2
    from urlparse import urlparse, urlunparse  # noqa

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, QueryDict
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from django_sudo import REDIRECT_FIELD_NAME, REDIRECT_URL
from django_sudo.forms import SudoForm
from django_sudo.utils import grant_sudo_privileges

try:
    from django.shortcuts import resolve_url
except ImportError:  # pragma: no cover
    # Django <1.5 doesn't have `resolve_url`
    from django.core import urlresolvers

    # resolve_url yanked from Django 1.5.5
    def resolve_url(to, *args, **kwargs):
        """
        Return a URL appropriate for the arguments passed.

        The arguments could be:

            * A model: the model's `get_absolute_url()` function will be called.

            * A view name, possibly with arguments: `urlresolvers.reverse()` will
              be used to reverse-resolve the name.

            * A URL, which will be returned as-is.

        """
        # If it's a model, use get_absolute_url()
        if hasattr(to, 'get_absolute_url'):
            return to.get_absolute_url()

        # Next try a reverse URL resolution.
        try:
            return urlresolvers.reverse(to, args=args, kwargs=kwargs)
        except urlresolvers.NoReverseMatch:
             # If this is a callable, re-raise.
            if callable(to):
                raise
            # If this doesn't "feel" like a URL, re-raise.
            if '/' not in to and '.' not in to:
                raise

        # Finally, fall back and assume it's a URL
        return to


@sensitive_post_parameters()
@never_cache
@csrf_protect
@login_required
def sudo(request, template_name='sudo.html', extra_context=None):
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, REDIRECT_URL)
    # Make sure we're not redirecting to other sites
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = resolve_url(REDIRECT_URL)

    if request.is_sudo():
        return HttpResponseRedirect(redirect_to)

    form = SudoForm(request.user, request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            grant_sudo_privileges(request)
            return HttpResponseRedirect(redirect_to)

    context = {
        'form': form,
        REDIRECT_FIELD_NAME: redirect_to,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context)


def redirect_to_sudo(next_url):
    """
    Redirects the user to the login page, passing the given 'next' page
    """
    sudo_url_parts = list(urlparse(reverse('django_sudo.views.sudo')))

    querystring = QueryDict(sudo_url_parts[4], mutable=True)
    querystring[REDIRECT_FIELD_NAME] = next_url
    sudo_url_parts[4] = querystring.urlencode(safe='/')

    return HttpResponseRedirect(urlunparse(sudo_url_parts))
