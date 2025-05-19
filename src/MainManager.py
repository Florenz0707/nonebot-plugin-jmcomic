import os
import shutil
import asyncio
import jmcomic

from enum import Enum
from pathlib import Path
from nonebot.log import logger

from .Downloader import Downloader
from .Client import Client
from .Database import Database
from .Filter import FirstImageFilter
from .utils import *
from .PathRelocator import PathRelocator


class Status(Enum):
    GOOD = 1
    BAD = 2
    RUDE = 3
    NOTFOUND = 4
    RESTRICT = 5
    BUSY = 6
    CACHED = 7
    UPLOADING = 8
    DOWNLOADING = 9


class FileType(Enum):
    PDF = 0
    JPG = 1


PathRelocator.load()


class MainManager:
    base_dir: Path = PathRelocator.getBaseDir()
    conf_dir: Path = Path.joinpath(base_dir, "config")
    data_dir: Path = Path.joinpath(base_dir, "data")
    album_cache_dir: Path = Path.joinpath(data_dir, "album_cache")
    save_cache_dir: Path = Path.joinpath(data_dir, "save_cache")
    database_dir: Path = Path.joinpath(data_dir, "database")
    pdf_dir: Path = Path.joinpath(save_cache_dir, "pdf")
    pics_dir: Path = Path.joinpath(save_cache_dir, "pics")

    def __init__(self):
        self.pdf_cache_limit = 10 * 1024  # GB to MB
        self.pic_cache_limit = 1 * 1024
        self.download_queue = []
        self.upload_queue = []
        self.image_queue = []
        self.queue_limit = 5
        self.downloader = Downloader(self.conf_dir)
        self.client = Client(self.conf_dir)
        self.firstImageDownloader = jmcomic.create_option_by_file(
            os.path.join(str(self.conf_dir), "firstImage_options.yml")
        )
        self.database = Database(self.database_dir)

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
        while cur_size > self.getCacheMaxSize(file_type):
            file_path = file_list[0]
            cur_size -= Byte2MB(file_path.stat().st_size)
            os.remove(file_path)
            logger.warning(f"Clean cache file: {file_path}")
            file_list = file_list[1:]

    def isFileCached(self, album_id: str, file_type: FileType) -> bool:
        return self.getFilePath(album_id, file_type).exists()

    def cleanPics(self):
        if len(self.download_queue) == 0 and len(self.image_queue) == 0:
            shutil.rmtree(self.album_cache_dir)

    def isValidAlbumId(self, album_id: str) -> bool:
        return self.client.isValidAlbumId(album_id)

    def switchProxy(self) -> None:
        self.client.switchProxy()

    def getProxy(self) -> bool:
        return self.client.getProxy()

    def add2queue(self, album_id: str, force: bool = False) -> Status:
        info: dict = self.database.getAlbumInfo(album_id)
        if info is None:
            return Status.RUDE
        if not force and self.getRestrictedInfo(album_id) is not None:
            return Status.RESTRICT
        if self.isFileCached(album_id, FileType.PDF):
            return Status.CACHED
        if self.isDownloading(album_id):
            return Status.DOWNLOADING
        if len(self.download_queue) >= self.queue_limit:
            return Status.BUSY
        if self.isUploading(album_id):
            return Status.UPLOADING
        if not self.isValidAlbumId(album_id):
            return Status.NOTFOUND

        self.download_queue.append(album_id)
        return Status.GOOD

    async def download(self, album_id: str) -> None:
        await asyncio.to_thread(self.downloader.download, album_id)
        self.database.setAlbumSize(album_id, self.getFileSize(album_id, FileType.PDF))
        self.download_queue.remove(album_id)
        self.cleanCache(FileType.PDF)

    def isDownloading(self, album_id: str) -> bool:
        return album_id in self.download_queue

    def downloadDone(self, album_id: str) -> None:
        if self.isDownloading(album_id):
            self.download_queue.remove(album_id)

    def getDownloadQueue(self) -> list:
        return self.download_queue

    def clearDownloadQueue(self) -> None:
        self.download_queue.clear()

    def isUploading(self, album_id: str) -> bool:
        return album_id in self.upload_queue

    def upload(self, album_id: str) -> None:
        if not self.isUploading(album_id):
            self.upload_queue.append(album_id)

    def uploadDone(self, album_id: str) -> None:
        if self.isUploading(album_id):
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

    def getRestrictedInfo(self, album_id: str) -> str | None:
        info = self.database.getAlbumInfo(album_id)
        if (tag := self.database.isTagsRestricted(info.get('tags'))) is not None:
            return tag
        if self.database.isAlbumIdRestricted(album_id):
            return album_id
        return None

    def increaseUserFreq(self, user_id: str, date: str) -> None:
        self.database.increaseUserFreq(user_id, date)

    def getUserFreq(self, user_id: str, date: str) -> int:
        return self.database.getUserFreq(user_id, date)

    def getAllFreq(self, date: str) -> list:
        return self.database.getAllFreq(date)

    def getMostFreq(self, date: str) -> tuple:
        return self.database.getMostFreq(date)

    def setUserLimit(self, user_id: str, limit: int) -> None:
        self.database.setUserLimit(user_id, limit)

    def getUserLimit(self, user_id: str) -> None | int:
        return self.database.getUserLimit(user_id)

    def getAllLimit(self) -> list:
        return self.database.getAllLimit()

    def deleteUserLimit(self, user_id: str) -> None:
        self.database.deleteUserLimit(user_id)

    def increaseUserXPByTags(self, user_id: str, tags: str) -> None:
        tag_list = splitTags(tags)
        for tag in tag_list:
            self.database.increaseUserXP(user_id, tag)

    def increaseUserXPByAlbumID(self, user_id: str, album_id: str) -> None:
        info = self.database.getAlbumInfo(album_id)
        if info is None:
            return
        self.increaseUserXPByTags(user_id, info.get('tags'))

    def getUserXP(self, user_id: str, length: int) -> None | list:
        ret = self.database.getUserXP(user_id)
        if len(ret) == 0:
            return None
        if len(ret) > length:
            ret = ret[:length]
        return ret

    async def getAlbumInfo(self, album_id: str, with_image=False) -> dict | None:
        info = self.database.getAlbumInfo(album_id)
        if info is None:
            if not self.isValidAlbumId(album_id):
                return None
            info = self.client.getAlbumInfo(album_id)
            self.database.insertAlbumInfo(info)

        if with_image and not self.isFileCached(album_id, FileType.JPG):
            self.image_queue.append(album_id)
            jmcomic.JmModuleConfig.CLASS_DOWNLOADER = FirstImageFilter
            self.firstImageDownloader.download_photo(album_id)
            jmcomic.JmModuleConfig.CLASS_DOWNLOADER = None

            target = None
            album_dir = os.path.join(self.album_cache_dir, album_id)
            for file in os.listdir(album_dir):
                target = os.path.join(album_dir, file)
                break

            if target is None:
                return
            shutil.move(target, str(self.getFilePath(album_id, FileType.JPG)))
            self.image_queue.remove(album_id)
            self.cleanPics()
            self.cleanCache(FileType.JPG)

        return info


mm = MainManager()
