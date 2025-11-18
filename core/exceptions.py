from rest_framework import status
from rest_framework.exceptions import APIException


class NotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
