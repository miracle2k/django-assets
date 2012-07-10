import imp
from django.conf import settings
from webassets.env import (
    BaseEnvironment, ConfigStorage, Resolver, url_prefix_join)
from webassets.exceptions import ImminentDeprecationWarning
try:
    from django.contrib.staticfiles import finders
except ImportError:
    # Support pre-1.3 versions.
    finders = None

from glob import Globber, has_magic


__all__ = ('register',)



class DjangoConfigStorage(ConfigStorage):

    _mapping = {
        'debug': 'ASSETS_DEBUG',
        'cache': 'ASSETS_CACHE',
        'updater': 'ASSETS_UPDATER',
        'auto_build': 'ASSETS_AUTO_BUILD',
        'url_expire': 'ASSETS_URL_EXPIRE',
        'versions': 'ASSETS_VERSIONS',
        'manifest': 'ASSETS_MANIFEST',
        # Deprecated
        'expire': 'ASSETS_EXPIRE',
    }

    def _transform_key(self, key):
        # STATIC_* are the new Django 1.3 settings,
        # MEDIA_* was used in earlier versions.

        if key.lower() == 'directory':
            if hasattr(settings, 'ASSETS_ROOT'):
                return 'ASSETS_ROOT'
            if getattr(settings, 'STATIC_ROOT', None):
                # Is None by default
                return 'STATIC_ROOT'
            return 'MEDIA_ROOT'

        if key.lower() == 'url':
            if hasattr(settings, 'ASSETS_URL'):
                return 'ASSETS_URL'
            if getattr(settings, 'STATIC_URL', None):
                # Is '' by default
                return 'STATIC_URL'
            return 'MEDIA_URL'

        return self._mapping.get(key.lower(), key.upper())

    def __contains__(self, key):
        return hasattr(settings, self._transform_key(key))

    def __getitem__(self, key):
        if self.__contains__(key):
            value = self._get_deprecated(key)
            if value is not None:
                return value
            return getattr(settings, self._transform_key(key))
        else:
            raise KeyError("Django settings doesn't define %s" % key)

    def __setitem__(self, key, value):
        if not self._set_deprecated(key, value):
            setattr(settings, self._transform_key(key), value)

    def __delitem__(self, key):
        # This isn't possible to implement in Django without relying
        # on internals of the settings object, so just set to None.
        self.__setitem__(key, None)


class StorageGlobber(Globber):
    """Globber that works with a Django storage."""

    def __init__(self, storage):
        self.storage = storage

    def isdir(self, path):
        # No API for this, though we could a) check if this is a filesystem
        # storage, then do a shortcut, otherwise b) use listdir() and see
        # if we are in the directory set.
        # However, this is only used for the "sdf/" syntax, so by returning
        # False we disable this syntax and cause it no match nothing.
        return False

    def islink(self, path):
        # No API for this, just act like we don't know about links.
        return False

    def listdir(self, path):
        directories, files = self.storage.listdir(path)
        return directories + files

    def exists(self, path):
        try:
            return self.storage.exists(path)
        except NotImplementedError:
            return False


class DjangoResolver(Resolver):
    """Adds support for staticfiles resolving."""

    @property
    def use_staticfiles(self):
        return settings.DEBUG and \
            'django.contrib.staticfiles' in settings.INSTALLED_APPS

    def glob_staticfiles(self, item):
        # The staticfiles finder system can't do globs, but we can
        # access the storages behind the finders, and glob those.

        for finder in finders.get_finders():
            # Builtin finders use either one of those attributes,
            # though this does seem to be informal; custom finders
            # may well use neither. Nothing we can do about that.
            if hasattr(finder, 'storages'):
                storages = finder.storages.values()
            elif hasattr(finder, 'storage'):
                storages = [finder.storage]
            else:
                continue

            for storage in storages:
                globber = StorageGlobber(storage)
                for file in globber.glob(item):
                    yield storage.path(file)

    def search_for_source(self, item):
        if not self.use_staticfiles:
            return Resolver.search_for_source(self, item)

        # Use the staticfiles finders to determine the absolute path
        if finders:
            if has_magic(item):
                return list(self.glob_staticfiles(item))
            else:
                f = finders.find(item)
                if f is not None:
                    return f

        raise IOError(
            "'%s' not found (using staticfiles finders)" % item)

    def resolve_source_to_url(self, filepath, item):
        if not self.use_staticfiles:
            return Resolver.resolve_source_to_url(self, filepath, item)

        # With staticfiles enabled, searching the url mappings, as the
        # parent implementation does, will not help. Instead, we can
        # assume that the url is the root url + the original relative
        # item that was specified (and searched for using the finders).
        return url_prefix_join(self.env.url, item)


class DjangoEnvironment(BaseEnvironment):
    """For Django, we need to redirect all the configuration values this
    object holds to Django's own settings object.
    """

    config_storage_class = DjangoConfigStorage
    resolver_class = DjangoResolver

    def __init__(self, **config):
        super(DjangoEnvironment, self).__init__(**config)

        # This is pretty stupid, but fortunately will be removed with
        # the deprecated option. This triggers the deprecation warnings.
        if 'expire' in self.config:
            self.config['expire'] = getattr(settings, 'ASSETS_EXPIRE')
        if 'updater' in self.config:
            self.config['updater'] = getattr(settings, 'ASSETS_UPDATER')


# Django has a global state, a global configuration, and so we need a
# global instance of a asset environment.
env = None

def get_env():
    global env
    if env is None:
        env = DjangoEnvironment()

        # Load application's ``assets``  modules. We need to do this in
        # a delayed fashion, since the main django_assets module imports
        # this, and the application ``assets`` modules we load will import
        # ``django_assets``, thus giving us a classic circular dependency
        # issue.
        autoload()
    return env

def reset():
    global env
    env = None

# The user needn't know about the env though, we can expose the
# relevant functionality directly. This is also for backwards-compatibility
# with times where ``django-assets`` was a standalone library.
def register(*a, **kw):
    return get_env().register(*a, **kw)


# Finally, we'd like to autoload the ``assets`` module of each Django.
try:
    from django.utils.importlib import import_module
except ImportError:
    # django-1.0 compatibility
    import warnings
    warnings.warn('django-assets may not be compatible with Django versions '
                  'earlier than 1.1', ImminentDeprecationWarning)
    def import_module(app):
        return __import__(app, {}, {}, [app.split('.')[-1]]).__path__


_ASSETS_LOADED = False

def autoload():
    """Find assets by looking for an ``assets`` module within each
    installed application, similar to how, e.g., the admin autodiscover
    process works. This is were this code has been adapted from, too.

    Only runs once.

    TOOD: Not thread-safe!
    TODO: Bring back to status output via callbacks?
    """
    global _ASSETS_LOADED
    if _ASSETS_LOADED:
        return False

    # Import this locally, so that we don't have a global Django
    # dependency.
    from django.conf import settings

    for app in settings.INSTALLED_APPS:
        # For each app, we need to look for an assets.py inside that
        # app's package. We can't use os.path here -- recall that
        # modules may be imported different ways (think zip files) --
        # so we need to get the app's __path__ and look for
        # admin.py on that path.
        #if options.get('verbosity') > 1:
        #    print "\t%s..." % app,

        # Step 1: find out the app's __path__ Import errors here will
        # (and should) bubble up, but a missing __path__ (which is
        # legal, but weird) fails silently -- apps that do weird things
        # with __path__ might need to roll their own registration.
        try:
            app_path = import_module(app).__path__
        except AttributeError:
            #if options.get('verbosity') > 1:
            #    print "cannot inspect app"
            continue

        # Step 2: use imp.find_module to find the app's assets.py.
        # For some reason imp.find_module raises ImportError if the
        # app can't be found but doesn't actually try to import the
        # module. So skip this app if its assetse.py doesn't exist
        try:
            imp.find_module('assets', app_path)
        except ImportError:
            #if options.get('verbosity') > 1:
            #    print "no assets module"
            continue

        # Step 3: import the app's assets file. If this has errors we
        # want them to bubble up.
        import_module("%s.assets" % app)
        #if options.get('verbosity') > 1:
        #    print "assets module loaded"

    # Load additional modules.
    for module in getattr(settings, 'ASSETS_MODULES', []):
        import_module("%s" % module)

    _ASSETS_LOADED = True
