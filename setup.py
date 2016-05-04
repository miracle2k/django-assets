#!/usr/bin/env python
# coding: utf8

from __future__ import with_statement
from setuptools import setup, find_packages

import multiprocessing

# Figure out the version; this could be done by importing the
# module, though that requires dependencies to be already installed,
# which may not be the case when processing a pip requirements
# file, for example.
def parse_version(assignee):
    import os, re
    here = os.path.dirname(os.path.abspath(__file__))
    version_re = re.compile(
        r'%s = (\(.*?\))' % assignee)
    with open(os.path.join(here, 'django_assets', '__init__.py')) as fp:
        for line in fp:
            match = version_re.search(line)
            if match:
                version = eval(match.group(1))
                return ".".join(map(str, version))
        else:
            raise Exception("cannot find version")
version = parse_version('__version__')
webassets_version = parse_version('__webassets_version__')


setup(
    name='django-assets',
    version=version,
    url='http://github.com/miracle2k/django-assets',
    license='BSD',
    author='Michael Elsdörfer',
    author_email='michael@elsdoerfer.com',
    description='Asset management for Django, to compress and merge '\
                'CSS and Javascript files.',
    long_description=__doc__,
    packages=find_packages(exclude=('tests',)),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Django>=1.7',
        'webassets%s' % webassets_version
        ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
    ],
    # make plugin available to pytest
    entry_points = {
        'pytest11': [
            'django_assets = django_assets.pytest_plugin',
        ]
    },
)
