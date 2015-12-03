from nose import SkipTest
try:
    import django
except ImportError:
    raise SkipTest()


# Setup a Django environment, before we do anything else.
#
# Most Django imports fail one way or another without an
# environment.
#
# We can't even use setup_package() here, because then
# module-global imports in our test submodules still run
# first.

from django.conf import settings
settings.configure(INSTALLED_APPS=['django_assets', 'django.contrib.staticfiles'])

if django.VERSION >= (1, 7):
    from django.apps import apps
    apps.populate(settings.INSTALLED_APPS)
