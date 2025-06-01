from datetime import datetime


def Byte2MB(size: int) -> float:
    return size / 1024 / 1024


def getDict(info: tuple) -> dict:
    keys = ("album_id", "title", "author", "tags", "page", "size", "query_cnt", "dl_cnt")
    ret = {key: val for key, val in zip(keys, info)}
    return ret


def splitTags(tags: str) -> list:
    ret = []
    for tag in tags.split(sep="#"):
        tag = tag.strip()
        if tag != "":
            ret.append(tag)
    return ret


def currentDate() -> str:
    return str(datetime.now().date())


def date2words(date: str) -> str:
    date = date.split(sep="-")
    year = date[0]
    month = date[1]
    day = date[2]
    if len(month) > 1 and month[0] == '0':
        month = month[1]
    if len(day) > 1 and day[0] == '0':
        day = day[1]
    return f"{year}年{month}月{day}日"


def AlbumIdStrip(album_id: str):
    return album_id.lstrip('0')


if __name__ == "__main__":
    print(date2words(currentDate()))
