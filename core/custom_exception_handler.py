import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    A custom exception handler to create a standardized error response.
    """
    response = exception_handler(exc, context)

    if response is None:
        logger.error(f"Unhandled exception: {exc}")

        return Response(
            {
                'status': 'error',
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'An unexpected internal error occurred.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    status_code = response.status_code
    message = 'An error occurred.'

    if isinstance(response.data, dict):
        if 'detail' in response.data:
            message = response.data['detail']
        else:
            try:
                first_key = next(iter(response.data))
                first_error_list = response.data[first_key]
                if isinstance(first_error_list, list):
                    message = f"{first_key.title()}: {first_error_list[0]}"
                else:
                    message = str(first_error_list)
            except (StopIteration, TypeError):
                message = 'Invalid input.'
    elif isinstance(response.data, list) and response.data:
        message = response.data[0]

    custom_response_data = {
        'status': 'error',
        'status_code': status_code,
        'message': str(message)
    }

    response.data = custom_response_data
    return response
