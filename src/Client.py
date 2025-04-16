import jmcomic

from .utils import *


class Client:
    def __init__(self):
        self.client = jmcomic.JmOption.default().new_jm_client()

    def isValidAlbumId(self, album_id: str) -> bool:
        try:
            self.client.get_album_detail(album_id)
        except jmcomic.JmcomicException:
            return False
        else:
            return True

    def getAlbumInfo(self, album_id: str) -> dict:
        album_detail = self.client.get_album_detail(album_id)
        tags = ""
        for tag in album_detail.tags:
            tag = tag.strip()
            if tag != "":
                tags += f"#{tag} "
        return getDict((album_detail.album_id, album_detail.title, album_detail.author, tags, 0.0))
