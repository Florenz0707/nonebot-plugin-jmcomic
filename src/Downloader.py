import jmcomic

from nonebot.log import logger
from pathlib import Path

from .utils import *


class Downloader:
    def __init__(self, conf_path: Path, client: jmcomic.JmcomicClient):
        self.option = jmcomic.create_option_by_file(
            str(Path.joinpath(conf_path, "default_options.yml"))
        )
        self.client = client

    def download(self, album_id: str) -> None:
        try:
            self.option.download_album(album_id)
        except jmcomic.RequestRetryAllFailException as e:
            logger.warning(e)
        except jmcomic.JmcomicException as e:
            raise e
        else:
            pass

    def query(self, album_id: str) -> dict:
        album_detail = self.client.get_album_detail(album_id)
        tags = ""
        for tag in album_detail.tags:
            tags += f"#{tag} "
        package = (album_detail.album_id, album_detail.title, album_detail.author, tags, 0)
        return getDict(package)
