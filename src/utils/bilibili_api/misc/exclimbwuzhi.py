"""
@Author         : Ailitonia
@Date           : 2024/3/25 0:30
@FileName       : exclimbwuzhi
@Project        : nonebot2_miya
@Description    : 激活 buvid3
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

Web 风控相关问题: buvid3, buvid4 获取及激活(ExClimbWuzhi 上传设备指纹消息)见:
https://github.com/SocialSisterYi/bilibili-API-collect/issues/933

相关风控问题见:
https://github.com/SocialSisterYi/bilibili-API-collect/issues/686
https://github.com/SocialSisterYi/bilibili-API-collect/issues/868

Reference: https://github.com/Nemo2011/bilibili-api/commit/f7de473bc42d60604372f80d06244e45a08bdbb4
From: https://github.com/Nemo2011/bilibili-api/blob/f7de473bc42d60604372f80d06244e45a08bdbb4/bilibili_api/utils/exclimbwuzhi.py
Reference: https://github.com/SomeACG/SomeACG-Bot/blob/8027673f6fd90a408d81e4885b5007cb71d852b6/src/platforms/bilibili-api/utils.ts#L21
"""

import base64
import io
import os
import random
import struct
import time
from urllib.parse import quote

import ujson

MOD = 1 << 64


def get_time_milli() -> int:
    return time.time_ns() // 1_000_000


def rotate_left(x: int, k: int) -> int:
    bin_str = bin(x)[2:].rjust(64, '0')
    return int(bin_str[k:] + bin_str[:k], base=2)


def gen_uuid_infoc() -> str:
    t = get_time_milli() % 100000
    mp = list('123456789ABCDEF') + ['10']
    pck = [8, 4, 4, 4, 12]

    def gen_part(x) -> str:
        return ''.join([random.choice(mp) for _ in range(x)])

    return '-'.join([gen_part(x) for x in pck]) + str(t).ljust(5, '0') + 'infoc'


def gen_b_lsid() -> str:
    ret = ''
    for _ in range(8):
        ret += hex(random.randint(0, 15))[2:].upper()
    ret = f'{ret}_{hex(get_time_milli())[2:].upper()}'
    return ret


def gen_buvid_fp(key: str, seed: int):
    source = io.BytesIO(bytes(key, 'ascii'))
    m = murmur3_x64_128(source, seed)
    return f'{hex(m & (MOD - 1))[2:]}{hex(m >> 64)[2:]}'


def murmur3_x64_128(source: io.BufferedIOBase, seed: int) -> int:  # type: ignore
    c1 = 0x87C3_7B91_1142_53D5
    c2 = 0x4CF5_AD43_2745_937F
    c3 = 0x52DC_E729
    c4 = 0x3849_5AB5
    r1, r2, r3, m = 27, 31, 33, 5
    h1, h2 = seed, seed
    processed = 0
    while 1:
        read = source.read(16)
        processed += len(read)
        if len(read) == 16:
            k1 = struct.unpack('<q', read[:8])[0]
            k2 = struct.unpack('<q', read[8:])[0]
            h1 ^= rotate_left(k1 * c1 % MOD, r2) * c2 % MOD
            h1 = ((rotate_left(h1, r1) + h2) * m + c3) % MOD
            h2 ^= rotate_left(k2 * c2 % MOD, r3) * c1 % MOD
            h2 = ((rotate_left(h2, r2) + h1) * m + c4) % MOD
        elif len(read) == 0:
            h1 ^= processed
            h2 ^= processed
            h1 = (h1 + h2) % MOD
            h2 = (h2 + h1) % MOD
            h1 = fmix64(h1)
            h2 = fmix64(h2)
            h1 = (h1 + h2) % MOD
            h2 = (h2 + h1) % MOD
            return (h2 << 64) | h1
        else:
            k1 = 0
            k2 = 0
            if len(read) >= 15:
                k2 ^= int(read[14]) << 48
            if len(read) >= 14:
                k2 ^= int(read[13]) << 40
            if len(read) >= 13:
                k2 ^= int(read[12]) << 32
            if len(read) >= 12:
                k2 ^= int(read[11]) << 24
            if len(read) >= 11:
                k2 ^= int(read[10]) << 16
            if len(read) >= 10:
                k2 ^= int(read[9]) << 8
            if len(read) >= 9:
                k2 ^= int(read[8])
                k2 = rotate_left(k2 * c2 % MOD, r3) * c1 % MOD
                h2 ^= k2
            if len(read) >= 8:
                k1 ^= int(read[7]) << 56
            if len(read) >= 7:
                k1 ^= int(read[6]) << 48
            if len(read) >= 6:
                k1 ^= int(read[5]) << 40
            if len(read) >= 5:
                k1 ^= int(read[4]) << 32
            if len(read) >= 4:
                k1 ^= int(read[3]) << 24
            if len(read) >= 3:
                k1 ^= int(read[2]) << 16
            if len(read) >= 2:
                k1 ^= int(read[1]) << 8
            if len(read) >= 1:
                k1 ^= int(read[0])
            k1 = rotate_left(k1 * c1 % MOD, r2) * c2 % MOD
            h1 ^= k1


def fmix64(k: int) -> int:
    c1 = 0xFF51_AFD7_ED55_8CCD
    c2 = 0xC4CE_B9FE_1A85_EC53
    r = 33
    tmp = k
    tmp ^= tmp >> r
    tmp = tmp * c1 % MOD
    tmp ^= tmp >> r
    tmp = tmp * c2 % MOD
    tmp ^= tmp >> r
    return tmp


def _random_canvas() -> str:
    rand_png = os.urandom(2) + bytes(
        [0x00, 0x00, 0x00, 0x00, 73, 69, 78, 68, 0x00, 0xA0, 0x00, 0x00]
    )
    return base64.b64encode(rand_png).decode('ascii')


def _random_audio() -> float:
    min_ = 124.04347
    max_ = 124.04348
    return random.random() * (max_ - min_) + min_


def _random_png_end() -> str:
    rand_png = (
            os.urandom(32)
            + bytes([0x00, 0x00, 0x00, 0x00, 73, 69, 78, 68])
            + os.urandom(4)
    )
    return base64.b64encode(rand_png).decode('ascii')[-50:]


def gen_payload(
        post_url: str,
        spm_prefix: str,
        uuid: str,
        user_agent: str,
) -> str:
    content = {
        '3064': 1,
        '5062': get_time_milli(),
        '03bf': quote(post_url, safe="!*'()"),
        '39c8': f'{spm_prefix}.fp.risk',
        '34f1': '',
        'd402': '',
        '654a': '',
        '6e7c': '1599x1073',
        '3c43': {
            '2673': 0,
            '5766': 24,
            '6527': 0,
            '7003': 1,
            '807e': 1,
            'b8ce': user_agent,
            '641c': 0,
            '07a4': 'zh-CN',
            '1c57': 32,
            '0bd0': 28,
            '748e': [2561, 1441],
            'd61f': [2561, 1393],
            'fc9d': -480,
            '6aa9': 'Asia/Shanghai',
            '75b8': 1,
            '3b21': 1,
            '8a1c': 0,
            'd52f': 'not available',
            'adca': 'Win32',
            '80c9': [
                [
                    'PDF Viewer',
                    'Portable Document Format',
                    [['application/pdf', 'pdf'], ['text/pdf', 'pdf']],
                ],
                [
                    'Chrome PDF Viewer',
                    'Portable Document Format',
                    [['application/pdf', 'pdf'], ['text/pdf', 'pdf']],
                ],
                [
                    'Chromium PDF Viewer',
                    'Portable Document Format',
                    [['application/pdf', 'pdf'], ['text/pdf', 'pdf']],
                ],
                [
                    'Microsoft Edge PDF Viewer',
                    'Portable Document Format',
                    [['application/pdf', 'pdf'], ['text/pdf', 'pdf']],
                ],
                [
                    'WebKit built-in PDF',
                    'Portable Document Format',
                    [['application/pdf', 'pdf'], ['text/pdf', 'pdf']],
                ],
            ],
            '13ab': 'mW9qAAAAAElFTkSuQmCC',  # Alternative generator `_random_canvas()`
            'bfe9': '//TgNIfAAAAAZJREFUAwBde+3wgcxEHQAAAABJRU5ErkJggg==',  # Alternative generator `_random_png_end()`
            'a3c1': [
                'extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_clip_control;EXT_color_buffer_half_float;EXT_depth_clamp;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_polygon_offset_clamp;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_texture_mirror_clamp_to_edge;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_blend_func_extended;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw;WEBGL_polygon_mode',
                'webgl aliased line width range:[1, 1]',
                'webgl aliased point size range:[1, 1024]',
                'webgl alpha bits:8',
                'webgl antialiasing:yes',
                'webgl blue bits:8',
                'webgl depth bits:24',
                'webgl green bits:8',
                'webgl max anisotropy:16',
                'webgl max combined texture image units:32',
                'webgl max cube map texture size:16384',
                'webgl max fragment uniform vectors:1024',
                'webgl max render buffer size:16384',
                'webgl max texture image units:16',
                'webgl max texture size:16384',
                'webgl max varying vectors:30',
                'webgl max vertex attribs:16',
                'webgl max vertex texture image units:16',
                'webgl max vertex uniform vectors:4095',
                'webgl max viewport dims:[32767, 32767]',
                'webgl red bits:8',
                'webgl renderer:WebKit WebGL',
                'webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)',
                'webgl stencil bits:0',
                'webgl vendor:WebKit',
                'webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)',
                'webgl unmasked vendor:Google Inc. (NVIDIA)',
                'webgl unmasked renderer:ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 SUPER (0x00002702) Direct3D11 '
                'vs_5_0 ps_5_0, D3D11)',
                'webgl vertex shader high float precision:23',
                'webgl vertex shader high float precision rangeMin:127',
                'webgl vertex shader high float precision rangeMax:127',
                'webgl vertex shader medium float precision:23',
                'webgl vertex shader medium float precision rangeMin:127',
                'webgl vertex shader medium float precision rangeMax:127',
                'webgl vertex shader low float precision:23',
                'webgl vertex shader low float precision rangeMin:127',
                'webgl vertex shader low float precision rangeMax:127',
                'webgl fragment shader high float precision:23',
                'webgl fragment shader high float precision rangeMin:127',
                'webgl fragment shader high float precision rangeMax:127',
                'webgl fragment shader medium float precision:23',
                'webgl fragment shader medium float precision rangeMin:127',
                'webgl fragment shader medium float precision rangeMax:127',
                'webgl fragment shader low float precision:23',
                'webgl fragment shader low float precision rangeMin:127',
                'webgl fragment shader low float precision rangeMax:127',
                'webgl vertex shader high int precision:0',
                'webgl vertex shader high int precision rangeMin:31',
                'webgl vertex shader high int precision rangeMax:30',
                'webgl vertex shader medium int precision:0',
                'webgl vertex shader medium int precision rangeMin:31',
                'webgl vertex shader medium int precision rangeMax:30',
                'webgl vertex shader low int precision:0',
                'webgl vertex shader low int precision rangeMin:31',
                'webgl vertex shader low int precision rangeMax:30',
                'webgl fragment shader high int precision:0',
                'webgl fragment shader high int precision rangeMin:31',
                'webgl fragment shader high int precision rangeMax:30',
                'webgl fragment shader medium int precision:0',
                'webgl fragment shader medium int precision rangeMin:31',
                'webgl fragment shader medium int precision rangeMax:30',
                'webgl fragment shader low int precision:0',
                'webgl fragment shader low int precision rangeMin:31',
                'webgl fragment shader low int precision rangeMax:30'
            ],
            '6bc5': (
                'Google Inc. (NVIDIA)~ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 SUPER (0x00002702) Direct3D11 '
                'vs_5_0 ps_5_0, D3D11)'
            ),
            'ed31': 0,
            '72bd': 0,
            '097b': 0,
            '52cd': [0, 0, 0],
            'a658': [
                'Arial',
                'Arial Black',
                'Arial Narrow',
                'Book Antiqua',
                'Bookman Old Style',
                'Calibri',
                'Cambria',
                'Cambria Math',
                'Century',
                'Century Gothic',
                'Century Schoolbook',
                'Comic Sans MS',
                'Consolas',
                'Courier',
                'Courier New',
                'Georgia',
                'Helvetica',
                'Impact',
                'Lucida Bright',
                'Lucida Calligraphy',
                'Lucida Console',
                'Lucida Fax',
                'Lucida Handwriting',
                'Lucida Sans',
                'Lucida Sans Typewriter',
                'Lucida Sans Unicode',
                'Microsoft Sans Serif',
                'Monotype Corsiva',
                'MS Gothic',
                'MS PGothic',
                'MS Reference Sans Serif',
                'MS Sans Serif',
                'MS Serif',
                'Palatino Linotype',
                'Segoe Print',
                'Segoe Script',
                'Segoe UI',
                'Segoe UI Light',
                'Segoe UI Semibold',
                'Segoe UI Symbol',
                'Tahoma',
                'Times',
                'Times New Roman',
                'Trebuchet MS',
                'Verdana',
                'Wingdings',
                'Wingdings 2',
                'Wingdings 3',
            ],
            'd02f': '124.04347776696522',  # Alternative generator `_random_audio()`
        },
        '54ef': (
            '{"b_ut":"","home_version":"V8","in_new_ab":true,'
            '"ab_version":{"for_ai_home_version":"V8","in_theme_version":"OPEN","enable_web_push":"DISABLE",'
            '"enable_ai_floor_api":"ENABLE","enable_shortcut_key":"DISABLE","rcmd_timeout_config":"550",'
            '"home_performance_opt":"ssr_fetch_opt","infra_projection":"OFF"},'
            '"ab_split_num":{"for_ai_home_version":54,"in_theme_version":30,"enable_web_push":10,'
            '"enable_ai_floor_api":137,"enable_shortcut_key":54,"rcmd_timeout_config":49,'
            '"home_performance_opt":49,"infra_projection":49},'
            '"uniq_page_id":"1671272756362","is_modern":true}'
        ),
        '8b94': '',
        'df35': uuid,
        '07a4': 'zh-CN',
        '5f45': None,
        'db46': 0,
    }
    return ujson.dumps(
        {'payload': ujson.dumps(content, separators=(',', ':'), escape_forward_slashes=False)},
        separators=(',', ':'),
        escape_forward_slashes=False,
    )


__all__ = [
    'gen_b_lsid',
    'gen_buvid_fp',
    'gen_payload',
    'gen_uuid_infoc',
]
