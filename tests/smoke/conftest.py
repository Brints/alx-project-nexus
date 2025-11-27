import pytest


def pytest_addoption(parser):
    """
    Register the custom --url command line option.
    """
    parser.addoption(
        "--url",
        action="store",
        default="http://localhost:8000",
        help="Base URL for the application under test",
    )


@pytest.fixture
def api_url(request):
    """
    Fixture to retrieve the URL in tests.
    Ensures no trailing slash for consistent concatenation.
    """
    url = request.config.getoption("--url")
    return url.rstrip("/")
