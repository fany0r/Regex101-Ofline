import os
import sys
import requests
import re
import shutil
import ast
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from common import log

# Constants
BASE_DIR = 'regex101_offline'
BASE_URL = 'https://regex101.com'
STATIC_DIR = os.path.join(BASE_DIR, "static")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")
OFFLINE_DIR = os.path.join(BASE_DIR, "offline")
FONTS_DIR = os.path.join(STATIC_DIR, "fonts")
API = os.path.join(BASE_DIR, "api/library/1")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'X-Forwarded-For': '127.0.0.1',

}

workbox_version = None

# 持久连接
session = requests.Session()
session.headers.update({'Connection': 'keep-alive'})

def create_directories():
    dirs = [ASSETS_DIR, OFFLINE_DIR, FONTS_DIR, API]
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)

def delete_base_dir():
    log.info(f"[*] 正在清理旧的 {BASE_DIR} 目录")
    if os.path.exists(BASE_DIR):
        try:
            shutil.rmtree(BASE_DIR)
            log.info(f"[*] {BASE_DIR} 目录已删除。")
        except Exception as e:
            log.error(f"[-] 删除 {BASE_DIR} 目录时出错: {e}")
    else:
        log.error(f"[-] 目录 {BASE_DIR} 不存在。")

    log.info("[*] 旧目录文件已清理")

def fetch_content(url):
    try:
        response = session.get(url, headers=HEADERS, stream=True)
        if response.status_code == 200:
            return response
        log.error(f"[-] 无法下载文件 {url}, 状态码: {response.status_code}")
    except Exception as e:
        log.error(f"[-] 下载出错: {url}, 错误信息: {e}")
    return None

def download_file(url, save_path):
    if os.path.exists(save_path):
        log.warn(f"[!] 已存在: {url}, 跳过下载。")
        return

    response = fetch_content(url)
    if response:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(8192):
                file.write(chunk)
        log.info(f"[*] 已下载: {url}")

def generate_save_path(url_path, is_asset=False, is_font=False):
    path_parts = url_path.split('/')
    if is_font:
        return os.path.join(FONTS_DIR, os.path.basename(url_path))
    elif is_asset:
        return os.path.join(ASSETS_DIR, *path_parts[3:])
    elif path_parts[1] == 'static':
        return os.path.join(STATIC_DIR, *path_parts[2:])
    return None

def mactch_workbox():
    global workbox_version
    sw_file_path = os.path.join(BASE_DIR, "sw.js")

    with open(sw_file_path, 'r', encoding='utf-8') as file:
        sw_content = file.read()
 
    workbox_match = re.search(r'workbox-[a-zA-Z0-9]+', sw_content)
    workbox_version = f"{workbox_match.group(0)}.js" if workbox_match else None

def scrape_website():
    log.info("[开始生成离线版 regex101]")

    index_file_path = os.path.join(BASE_DIR, "index.html")
    sw_file_path = os.path.join(BASE_DIR, "sw.js")

    response = fetch_content(BASE_URL)
    sw = fetch_content(urljoin(BASE_URL, f"/sw.js"))

    if not response or not sw:
        # missing_file = "index.html" if not response else "sw.js"
        log.error("[-] 网站布局可能以改变。")
        sys.exit(1)

    with open(index_file_path, 'w', encoding='utf-8') as index_file:
        index_file.write(response.text)
    with open(sw_file_path, 'w', encoding='utf-8') as sw_file:
        sw_file.write(sw.text)

    mactch_workbox()
    file_list = [
        'plausible.js', workbox_version, 'changelog.md', 'flavors.md',
        'icon-36.png', 'icon-48.png', 'icon-512.png', 'maskable-icon-512.png'
    ]

    for file_name in file_list:
        if file_name.endswith(('.md','.png')):
            file_url = urljoin(BASE_URL, f"/static/assets/{file_name}")
            save_path = os.path.join(ASSETS_DIR, file_name)
        elif file_name == 'plausible.js':
            file_url = urljoin(f"https://analytics.regex101.com/js/", file_name)
            save_path = os.path.join(STATIC_DIR, "js", file_name)
        else:
            file_url = urljoin(BASE_URL, file_name)
            save_path = os.path.join(BASE_DIR, file_name)

        download_file(file_url, save_path)

    soup = BeautifulSoup(response.text, 'html.parser')
    for link_tag in soup.find_all('link', rel=True):
        href = link_tag.get('href')
        if href:
            file_url = urljoin(BASE_URL, href)
            save_path = generate_save_path(href, is_asset=href.startswith('/static/assets'))
            if save_path:
                download_file(file_url, save_path)


def download_from_sw():
    log.info("[从 sw.js 提取所需资源并下载]")

    sw_file_path = os.path.join(BASE_DIR, "sw.js")
    with open(sw_file_path, 'r', encoding='utf-8') as file:
        sw_content = file.read()

    urls = re.findall(r'url:"([^"]+)"', sw_content)
    for url in urls:
        if url == "/offline":
            continue
        file_url = urljoin(BASE_URL, url)
        save_path = generate_save_path(url, is_asset=url.startswith('/static/assets'))
        if save_path:
            download_file(file_url, save_path)

    log.info("[*] sw 所需资源已下载")

def extract_json_paths(content):
    return re.findall(r'assets/[a-zA-Z0-9_.-]+\.json', content)

def download_json_from_bundle_js():
    log.info("[下载语言文件]")

    for file_name in os.listdir(STATIC_DIR):
        if file_name.startswith("bundle") and file_name.endswith(".js"):
            with open(os.path.join(STATIC_DIR, file_name), 'r', encoding='utf-8') as f:
                content = f.read()
            json_paths = extract_json_paths(content)
            for json_path in json_paths:
                json_url = f"{BASE_URL}/static/{json_path}"
                json_save_path = generate_save_path(f"/static/{json_path}", is_asset=True)
                download_file(json_url, json_save_path)

    log.info("[*] 语言文件已下载")

def extract_js_dict(content):
    return ast.literal_eval(re.findall(r'(?<=o\.u=e=>\(\()[\w\W]*(?=\[e\]\|\|e)', content)[0])

def extract_js_suffix(content):
    return ast.literal_eval(re.findall(r'(?<=\+"\."\+)[\w\W]*(?=\[e\]\+"\.chunk\.js")', content)[0])

def extract_css_suffix(content):
    return ast.literal_eval(re.findall(r'(?<=e\+"\."\+)[\w\W]*(?=\[e\]\+"\.css")', content)[0])

def download_missing_js_css(js_dict, js_suffix_dict, css_dict):
    # 下载缺失的 JS 文件
    for key, prefix in js_dict.items():
        if key in js_suffix_dict:
            js_name = f"{prefix}.{js_suffix_dict[key]}.chunk.js"
            js_url = f"{BASE_URL}/static/{js_name}"
            download_file(js_url, os.path.join(STATIC_DIR, js_name))

    # 下载缺失的 CSS 文件
    for key, css_suffix in css_dict.items():
        css_name = f"{key}.{css_suffix}.css"
        css_url = f"{BASE_URL}/static/{css_name}"
        download_file(css_url, os.path.join(STATIC_DIR, css_name))

def download_chunk_and_css_files():
    log.info("[下载缺失的 js 和 css 文件]")

    # 打开bundle开头的js文件
    for file_name in os.listdir(STATIC_DIR):
        if file_name.startswith("bundle") and file_name.endswith(".js"):
            with open(os.path.join(STATIC_DIR, file_name), 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 匹配js发起的请求相关代码
            patterns = [
                r'(?<=const k=\(\)=>\{)[\w\W]*?(?=\};async function)',  # CESIEKJM.json
                r'(?<=async function l\(\)\{)[\w\W]*?(?=\}async function c)',  # Sentry监控
                r'(?<=async function u\(e,t\)\{)[\w\W]*?(?=\}function)' # 消除报错
            ]

            # 删除js中发起外部请求的代码
            for pattern in patterns:
                del_js_content = re.findall(pattern, content, re.IGNORECASE)
                for match in del_js_content:
                    content = content.replace(match, str("return null;"))

            # 保存修改后的js文件
            with open(os.path.join(STATIC_DIR, file_name), 'w', encoding='utf-8') as f:
                f.write(content )

            # 提取依赖的js和css文件名前后缀
            js_dict = extract_js_dict(content)
            js_suffix_dict = extract_js_suffix(content)
            css_dict = extract_css_suffix(content)

            # 下载缺失的 JS 和 CSS 文件
            download_missing_js_css(js_dict, js_suffix_dict, css_dict)

            break
    log.info("[*] 缺失的 js 和 css 已下载")

def hide_sponsors(soup):
    sponsors_div = soup.find('div', string='Sponsors')
    if sponsors_div:
        parent_div = sponsors_div.find_parent('div')  # 父 div
        if parent_div and parent_div.has_attr('class'):
            target_class = '.' + parent_div['class'][0]  # 只取第一个 class 名称

    # 查找包含 target_class 的 CSS 文件并添加隐藏样式
    css_file_path = next(
        (os.path.join(STATIC_DIR, file_name) for file_name in os.listdir(STATIC_DIR)
        if file_name.endswith('.css') and target_class in open(os.path.join(STATIC_DIR, file_name), 'r', encoding='utf-8').read()), 
        None
    )

    # 如果找到文件，则添加隐藏样式
    if css_file_path:
        hide_css = f"\n{target_class} {{ display: none !important; }}\n"
        with open(css_file_path, 'a', encoding='utf-8') as css_file:
            css_file.write(hide_css)
        log.info("[*] 顺带隐藏了Sponsors")

def replace_google_fonts():
    log.info("[下载字体到本地并修改引用路径]")

    # 解析 index.html 文件
    index_file_path = os.path.join(BASE_DIR, "index.html")
    with open(index_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # 提取包含字体链接的 CSS2
    css2_links = soup.find_all("link", href=lambda href: href and "https://fonts.googleapis.com/" in href)

    if css2_links:
        '''下载字体文件并修改 CSS2 中字体的链接'''
        for link in css2_links:
            font_url = link["href"]
            response = fetch_content(font_url)
            if not response:
                continue
            css2_content = response.text
            # 修改CSS2文件名，防止在 windows下路径冲突问题
            '''https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&family=Source+Code+Pro:wght@400;500;700&display=swap'''
            hash_name = hashlib.md5(font_url.encode()).hexdigest()
            css2_file_name = f"font_{hash_name}.css"
            css2_save_path = os.path.join(FONTS_DIR, css2_file_name)

            # 查找并下载字体文件，将其替换为本地路径
            font_file_urls = re.findall(r'url\((https://fonts\.gstatic\.com/s/[^)]+)\)', css2_content)
            for font_file_url in font_file_urls:
                font_file_name = os.path.basename(font_file_url)
                font_save_path = os.path.join(FONTS_DIR, font_file_name)
                download_file(font_file_url, font_save_path)
                css2_content = css2_content.replace(font_file_url, f"./{font_file_name}") # 替换为本地路径

            # 保存修改后的 CSS2 文件
            with open(css2_save_path, 'w', encoding='utf-8') as css_file:
                css_file.write(css2_content)

            link["href"] = f"./static/fonts/{css2_file_name}"

            log.info("[*] 字体引用已改为本地路径")

        # 顺带删除主页面左下角的 Sponsors
        hide_sponsors(soup)

    # 顺带修改 plausible.js 引用路径
    plausible_script = soup.find("script", src="https://analytics.regex101.com/js/plausible.js")

    if plausible_script:
        plausible_script["src"] = "./static/js/plausible.js"
        with open(index_file_path, 'w', encoding='utf-8') as file:
            file.write(str(soup))

def main():
    # delete_base_dir() # 每次执行时先清理旧的目录，可选
    create_directories()
    scrape_website()
    download_from_sw()
    download_json_from_bundle_js()
    download_chunk_and_css_files()
    replace_google_fonts()
    log.info("[*] 已生成离线版 regex101")

if __name__ == "__main__":
    main()
