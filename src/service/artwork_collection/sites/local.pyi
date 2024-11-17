from src.service.artwork_proxy import LocalCollectedArtworkProxy

from ..internal import BaseArtworkCollection

class LocalCollectedArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> LocalCollectedArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[LocalCollectedArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> LocalCollectedArtworkProxy: ...
