#!/usr/bin/env python
"""Django 的命令列工具（migrate / runserver / check ...）。

教學重點：所有 manage.py 指令都從這裡進入，
它只做一件事 —— 指定 settings 模組，然後把參數交給 Django。
"""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
