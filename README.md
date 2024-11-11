# 介绍 | Introduction

本项目是基于 regex101.com 生成的离线版 regex101。| This project is based on regex101.com to generate an offline version of regex101.

当然，你也可以在 [Release](https://github.com/fany0r/Regex101-Ofline/releases)页面下载已经生成好的离线版regex101放到本地 Http 服务器中使用。| Of course, you can also download the generated offline version of regex101 from the [Release](https://github.com/fany0r/Regex101-Ofline/releases) page and put it into your local HTTP server for use.

## 环境要求 | Environment
 - python 3.8+
 - Http 服务器(如：nginx 或者 python 内置的 http 服务器) | Http server (such as nginx or python built-in http server)

## 使用方法 | Usage

1. 下载本项目。| Download this project.
```bash
git clone https://github.com/fany0r/Regex101-Ofline.git
cd Regex101-Ofline
pip install -r requirements.txt
python get_regex101_offline.py
```

2. 运行 Http 服务器。| Run Http server.
```bash
cd regex101_offline
python -m http.server 8080
```
这里附上一个各大语言的 Http 服务器的启动命令的[列表。](https://gist.github.com/willurd/5720255) | Here is a [list](https://gist.github.com/willurd/5720255) of commands to start Http servers for various languages.

3. 访问 http://127.0.0.1:8080 | Access URL_ADDRESS

## 注意 | Notice

1. regex101.com 可能会随时更新页面，本项目不保证页面的稳定性。| regex101.com may update the page at any time, and this project does not guarantee the stability of the page.
2. 目前可克隆最新版 regex101 为 2024年11月1日的 v12.0.11。| The latest version of regex101 that can be cloned is v12.0.11 on November 1, 2024.
