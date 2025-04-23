import jmcomic
from pathlib import Path
from nonebot.log import logger

from .utils import *


class Client:
    def __init__(self, conf_dir: Path):
        self.noProxyClient = jmcomic.JmOption.default().new_jm_client()
        self.proxyClient = jmcomic.create_option_by_file(
            str(Path.joinpath(conf_dir, "proxyClient.yml"))
        ).new_jm_client()
        self.proxy = False
        self.client = self.noProxyClient

    def switchProxy(self) -> None:
        self.proxy = not self.proxy
        self.client = self.proxyClient if self.proxy else self.noProxyClient

    def getProxy(self) -> bool:
        return self.proxy

    def isValidAlbumId(self, album_id: str) -> bool:
        try:
            self.client.get_album_detail(album_id)
        except jmcomic.JmcomicException as error:
            if "ip地区禁止访问/爬虫被识别" in str(error):
                raise error
            return False
        else:
            return True

    def getAlbumInfo(self, album_id: str) -> dict:
        try:
            album_detail = self.client.get_album_detail(album_id)
        except jmcomic.JmcomicException as error:
            raise error
        else:
            tags = ""
            for tag in album_detail.tags:
                tag = tag.strip()
                if tag != "":
                    tags += f"#{tag} "
            return getDict((album_detail.album_id, album_detail.title, album_detail.author,
                            tags, album_detail.page_count, 0.0))
