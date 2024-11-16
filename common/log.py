# -*- coding: utf-8 -*-

import time


def error(message):
    print(f"\033[91m\033[3m{time.strftime('%Y-%m-%d %H:%M:%S')} : {message}\033[0m")


def info(message):
    print(f"\033[92m\033[3m{time.strftime('%Y-%m-%d %H:%M:%S')} : {message}\033[0m")


def warn(message):
    print(f"\033[33m\033[3m{time.strftime('%Y-%m-%d %H:%M:%S')} : {message}\033[0m")
