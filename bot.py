"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午10:44
@FileName       : omega_any_artworks
@Project        : bot.py
@Description    : [Deactivated]omega-miya 启动入口文件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""


def omega_miya_main():
    from src.cli import build_cli_parser, execute_cli_handler, parse_cli_args

    parser = build_cli_parser()
    args = parse_cli_args(parser.parse_args())

    execute_cli_handler(args)


if __name__ == '__main__':
    omega_miya_main()
