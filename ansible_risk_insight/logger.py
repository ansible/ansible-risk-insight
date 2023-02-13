# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2023 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import logging


_logger = None

log_level_map = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def set_logger_channel(channel: str = ""):
    global _logger
    _logger = logging.getLogger(channel)
    handler = logging.StreamHandler(sys.stdout)
    # default formatter
    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)


def set_log_level(level_str: str = "info"):
    global _logger
    level = log_level_map.get(level_str.lower(), None)
    _logger.setLevel(level)


def exception(*args, **kwargs):
    _logger.exception(*args, **kwargs)


def error(*args, **kwargs):
    _logger.error(*args, **kwargs)


def warning(*args, **kwargs):
    _logger.warning(*args, **kwargs)


def info(*args, **kwargs):
    _logger.info(*args, **kwargs)


def debug(*args, **kwargs):
    _logger.debug(*args, **kwargs)
