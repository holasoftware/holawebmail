from django.views.generic import View


from .ajax_decorator import ajax


class AJAXViewMixin:

    """
    AJAX Mixin Class
    """
    ajax_mandatory = True
    ajax_login_required = True

    def dispatch(self, request, *args, **kwargs):
        """
        Using ajax decorator
        """
        ajax_kwargs = {'mandatory': self.ajax_mandatory, 'login_required': self.ajax_login_required}

        return ajax(**ajax_kwargs)(super().dispatch)(request, *args, **kwargs)


class AJAXView(AJAXViewMixin, View):
    pass
