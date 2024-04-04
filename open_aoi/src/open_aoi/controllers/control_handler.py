from typing import List, Optional, Tuple


class Module:
    parameters: List

    @staticmethod
    def validate_specification(specification: dict) -> Tuple[bool, Optional[str]]:
        try:
            assert (
                specification.get("parameters") is not None
            ), "Parameters are missing!"
            assert (
                specification.get("process") is not None
            ), "Process function is missing!"
        except Exception as e:
            return False, str(e)
        return True, None

    def __init__(self, specification: dict) -> None:
        self._spec = specification
        res, detail = self.validate_specification(specification)
        assert res, detail

        self.parameters = specification["parameters"]
        self.process = specification["process"]

    def process(self):
        raise NotImplemented()


class ControlHandlerController(Controller):
    model = ControlHandlerModel

    @classmethod
    def create(cls):
        raise NotImplemented()
