import threading
import os
import shutil
import jmcomic
import asyncio

from enum import Enum
from pathlib import Path
from nonebot.log import logger

from .Downloader import Downloader
from .Client import Client
from .Database import Database
from .Filter import FirstImageFilter
from .utils import *


class Status(Enum):
    GOOD = 0
    CACHED = 1
    BUSY = 2
    NOTFOUND = 3
    REPEAT = 4
    BAD = 5
    RUDE = 6
    RESTRICT = 7


class FileType(Enum):
    PDF = 0
    JPG = 1


class MainManager:
    base_dir: Path = Path(r"D:\NoneBot\Rift\nonebot_plugin_jmcomic")
    conf_dir: Path = Path.joinpath(base_dir, "config")
    downloads_dir: Path = Path.joinpath(base_dir, "downloads")
    cache_dir: Path = Path.joinpath(downloads_dir, "cache")
    pdf_dir: Path = Path.joinpath(cache_dir, "pdf")
    database_dir: Path = Path.joinpath(cache_dir, "database")
    pics_dir: Path = Path.joinpath(cache_dir, "pics")

    def __init__(self):
        self.pdf_cache_limit = 10 * 1024  # GB to MB
        self.pic_cache_limit = 1 * 1024
        self.client = Client()
        self.download_queue = []
        self.upload_queue = []
        self.queue_limit = 5
        self.downloader = Downloader(self.conf_dir)
        self.firstImageDownloader = jmcomic.create_option_by_file(
            os.path.join(str(self.conf_dir), "firstImage_options.yml"))
        self.database = Database(self.database_dir)
        self.lock = threading.Lock()

    def getPathDir(self, file_type: FileType) -> Path:
        return self.pics_dir if file_type == FileType.JPG else self.pdf_dir

    def getCacheMaxSize(self, file_type: FileType) -> int:
        return self.pic_cache_limit if file_type == FileType.JPG else self.pdf_cache_limit

    def getFilePath(self, album_id: str, file_type: FileType) -> Path:
        suffix = "jpg" if file_type == FileType.JPG else "pdf"
        return Path.joinpath(self.getPathDir(file_type), f"{album_id}.{suffix}")

    def getFileSize(self, album_id: str, file_type: FileType) -> float:
        file_path: Path = self.getFilePath(album_id, file_type)
        return Byte2MB(file_path.stat().st_size) if file_path.exists() else 0

    def getCacheList(self, file_type: FileType) -> list[Path]:
        ret = [Path.joinpath(self.getPathDir(file_type), path) for path in os.listdir(self.getPathDir(file_type))]
        return ret

    def getCacheCnt(self, file_type: FileType) -> int:
        return len(self.getCacheList(file_type))

    def getCacheSize(self, file_type: FileType) -> float:
        ret = 0
        for file in self.getCacheList(file_type):
            ret += file.stat().st_size
        return Byte2MB(ret)

    def isCacheFull(self, file_type: FileType):
        return self.getCacheSize(file_type) > self.getCacheMaxSize(file_type)

    def cleanCache(self, file_type: FileType):
        if not self.isCacheFull(file_type):
            return
        file_list = sorted(self.getCacheList(file_type), key=lambda x: os.path.getctime(str(x)))
        cur_size = self.getCacheSize(file_type)
        index = 0
        while cur_size > self.getCacheMaxSize(file_type):
            file_path = file_list[index]
            cur_size -= Byte2MB(file_path.stat().st_size)
            os.remove(file_path)
            logger.warning(f"Clean cache file:{file_path}")
            file_list = file_list[1:]
            index += 1

    def isFileCached(self, album_id: str, file_type: FileType) -> bool:
        return self.getFilePath(album_id, file_type).exists()

    def cleanPics(self):
        for target in os.listdir(self.downloads_dir):
            if target != "cache":
                shutil.rmtree(os.path.join(self.downloads_dir, target))

    def isValidAlbumId(self, album_id: str) -> bool:
        return self.client.isValidAlbumId(album_id)

    def add2queue(self, album_id: str) -> Status:
        info: dict = self.database.queryAlbumInfo(album_id)
        if info is None:
            return Status.RUDE
        restriction = self.database.isAlbumIdRestricted(album_id)
        if restriction is None:
            restriction = self.database.isTagsRestricted(info.get("tags"))
        if restriction is not None:
            logger.warning(f"Trigger restriction: {restriction}")
            return Status.RESTRICT
        if album_id in self.download_queue:
            return Status.REPEAT
        if len(self.download_queue) >= self.queue_limit:
            return Status.BUSY
        if self.isFileCached(album_id, FileType.PDF):
            return Status.CACHED
        if not self.isValidAlbumId(album_id):
            return Status.NOTFOUND

        self.download_queue.append(album_id)
        return Status.GOOD

    async def download(self) -> None:
        while len(self.download_queue) > 0:
            album_id = self.download_queue[0]
            self.download_queue.remove(album_id)
            self.downloader.download(album_id)
            self.database.setAlbumSize(album_id, self.getFileSize(album_id, FileType.PDF))

        self.cleanPics()
        self.cleanCache(FileType.PDF)

    def getDownloadQueue(self) -> list:
        return self.download_queue

    def clearDownloadQueue(self) -> None:
        self.download_queue.clear()

    def upload(self, album_id: str) -> bool:
        if album_id in self.upload_queue:
            return False
        self.upload_queue.append(album_id)
        return True

    def uploadDone(self, album_id: str) -> None:
        self.upload_queue.remove(album_id)

    def clearUploadQueue(self) -> None:
        self.upload_queue.clear()

    def getUploadQueue(self) -> list:
        return self.upload_queue

    def insertRestriction(self, kind: str, info: str) -> None | str:
        return self.database.insertRestriction(kind, info)

    def deleteRestriction(self, kind: str, info: str) -> None | str:
        return self.database.deleteRestriction(kind, info)

    def getRestriction(self) -> tuple[list, list]:
        return self.database.getRestriction()

    async def query(self, album_id: str, with_image=False) -> dict | None:
        info = self.database.queryAlbumInfo(album_id)
        if info is None:
            if not self.isValidAlbumId(album_id):
                return None
            info = self.client.getAlbumInfo(album_id)
            self.database.insertAlbumInfo(info)

        if with_image and not self.isFileCached(album_id, FileType.JPG):
            jmcomic.JmModuleConfig.CLASS_DOWNLOADER = FirstImageFilter
            self.firstImageDownloader.download_photo(album_id)
            jmcomic.JmModuleConfig.CLASS_DOWNLOADER = None

            shutil.move(str(Path.joinpath(self.downloads_dir, "00001.jpg")),
                        str(self.getFilePath(album_id, FileType.JPG)))
            self.cleanCache(FileType.JPG)

        return info


mm = MainManager()
