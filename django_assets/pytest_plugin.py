import pytest
import django_assets.env

@pytest.fixture(autouse=True)
def set_django_assets_env():
    print("Set django assets environment")
    django_assets.env.get_env() # initialise django-assets settings
