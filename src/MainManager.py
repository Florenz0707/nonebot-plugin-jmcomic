import os
import shutil
import jmcomic

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
            str(Path.joinpath(self.conf_dir, "firstImage_options.yml"))
        )
        self.database = Database(self.database_dir)

    def getPathBySuffix(self, suffix: str) -> tuple:
        if suffix == "jpg":
            return self.pics_dir, self.pic_cache_limit
        else:
            return self.pdf_dir, self.pdf_cache_limit

    def getFilePath(self, album_id: str, suffix: str) -> Path:
        return Path.joinpath(self.getPathBySuffix(suffix)[0], f"{album_id}.{suffix}")

    def getFileSize(self, album_id: str, suffix: str) -> float:
        file_path: Path = self.getFilePath(album_id, suffix)
        return Byte2MB(file_path.stat().st_size) if file_path.exists() else 0

    def getCacheList(self, suffix: str) -> list:
        ret = os.listdir(self.getPathBySuffix(suffix)[0])
        for i in range(len(ret)):
            ret[i] = Path.joinpath(self.getPathBySuffix(suffix)[0], ret[i])
        return ret

    def getCacheCnt(self, suffix: str) -> int:
        return len(self.getCacheList(suffix))

    def getCacheSize(self, suffix: str) -> float:
        ret = 0
        for file in self.getCacheList(suffix):
            ret += file.stat().st_size
        return Byte2MB(ret)

    def isCacheFull(self, suffix: str):
        return self.getCacheSize(suffix) > self.getPathBySuffix(suffix)[1]

    def cleanCache(self, suffix: str):
        file_list = sorted(self.getCacheList(suffix), key=lambda x: os.path.getctime(str(x)))
        cur_size = self.getCacheSize(suffix)
        index = 0
        while cur_size > self.getPathBySuffix(suffix)[1]:
            file_path = file_list[index]
            cur_size -= Byte2MB(file_path.stat().st_size)
            os.remove(file_path)
            logger.warning(f"Clean cache file:{file_path}")
            file_list = file_list[1:]
            index += 1

    def isFileCached(self, album_id: str, suffix: str) -> bool:
        return self.getFilePath(album_id, suffix).exists()

    def cleanPics(self):
        for target in os.listdir(self.downloads_dir):
            if target != "cache":
                shutil.rmtree(os.path.join(self.downloads_dir, target))

    def isValidAlbumId(self, album_id: str) -> bool:
        return self.client.isValidAlbumId(album_id)

    def add2queue(self, album_id: str) -> Status:
        if self.isFileCached(album_id, "pdf"):
            return Status.CACHED
        if album_id in self.download_queue:
            return Status.REPEAT
        if len(self.download_queue) >= self.queue_limit:
            return Status.BUSY
        if self.database.query(album_id) is None:
            return Status.RUDE
        if not self.isValidAlbumId(album_id):
            return Status.NOTFOUND

        self.download_queue.append(album_id)
        return Status.GOOD

    def download(self) -> None:
        while len(self.download_queue) > 0:
            album_id = self.download_queue[0]
            self.download_queue = self.download_queue[1:]
            self.downloader.download(album_id)
            if self.database.query(album_id) is None:
                info = self.client.getAlbumInfo(album_id)
                info["size"] = self.getFileSize(album_id, "pdf")
                self.database.insert(info)
            else:
                self.database.update_size(album_id, self.getFileSize(album_id, "pdf"))

        self.cleanPics()
        if self.isCacheFull("pdf"):
            self.cleanCache("pdf")

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

    def query(self, album_id: str, with_image=False) -> dict | None:
        info = self.database.query(album_id)
        if info is None:
            if not self.isValidAlbumId(album_id):
                return None
            info = self.client.getAlbumInfo(album_id)
            self.database.insert(info)

        if with_image and not self.isFileCached(album_id, "jpg"):
            jmcomic.JmModuleConfig.CLASS_DOWNLOADER = FirstImageFilter
            self.firstImageDownloader.download_photo(album_id)
            jmcomic.JmModuleConfig.CLASS_DOWNLOADER = None

            shutil.move(str(Path.joinpath(self.downloads_dir, "00001.jpg")),
                        str(self.getFilePath(album_id, "jpg")))
            if self.isCacheFull("jpg"):
                self.cleanCache("jpg")

        return info


mm = MainManager()
