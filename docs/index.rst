:tocdepth: 3

django-assets
=============

.. module:: django_assets

.. toctree::
    :maxdepth: 1

    jinja2
    settings

django-assets helps you to integrate `webassets`_ into your `Django`_
application.

.. _webassets: http://github.com/miracle2k/webassets
.. _Django: https://www.djangoproject.com/


Quickstart
----------

First, add ``django_assets`` to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    INSTALLED_APPS = (
        ...,
        'django_assets',
    )


Create an ``assets.py`` file inside your *application* directory. This
is where you define your assets, and like Django's ``admin.py`` files,
they will automatically be picked up:

.. code-block:: python

    from django_assets import Bundle, register
    js = Bundle('common/jquery.js', 'site/base.js', 'site/widgets.js',
                filters='jsmin', output='gen/packed.js')
    register('js_all', js)

.. note::

    Make sure your ``assets.py`` is inside a Django *application*, not in
    the *project*. That is, the path might be something like
    ``my_project/my_application/assets.py``.

    If you want to define assets in a different place, you can use the
    :data:`~django_assets.settings.ASSETS_MODULES` setting.


Finally, include the bundle you defined in the appropriate place within your
templates:

.. code-block:: django

    {% load assets %}
    {% assets "js_all" %}
        <script type="text/javascript" src="{{ ASSET_URL }}"></script>
    {% endassets %}


``django-assets`` will now automatically merge and compress your bundle's
source files the first time the template is rendered, and will
automatically update the compressed file every time a source file changes.
If :data:`~django_assets.settings.ASSETS_DEBUG` is enabled, then each source
file will be outputted individually instead.


Templates only
~~~~~~~~~~~~~~

If you prefer, you can also do without defining your bundles in code, and
simply define everything inside your template:

.. code-block:: django

    {% load assets %}
    {% assets filters="jsmin", output="gen/packed.js", "common/jquery.js", "site/base.js", "site/widgets.js" %}
        <script type="text/javascript" src="{{ ASSET_URL }}"></script>
    {% endassets %}

You can also pass in ``depends`` through templatetags with a slightly
modified comma-delimated syntax, e.g.
``depends="myfile.js,path/to/file.js"``.

The management command
~~~~~~~~~~~~~~~~~~~~~~

``django-assets`` also provides a management command, ``manage.py assets``.
It can be used to manually cause your bundles to be rebuilt::

    $ ./manage.py assets build
    Building asset: cache/site.js
    Building asset: cache/ie7.js
    Building asset: cache/site.css

Note that this is more difficult if you are defining your bundles within
your templates, rather than in code. You then need to use the
``--parse-templates`` option, so the ``build`` command can find the bundles.


``staticfiles`` integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``django-assets`` can integrate with Django's
:doc:`django.contrib.staticfiles <staticfiles>`.


Jinja2 support
~~~~~~~~~~~~~~

See :doc:`jinja2` if you want to use ``django-assets`` with the Jinja2
templating language.


Settings
~~~~~~~~~~~~

See :doc:`settings` for on overview of Django configuration values.


webassets documentation
-----------------------

For further information, have a look at the complete
:ref:`webassets documentation <index>`, and in particular, the
following topics:

- :ref:`All about bundles <webassets:bundles>`
- :ref:`Builtin filters <webassets:builtin-filters>`
- :ref:`Custom filters <webassets:custom-filters>`
- :ref:`CSS compilers <webassets:css-compilers>`
- :ref:`FAQ <webassets:faq>`
