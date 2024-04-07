from open_aoi.mixins import Mixin


class InspectionStatisticsMixin(Mixin):
    @property
    def overall_passed(self):
        raise NotImplementedError()
