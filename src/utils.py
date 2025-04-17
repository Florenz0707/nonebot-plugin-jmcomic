from nonebot.log import logger


def Byte2MB(size: int) -> float:
    return size / 1024 / 1024


def getDict(info: tuple) -> dict:
    keys = ("album_id", "title", "author", "tags", "size")
    ret = {key: val for key, val in zip(keys, info)}
    return ret


def splitTags(tags: str) -> list:
    tags = tags.split(sep="#")
    ret = [tag.strip() for tag in tags]
    return ret
