from rest_framework.renderers import JSONRenderer


class CustomJSONRenderer(JSONRenderer):
    """
    A custom renderer to create a standardized success response wrapper.
    """

    # override the 'render' method
    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Get the status code from the response context
        response = renderer_context["response"]
        status_code = response.status_code

        if status_code == 204:
            return super().render(None, accepted_media_type, renderer_context)

        if (
            isinstance(data, dict) and data.get("status") == "error"
        ) or "detail" in str(data):
            return super().render(data, accepted_media_type, renderer_context)

        # Allow the view to provide a custom message
        message = "Success"
        payload = {}

        if isinstance(data, dict):
            message = data.pop("message", "Success")
            payload = data
        elif data is not None:
            payload = data

        # Create the standardized response structure
        response_data = {
            "status": "success",
            "status_code": status_code,
            "message": message,
            "data": payload,
        }

        return super().render(response_data, accepted_media_type, renderer_context)
