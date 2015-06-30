"""Manage assets.

Usage:

    ./manage.py assets build

        Build all known assets; this requires tracking to be enabled: Only
        assets that have previously been built and tracked are
        considered "known".

    ./manage.py assets build --parse-templates

        Try to find as many of the project's templates (hopefully all), and
        check them for the use of assets. Build all the assets discovered in
        this way. If tracking is enabled, the tracking database will be
        replaced by the newly found assets.

    ./manage.py assets watch

        Like ``build``, but continues to watch for changes, and builds assets
        right away. Useful for cases where building takes some time.
"""

import sys
from os import path
import logging
from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from webassets.script import (CommandError as AssetCommandError,
                              GenericArgparseImplementation)
from django_assets.env import get_env, autoload
from django_assets.loaders import get_django_template_dirs, DjangoLoader
from django_assets.manifest import DjangoManifest  # noqa: enables the --manifest django option

try:
    from django.core.management import LaxOptionParser
except ImportError:
    from optparse import OptionParser

    class LaxOptionParser(OptionParser):
        """
        An option parser that doesn't raise any errors on unknown options.
        This is needed because the --settings and --pythonpath options affect
        the commands (and thus the options) that are available to the user.
        Backported from Django 1.7.x
        """
        def error(self, msg):
            pass

        def print_help(self):
            """Output nothing.
            The lax options are included in the normal option parser, so under
            normal usage, we don't need to print the lax options.
            """
            pass

        def print_lax_help(self):
            """Output the basic options available to every command.
            This just redirects to the default print_help() behavior.
            """
            OptionParser.print_help(self)

        def _process_args(self, largs, rargs, values):
            """
            Overrides OptionParser._process_args to exclusively handle default
            options and ignore args and other options.
            This overrides the behavior of the super class, which stop parsing
            at the first unrecognized option.
            """
            while rargs:
                arg = rargs[0]
                try:
                    if arg[0:2] == "--" and len(arg) > 2:
                        # process a single long option (possibly with value(s))
                        # the superclass code pops the arg off rargs
                        self._process_long_opt(rargs, values)
                    elif arg[:1] == "-" and len(arg) > 1:
                        # process a cluster of short options (possibly with
                        # value(s) for the last one only)
                        # the superclass code pops the arg off rargs
                        self._process_short_opts(rargs, values)
                    else:
                        # it's either a non-default option or an arg
                        # either way, add it to the args list so we can keep
                        # dealing with options
                        del rargs[0]
                        raise Exception
                except:  # Needed because we might need to catch a SystemExit
                    largs.append(arg)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--parse-templates', action='store_true',
            help='Search project templates to find bundles. You need '
                 'this if you directly define your bundles in templates.'),
    )
    help = 'Manage assets.'
    args = 'subcommand'
    requires_model_validation = False

    def create_parser(self, prog_name, subcommand):
        # Overwrite parser creation with a LaxOptionParser that will
        # ignore arguments it doesn't know, allowing us to pass those
        # along to the webassets command.
        # Hooking into run_from_argv() would be another thing to try
        # if this turns out to be problematic.
        parser = BaseCommand.create_parser(self, prog_name, subcommand)
        parser.__class__ = LaxOptionParser
        return parser

    def handle(self, *args, **options):
        # Due to the use of LaxOptionParser ``args`` now contains all
        # unparsed options, and ``options`` those that the Django command
        # has declared.

        # Create log
        log = logging.getLogger('django-assets')
        log.setLevel({0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[int(options.get('verbosity', 1))])
        log.addHandler(logging.StreamHandler())

        # If the user requested it, search for bundles defined in templates
        if options.get('parse_templates'):
            log.info('Searching templates...')
            # Note that we exclude container bundles. By their very nature,
            # they are guaranteed to have been created by solely referencing
            # other bundles which are already registered.
            get_env().add(*[b for b in self.load_from_templates()
                            if not b.is_container])

        if len(get_env()) == 0:
            log.info("No asset bundles were found. "
                "If you are defining assets directly within your "
                "templates, you want to use the --parse-templates "
                "option.")
            return

        prog = "%s assets" % path.basename(sys.argv[0])
        impl = GenericArgparseImplementation(
            env=get_env(), log=log, no_global_options=True, prog=prog)
        try:
            # The webassets script runner may either return None on success (so
            # map that to zero) or a return code on build failure (so raise
            # a Django CommandError exception when that happens)
            retval = impl.run_with_argv(args) or 0
            if retval != 0:
                raise CommandError('The webassets build script exited with '
                                   'a non-zero exit code (%d).' % retval)
        except AssetCommandError as e:
            raise CommandError(e)

    def load_from_templates(self):
        # Using the Django loader
        bundles = DjangoLoader().load_bundles()

        # Using the Jinja loader, if available
        try:
            import jinja2
        except ImportError:
            pass
        else:
            from webassets.ext.jinja2 import Jinja2Loader, AssetsExtension

            jinja2_envs = []
            # Prepare a Jinja2 environment we can later use for parsing.
            # If not specified by the user, put in there at least our own
            # extension, which we will need most definitely to achieve anything.
            _jinja2_extensions = getattr(settings, 'ASSETS_JINJA2_EXTENSIONS', False)
            if not _jinja2_extensions:
                _jinja2_extensions = [AssetsExtension.identifier]
            jinja2_envs.append(jinja2.Environment(extensions=_jinja2_extensions))

            try:
                from coffin.common import get_env as get_coffin_env
            except ImportError:
                pass
            else:
                jinja2_envs.append(get_coffin_env())

            bundles.extend(Jinja2Loader(get_env(),
                                        get_django_template_dirs(),
                                        jinja2_envs).load_bundles())

        return bundles
