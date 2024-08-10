from src.service.artwork_proxy import DanbooruArtworkProxy
from ..internal import BaseArtworkCollection


class DanbooruArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> DanbooruArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[DanbooruArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> DanbooruArtworkProxy: ...
