"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:30
@FileName       : base_model.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseTencentCloudModel(BaseModel):
    """腾讯云 API 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class BaseTencentCloudError(BaseModel):
    """Api 调用失败错误信息

    - Code: 错误码
    - Message: 错误消息
    """
    Code: str
    Message: str


class BaseTencentCloudErrorResponse(BaseModel):
    """Api 调用失败返回基类

    - Error: 错误内容
    - RequestId: 唯一请求 ID, 由服务端生成, 每次请求都会返回(若请求因其他原因未能抵达服务端, 则该次请求不会获得 RequestId), 定位问题时需要提供该次请求的 RequestId
    """
    Error: BaseTencentCloudError
    RequestId: Optional[UUID] = None


class BaseTencentCloudSuccessResponse(BaseModel):
    """Api 调用成功返回基类

    - RequestId: 唯一请求 ID, 由服务端生成, 每次请求都会返回(若请求因其他原因未能抵达服务端, 则该次请求不会获得 RequestId), 定位问题时需要提供该次请求的 RequestId
    """
    RequestId: Optional[UUID] = None


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
