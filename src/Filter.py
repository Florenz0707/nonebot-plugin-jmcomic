import jmcomic


class FirstImageFilter(jmcomic.JmDownloader):
    def do_filter(self, detail: jmcomic.DetailEntity):
        if detail.is_photo():
            photo: jmcomic.JmPhotoDetail = detail
            return photo[:1]
        elif detail.is_album():
            album: jmcomic.JmAlbumDetail = detail
            return album[:1]
        return detail


default_filter = None
