from src.service.artwork_proxy import NoneArtworkProxy

from ..internal import BaseArtworkCollection

class NoneArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> NoneArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[NoneArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> NoneArtworkProxy: ...
