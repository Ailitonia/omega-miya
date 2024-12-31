from src.service.artwork_proxy import (
    BehoimiArtworkProxy,
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
)

from ..internal import BaseArtworkCollection

class DanbooruArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> DanbooruArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[DanbooruArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> DanbooruArtworkProxy: ...


class GelbooruArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> GelbooruArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[GelbooruArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> GelbooruArtworkProxy: ...


class BehoimiArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> BehoimiArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[BehoimiArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> BehoimiArtworkProxy: ...


class KonachanArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> KonachanArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[KonachanArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> KonachanArtworkProxy: ...


class KonachanSafeArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> KonachanSafeArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[KonachanSafeArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> KonachanSafeArtworkProxy: ...


class YandereArtworkCollection(BaseArtworkCollection):
    @property
    def artwork_proxy(self) -> YandereArtworkProxy: ...

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[YandereArtworkProxy]: ...

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> YandereArtworkProxy: ...
