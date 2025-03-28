import jmcomic


class FirstImageFilter(jmcomic.JmDownloader):
    def do_filter(self, detail: jmcomic.DetailEntity):
        if detail.is_photo():
            photo: jmcomic.JmPhotoDetail = detail
            return photo[0:1]
        return detail


default_filter = None
