import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def activate_conda():
    os.system("conda activate base")


def pytest_configure(config):
    config.option.coverage = True
    config.option.coverage_report = "term-missing"
    config.option.coverage_html_report = "htmlcov"
    config.option.coverage_include = [
        "your_package_name/*"
    ]  # Update with your package name


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item.add_marker(pytest.mark.local)  # Mark tests as local by default


def pytest_addoption(parser):
    parser.addoption("--global", action="store_true", help="Show global status")
