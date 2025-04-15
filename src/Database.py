import sqlite3
import sqlite3 as sq

from nonebot.log import logger
from pathlib import Path
from .utils import *


class Database:
    def __init__(self, database_dir: Path):
        self.base_dir: Path = database_dir
        self.file_path: Path = Path.joinpath(self.base_dir, "records.db")
        self.database = sq.connect(self.file_path)
        self.cursor = self.database.cursor()
        try:
            command = """
            create table if not exists jmcomic (
                album_id    text    not null,
                title       text,
                author      text,
                tags        text,
                size        float   default 0.0,
                primary key (album_id)
            );
            """
            self.cursor.execute(command)
            self.database.commit()
        except sqlite3.Error as error:
            logger.error(f"Error occurs when create table jmcomic: {error}")

    def __del__(self):
        self.cursor.close()
        self.database.close()

    def insert(self, info: dict):
        self.cursor.execute(
            "insert into jmcomic values (?, ?, ?, ?, ?)",
            (info["album_id"], info["title"], info["author"], info["tags"], info["size"])
        )
        self.database.commit()

    def query(self, album_id: str) -> None | dict:
        self.cursor.execute(
            "select * from jmcomic where album_id = ?",
            (album_id,)
        )
        ret = self.cursor.fetchone()
        return None if ret is None else getDict(ret)

    def update_size(self, album_id: str, size: float) -> None:
        self.cursor.execute(
            "update jmcomic set size = ? where album_id = ?",
            (size, album_id)
        )
        self.database.commit()
