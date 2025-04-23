import sqlite3
import sqlite3 as sq

from nonebot.log import logger
from pathlib import Path
from .utils import *


class Database:
    def __init__(self, database_dir: Path):
        """
        create connection with jmcomic.db on database_dir.
        table structure:
            album_info: album_id, title, author, tags, size
            restriction: type, info
            user_freq: user_id, date, use_cnt
            user_limit: user_id, daily_limit
        """
        self.base_dir: Path = database_dir
        self.file_path: Path = Path.joinpath(self.base_dir, "jmcomic.db")
        self.database = sq.connect(self.file_path)
        self.cursor = self.database.cursor()
        try:
            command = """
            create table if not exists album_info (
                album_id    text,
                title       text,
                author      text,
                tags        text,
                page        int     default 0,
                size        float   default 0.0,
                primary key (album_id)
            );
            """
            self.cursor.execute(command)
            self.database.commit()
        except sqlite3.Error as error:
            logger.error(f"Error occurs when create table album_info: {error}")

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

        try:
            command = """
            create table if not exists user_freq (
                user_id     text,
                date        text,
                use_cnt     int     default 0,
                primary key (user_id, date)
            )
            """
            self.cursor.execute(command)
            self.database.commit()
        except sqlite3.Error as error:
            logger.warning(f"Error occurs when create table user_freq: {error}")

        try:
            command = """
            create table if not exists user_limit (
                user_id     text,
                daily_limit int,
                primary key (user_id)
            )
            """
            self.cursor.execute(command)
            self.database.commit()
        except sqlite3.Error as error:
            logger.warning(f"Error occurs when create table user_limit: {error}")

    def __del__(self):
        self.cursor.close()
        self.database.close()

    def insertAlbumInfo(self, info: dict) -> None:
        """
        insert info into table album_info,
        as there must be query in front of download,
        default size as 0.0
        """
        self.cursor.execute(
            "insert into album_info(album_id, title, author, tags, page) values (?, ?, ?, ?, ?)",
            (info.get("album_id"), info.get("title"), info.get("author"),
             info.get("tags"), info.get("page"))
        )
        self.database.commit()

    def getAlbumInfo(self, album_id: str) -> None | dict:
        self.cursor.execute(
            "select album_id, title, author, tags, page, size from album_info where album_id = ?",
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
        """
        if album_id is restricted, return album_id;
        otherwise return None
        """
        self.cursor.execute(
            "select * from restriction where type = ? and info = ?",
            ("album_id", album_id)
        )
        return None if self.cursor.fetchone() is None else album_id

    def isTagsRestricted(self, tags: str) -> str | None:
        """
        if one of the tags is restricted, return the tag;
        otherwise return None
        """
        tags: list = splitTags(tags)
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
        """
        insert restriction,
        if success, return None;
        otherwise return error information
        """
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
        """
        delete restriction,
        if success, return None;
        otherwise return error information
        """
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

    def getRestriction(self) -> tuple[list, list]:
        """
        return (tag_list, album_id_list)
        """
        self.cursor.execute("select type, info from restriction where type = 'tag' order by info")
        tag_list = self.cursor.fetchall()
        self.cursor.execute("select type, info from restriction where type = 'album_id' order by info")
        album_id_list = self.cursor.fetchall()
        return tag_list, album_id_list

    def increaseUserFreq(self, user_id: str, date: str) -> None:
        self.cursor.execute(
            "select use_cnt from user_freq where user_id = ? and date = ?",
            (user_id, date)
        )
        if self.cursor.fetchone() is None:
            self.cursor.execute(
                "insert into user_freq(user_id, date, use_cnt) values (?, ?, ?)",
                (user_id, date, 0)
            )
            self.database.commit()

        self.cursor.execute(
            "update user_freq set use_cnt = use_cnt + 1 where user_id = ? and date = ?",
            (user_id, date)
        )
        self.database.commit()

    def getUserFreq(self, user_id: str, date: str) -> int:
        self.cursor.execute(
            "select use_cnt from user_freq where user_id = ? and date = ?",
            (user_id, date)
        )
        ret = self.cursor.fetchone()
        if ret is None:
            return 0
        else:
            return ret[0]

    def getAllFreq(self, date: str) -> list:
        self.cursor.execute(
            "select user_id, use_cnt from user_freq where date = ? order by use_cnt desc",
            (date,)
        )
        return self.cursor.fetchall()

    def getMostFreq(self, date: str) -> None | tuple:
        if (info := self.getAllFreq(date)) is None:
            return None
        return info[0]

    def setUserLimit(self, user_id: str, limit: int) -> None:
        self.cursor.execute(
            "select daily_limit from user_limit where user_id = ?",
            (user_id,)
        )
        if self.cursor.fetchone() is None:
            self.cursor.execute(
                "insert into user_limit(user_id, daily_limit) values (?, ?)",
                (user_id, limit)
            )
        else:
            self.cursor.execute(
                "update user_limit set daily_limit = ? where user_id = ?",
                (limit, user_id)
            )
        self.database.commit()

    def getUserLimit(self, user_id: str) -> None | int:
        self.cursor.execute(
            "select daily_limit from user_limit where user_id = ?",
            (user_id,)
        )
        ret = self.cursor.fetchone()
        return None if ret is None else ret[0]

    def getAllLimit(self) -> list:
        self.cursor.execute(
            "select user_id, daily_limit from user_limit"
        )
        return self.cursor.fetchall()

    def deleteUserLimit(self, user_id: str) -> None:
        self.cursor.execute(
            "delete from user_limit where user_id = ?",
            (user_id,)
        )
        self.database.commit()
