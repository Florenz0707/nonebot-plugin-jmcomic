import os
import shutil

from enum import Enum

from .Downloader import *
from .Database import *
from .Filter import *
from .utils import *


class Status(Enum):
    GOOD = 0
    CACHED = 1
    BUSY = 2
    NOTFOUND = 3
    REPEAT = 4
    BAD = 5


class MainManager:
    base_dir: Path = Path(r"D:\NoneBot\Rift\nonebot_plugin_jmcomic")
    conf_dir: Path = Path.joinpath(base_dir, "config")
    downloads_dir: Path = Path.joinpath(base_dir, "downloads")
    cache_dir: Path = Path.joinpath(downloads_dir, "cache")
    pdf_dir: Path = Path.joinpath(cache_dir, "pdf")
    database_dir: Path = Path.joinpath(cache_dir, "database")
    pics_dir: Path = Path.joinpath(cache_dir, "pics")

    def __init__(self):
        self.pdf_cache_limit = 5 * 1024  # GB to MB
        self.pic_cache_limit = 1 * 1024
        self.client = jmcomic.JmOption.default().new_jm_client()
        self.download_queue = []
        self.queue_limit = 5
        self.downloader = Downloader(self.conf_dir, self.client)
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
        if file_path.exists():
            return Byte2MB(file_path.stat().st_size)
        return 0

    def getCacheList(self, suffix: str) -> list:
        return os.listdir(self.getPathBySuffix(suffix)[0])

    def getCacheCnt(self, suffix: str) -> int:
        return len(self.getCacheList(suffix))

    def getCacheSize(self, suffix: str) -> float:
        ret = 0
        for file in self.getCacheList(suffix):
            ret += Path.joinpath(self.getPathBySuffix(suffix)[0], file).stat().st_size
        return Byte2MB(ret)

    def isCacheFull(self, suffix: str):
        return self.getCacheSize(suffix) > self.getPathBySuffix(suffix)[1]

    def cleanCache(self, suffix: str):
        file_list = sorted(self.getCacheList(suffix), key=lambda x: os.path.getctime(x))
        cur_size = self.getCacheSize(suffix)
        index = 0
        while cur_size > self.getPathBySuffix(suffix)[1]:
            file_path = Path.joinpath(self.getPathBySuffix(suffix)[0], file_list[index])
            cur_size -= Byte2MB(file_path.stat().st_size)
            os.remove(file_path)
            file_list = file_list[1:]
            index += 1

    def isFileCached(self, album_id: str, suffix: str) -> bool:
        return self.getFilePath(album_id, suffix).exists()

    def cleanPics(self):
        for target in os.listdir(self.downloads_dir):
            if target != "cache":
                shutil.rmtree(os.path.join(self.downloads_dir, target))

    def isValidAlbumId(self, album_id: str) -> bool:
        try:
            self.client.get_album_detail(album_id)
        except jmcomic.MissingAlbumPhotoException:
            return False
        else:
            return True

    def add2queue(self, album_id: str) -> Status:
        if self.isFileCached(album_id, "pdf"):
            return Status.CACHED
        if album_id in self.download_queue:
            return Status.REPEAT
        if len(self.download_queue) >= self.queue_limit:
            return Status.BUSY
        if not self.isValidAlbumId(album_id):
            return Status.NOTFOUND

        self.download_queue.append(album_id)
        return Status.GOOD

    def download(self) -> None:
        while len(self.download_queue) > 0:
            album_id = self.download_queue[0]
            self.downloader.download(album_id)
            self.download_queue = self.download_queue[1:]
            if self.database.query(album_id) is None:
                info = self.downloader.query(album_id)
                info[4] = self.getFileSize(album_id, "pdf")
                self.database.insert(info)
            else:
                self.database.update(album_id, self.getFileSize(album_id, "pdf"))

        self.cleanPics()
        if self.isCacheFull("pdf"):
            self.cleanCache("pdf")

    def query(self, album_id: str, with_image=False) -> list | None:
        info = self.database.query(album_id)
        if info is None:
            if not self.isValidAlbumId(album_id):
                return None
            info = self.downloader.query(album_id)
            self.database.insert(info)

        if with_image:
            if not self.isFileCached(album_id, "jpg"):
                jmcomic.JmModuleConfig.CLASS_DOWNLOADER = FirstImageFilter
                self.firstImageDownloader.download_photo(album_id)
                jmcomic.JmModuleConfig.CLASS_DOWNLOADER = None

                shutil.move(str(Path.joinpath(self.downloads_dir, "00001.jpg")),
                            str(self.getFilePath(album_id, "jpg")))
                if self.isCacheFull("jpg"):
                    self.cleanCache("jpg")

        return info


mm = MainManager()
