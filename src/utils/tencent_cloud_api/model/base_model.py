"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:30
@FileName       : base_model.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseTencentCloudModel(BaseModel):
    """腾讯云 API 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True)


class BaseTencentCloudError(BaseModel):
    """Api 调用失败错误信息"""
    Code: str
    Message: str


class BaseTencentCloudErrorResponse(BaseModel):
    """Api 调用失败返回基类"""
    Error: BaseTencentCloudError
    RequestId: UUID


class BaseTencentCloudSuccessResponse(BaseModel):
    """Api 调用成功返回基类"""
    RequestId: UUID


class BaseTencentCloudResponse(BaseModel):
    """Api 调用返回基类"""
    Response: BaseTencentCloudErrorResponse | BaseTencentCloudSuccessResponse

    @property
    def error(self) -> bool:
        return isinstance(self.Response, BaseTencentCloudErrorResponse)

    @property
    def success(self) -> bool:
        return not self.error


__all = [
    'BaseTencentCloudModel',
    'BaseTencentCloudErrorResponse',
    'BaseTencentCloudSuccessResponse',
    'BaseTencentCloudResponse'
]
