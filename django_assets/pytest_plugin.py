import pytest
import django_assets.env

@pytest.fixture
def set_django_assets_env():
    django_assets.env.get_env()  # initialise django-assets settings
