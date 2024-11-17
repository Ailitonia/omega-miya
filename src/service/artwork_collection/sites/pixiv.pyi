from src.service.artwork_proxy import PixivArtworkProxy

from ..internal import BaseArtworkCollection

class PixivArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> PixivArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[PixivArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> PixivArtworkProxy: ...
