class Restriction:
    def __init__(self):
        self.default_restrict_tags = ("獵奇", "重口", "YAOI", "yaoi", "男同", "血腥", "猎奇", "虐杀", "恋尸癖")
        self.default_restrict_album_id = ("136494", "323666", "350234", "363848", "405848",
                                          "454278", "481481", "559716", "611650", "629252",
                                          "69658", "626487", "400002", "208092", "253199",
                                          "382596", "418600", "279464", "565616", "222458")

    def isTagRestricted(self, tags: str) -> bool:
        tags = tags.split(sep="#")
        for tag in tags:
            tag = tag.strip()
            if tag in self.default_restrict_tags:
                return True

        return False

    def isAlbumIdRestricted(self, album_id: str) -> bool:
        return album_id in self.default_restrict_album_id
