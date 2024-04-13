ERROR = "error"
IDLE = "idle"
BUSY = "busy"


class StandardServiceMixin:
    service_status_default: str = IDLE
    service_status: str = service_status_default

    def _set_status(self, msg: str):
        self.service_status = msg

    def expose_status(self, request, response):
        response.status = self.service_status
        return response
