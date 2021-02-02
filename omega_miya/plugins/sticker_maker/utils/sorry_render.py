import hashlib
import os
import re
from subprocess import Popen, PIPE
from jinja2 import Template
from nonebot import log


def calculate_hash(src):
    m2 = hashlib.md5()
    m2.update(str(src).encode("utf8"))
    return m2.hexdigest()


def render_gif(template_name, sentences):
    filename = template_name + "-" + calculate_hash(sentences) + ".gif"
    plugin_path = os.path.dirname(__file__)
    gif_sticker_path = os.path.join(plugin_path, 'gif_sticker')
    if not os.path.exists(gif_sticker_path):
        os.mkdir(gif_sticker_path)
    gif_path = os.path.join(gif_sticker_path, filename)
    if os.path.exists(gif_path):
        return gif_path
    make_gif_with_ffmpeg(template_name, sentences, filename)
    return gif_path


def ass_text(template_name):
    plugin_path = os.path.dirname(__file__)
    template_path = os.path.join(plugin_path, 'gif_static', template_name, 'template.tpl')
    with open(template_path) as fp:
        content = fp.read()
    return content


def render_ass(template_name, sentences, filename):
    plugin_path = os.path.dirname(__file__)
    output_file_path = os.path.join(plugin_path, 'gif_sticker', f'{filename}.ass')
    template = ass_text(template_name)
    rendered_ass_text = Template(template).render(sentences=sentences)
    with open(output_file_path, "w", encoding="utf8") as fp:
        fp.write(rendered_ass_text)
    # 处理路径字符, 否则windows绝对路径直接放到ffmpeg中用会出错,
    # 见https://superuser.com/questions/1251296/get-error-while-adding-subtitles-with-ffmpeg
    output_file_path = re.sub(r'\\', '/', output_file_path)
    output_file_path = re.sub(r':', '\\:', output_file_path)
    return output_file_path


def make_gif_with_ffmpeg(template_name, sentences, filename):
    ass_path = render_ass(template_name, sentences, filename)
    plugin_path = os.path.dirname(__file__)
    gif_path = os.path.join(plugin_path, 'gif_sticker', filename)
    video_path = os.path.join(plugin_path, 'gif_static', template_name, 'template.mp4')
    log.logger.debug(ass_path, gif_path, video_path)

    # 使用插件携带ffmpeg程序执行
    # cmd = f'''{plugin_path}/ffmpeg -i {video_path} -r 8 -vf "ass='{ass_path}',scale=300:-1" -y {gif_path}'''

    # 使用系统环境ffmpeg执行
    cmd = f'''ffmpeg -i {video_path} -r 8 -vf "ass='{ass_path}',scale=300:-1" -y {gif_path}'''

    log.logger.debug(cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    p.wait()
    if p.returncode != 0:
        log.logger.error("Error.")
        return -1


if __name__ == '__main__':
    log.logger.info(str(["hello"]))
    test_sentences = ["好啊", "就算你是一流工程师", "就算你出报告再完美", "我叫你改报告你就要改",
                      "毕竟我是客户", "客户了不起啊", "sorry 客户真的了不起", "以后叫他天天改报告", "天天改 天天改"]
    test_template_name = "sorry"
    path = render_gif(test_template_name, test_sentences)
    print(path)
    log.logger.info(path)
