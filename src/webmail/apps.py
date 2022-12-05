from importlib import import_module


from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


from . import settings


#TODO: investigar metodo ready
class WebmailConfig(AppConfig):
    name = 'webmail'
    verbose_name = _("Webmail")

    def ready(self):
        if settings.WEBMAIL_PLUGINS:
            for plugin_name in settings.WEBMAIL_PLUGINS:
                plugin_module_name = "%s_webmail_plugin" % plugin_name

                try:
                    plugin_conf = import_module("%s.plugin" % plugin_module_name)
                except ModuleNotFoundError:
                    pass
                else:
                    plugin_conf.init()
