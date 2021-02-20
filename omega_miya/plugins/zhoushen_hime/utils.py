import aiohttp
from omega_miya.utils.Omega_Base import Result


async def download_file(url: str, file_path: str) -> Result:
    # 尝试从服务器下载资源
    error_info = ''
    timeout_count = 0
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                async with session.get(url=url, headers=headers, timeout=timeout) as resp:
                    dl_file = await resp.read()
                    with open(file_path, 'wb+') as f:
                        f.write(dl_file)
                        return Result(error=False, info='Success', result=0)
        except Exception as _e:
            error_info += f'{__name__}: {repr(_e)} Occurred in getting trying {timeout_count + 1}'
        finally:
            timeout_count += 1
    else:
        error_info += f'{__name__}: Failed too many times.'
        return Result(error=True, info=f'Download failed, error info: {error_info}', result=-1)
