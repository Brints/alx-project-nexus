import requests
import pytest


def test_health_check(api_url):
    """
    Verifies the application is running and the /health/ endpoint works.
    """
    endpoint = f"{api_url}/health/"
    print(f"Testing endpoint: {endpoint}")

    try:
        response = requests.get(endpoint, timeout=10)

        # Check if status is 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        # Check if response JSON is correct
        json_data = response.json()
        assert json_data.get("status") == "healthy", f"Unexpected response: {json_data}"

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Connection to {endpoint} failed: {str(e)}")


def test_public_api_docs(api_url):
    """
    Verifies that the Swagger/OpenAPI documentation loads.
    This confirms static files and DRF are working.
    """
    endpoint = f"{api_url}/api/docs/"

    try:
        response = requests.get(endpoint, timeout=10)
        assert (
            response.status_code == 200
        ), f"Docs page failed with {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Connection to {endpoint} failed: {str(e)}")
