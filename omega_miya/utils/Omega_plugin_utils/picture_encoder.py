import os
import base64
from nonebot import logger
from dataclasses import dataclass


class PicEncoder(object):
    @dataclass
    class __Result:
        error: bool
        info: str
        result: str

        def success(self) -> bool:
            if not self.error:
                return True
            else:
                return False

    @classmethod
    def file_to_b64(cls, file_path: str) -> __Result:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return cls.__Result(error=True, info='File not exists', result='')

        try:
            with open(abs_path, 'rb') as f:
                b64 = base64.b64encode(f.read())
            b64 = str(b64, encoding='utf-8')
            b64 = 'base64://' + b64
            return cls.__Result(error=True, info='Success', result=b64)
        except Exception as e:
            logger.opt(colors=True).warning(f'<Y><lw>PicEncoder</lw></Y> file_to_b64 failed, <y>Error</y>: {repr(e)}')
            return cls.__Result(error=True, info=repr(e), result='')

    @classmethod
    def bytes_to_b64(cls, image: bytes) -> __Result:
        try:
            b64 = str(base64.b64encode(image), encoding='utf-8')
            b64 = 'base64://' + b64
            return cls.__Result(error=False, info='Success', result=b64)
        except Exception as e:
            logger.opt(colors=True).warning(f'<Y><lw>PicEncoder</lw></Y> bytes_to_b64 failed, <y>Error</y>: {repr(e)}')
            return cls.__Result(error=True, info=repr(e), result='')


__all__ = [
    'PicEncoder'
]
