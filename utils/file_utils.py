# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: file_utilsユーティリティ
"""ファイルI/Oユーティリティ"""

import os
import stat
import tempfile


def atomic_write_text(file_path, write_func, encoding='utf-8', newline=None):
    """テキストファイルを同一ディレクトリの一時ファイル経由で原子的に書き込む。

    書き込み中に失敗した場合でも既存ファイルの内容は保持される。
    一時ファイルは失敗時に削除される。

    Args:
        file_path (str): 書き込み先ファイルパス
        write_func (callable): 開かれたファイルオブジェクトを受け取り書き込みを行う関数
        encoding (str): ファイルのエンコーディング（既定: utf-8）
        newline (str|None): open() に渡す newline 引数（CSVでは '' を指定）

    Raises:
        Exception: 書き込みまたは置換に失敗した場合（元ファイルは保持される）
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=os.path.basename(file_path) + '.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding=encoding, newline=newline) as f:
            write_func(f)
            f.flush()
            os.fsync(f.fileno())
        try:
            # 既存ファイルがあればパーミッションを引き継ぐ
            os.chmod(tmp_path, stat.S_IMODE(os.stat(file_path).st_mode))
        except OSError:
            pass
        os.replace(tmp_path, file_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
