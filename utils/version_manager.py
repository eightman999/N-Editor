# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: バージョン管理ユーティリティ
import os
import logging

logger = logging.getLogger(__name__)

VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.txt")

def increment_build_number():
    """version.txtのビルド番号を1増やす"""
    version = "0.0.0.00"
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                version = f.read().strip()
        parts = version.split('.')
        if parts and parts[-1].isdigit():
            width = len(parts[-1])
            parts[-1] = str(int(parts[-1]) + 1).zfill(width)
            new_version = '.'.join(parts)
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(new_version)
            logger.info(f"Incremented build number: {version} -> {new_version}")
            return new_version
    except Exception as e:
        logger.warning(f"Failed to increment build number: {e}")
    return version
