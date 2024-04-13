from open_aoi.models import ConnectedComponentModel, ControlZoneModel
from open_aoi.controllers import Controller


class ConnectedComponentController(Controller):
    _model = ConnectedComponentModel

    def create(
        self,
        stat_left: int,
        stat_top: int,
        stat_width: int,
        stat_height: int,
        control_zone: ControlZoneModel,
    ) -> ConnectedComponentModel:
        assert stat_left >= 0
        assert stat_top >= 0
        assert stat_width >= 0
        assert stat_height >= 0
        
        obj = ConnectedComponentModel(
            stat_left=stat_left,
            stat_top=stat_top,
            stat_width=stat_width,
            stat_height=stat_height,
            control_zone=control_zone,
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return True
