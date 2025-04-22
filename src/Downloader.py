import jmcomic

from nonebot.log import logger
from pathlib import Path


class Downloader:
    def __init__(self, conf_path: Path):
        self.option = jmcomic.create_option_by_file(
            str(Path.joinpath(conf_path, "default_options.yml"))
        )

    def download(self, album_id: str) -> None:
        try:
            self.option.download_album(album_id)
        except jmcomic.RequestRetryAllFailException:
            pass
        except jmcomic.JmcomicException as error:
            raise error
        else:
            pass
