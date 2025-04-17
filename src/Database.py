import sqlite3
import sqlite3 as sq

from nonebot.log import logger
from pathlib import Path
from .utils import *


class Database:
    def __init__(self, database_dir: Path):
        self.base_dir: Path = database_dir
        self.file_path: Path = Path.joinpath(self.base_dir, "jmcomic.db")
        self.database = sq.connect(self.file_path)
        self.cursor = self.database.cursor()
        try:
            command = """
            create table if not exists album_info (
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
            logger.error(f"Error occurs when create table album_info: {error}")
        else:
            pass

        try:
            command = """
            create table if not exists restriction (
                type    text,
                info    text,
                primary key (type, info),
                constraint CHK_TYPE check (type = 'tag' or type = 'album_id')
            );
            """
            self.cursor.execute(command)
            self.database.commit()
        except sqlite3.Error as error:
            logger.warning(f"Error occurs when create table restriction: {error}")
        else:
            pass

    def __del__(self):
        self.cursor.close()
        self.database.close()

    def insertAlbumInfo(self, info: dict) -> None:
        self.cursor.execute(
            "insert into album_info values (?, ?, ?, ?, ?)",
            (info["album_id"], info["title"], info["author"], info["tags"], 0.0)
        )
        self.database.commit()

    def queryAlbumInfo(self, album_id: str) -> None | dict:
        self.cursor.execute(
            "select album_id, title, author, tags, size from album_info where album_id = ?",
            (album_id,)
        )
        ret = self.cursor.fetchone()
        return None if ret is None else getDict(ret)

    def setAlbumSize(self, album_id: str, size: float) -> None:
        self.cursor.execute(
            "update album_info set size = ? where album_id = ?",
            (size, album_id)
        )
        self.database.commit()

    def isAlbumIdRestricted(self, album_id: str) -> str | None:
        self.cursor.execute(
            "select * from restriction where type = ? and info = ?",
            ("album_id", album_id)
        )
        return None if self.cursor.fetchone() is None else album_id

    def isTagsRestricted(self, tags: str) -> str | None:
        tags = splitTags(tags)
        self.cursor.execute(
            "select info from restriction where type = ?",
            ("tag",)
        )
        restriction = [tag[0] for tag in self.cursor.fetchall()]
        for tag in tags:
            if tag in restriction:
                return tag
        return None

    def insertRestriction(self, kind: str, info: str) -> None | str:
        try:
            self.cursor.execute(
                "insert into restriction values (?, ?)",
                (kind, info)
            )
            self.database.commit()
        except sqlite3.Error as error:
            return str(error)
        else:
            return None

    def deleteRestriction(self, kind: str, info: str) -> None | str:
        try:
            self.cursor.execute(
                "delete from restriction where type = ? and info = ?",
                (kind, info)
            )
            self.database.commit()
        except sqlite3.Error as error:
            return str(error)
        else:
            return None

    def getRestriction(self) -> list:
        self.cursor.execute(
            "select type, info from restriction order by type"
        )
        return self.cursor.fetchall()
