from open_aoi_core.models import ConnectedComponentModel, InspectionZoneModel
from open_aoi_core.controllers import Controller


class ConnectedComponentController(Controller):
    _model = ConnectedComponentModel

    def create(
        self,
        stat_left: int,
        stat_top: int,
        stat_width: int,
        stat_height: int,
        inspection_zone: InspectionZoneModel,
    ) -> ConnectedComponentModel:
        """Create connected component"""
        assert stat_left >= 0
        assert stat_top >= 0
        assert stat_width >= 0
        assert stat_height >= 0

        entity = ConnectedComponentModel(
            stat_left=stat_left,
            stat_top=stat_top,
            stat_width=stat_width,
            stat_height=stat_height,
            inspection_zone=inspection_zone,
        )
        self.session.add(entity)
        return entity

    def allow_delete_hook(self, id: int) -> bool:
        # Connected components do not have dependencies
        return True
