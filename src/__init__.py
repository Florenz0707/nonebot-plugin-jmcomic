# ------------------------ import ------------------------
# import packages from python
from random import *
from .MainManager import *

# import packages from nonebot or other plugins
from nonebot import require, logger
from nonebot.permission import SUPERUSER

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import *

require("nonebot_plugin_uninfo")
from nonebot_plugin_uninfo import *

# ------------------------ import ------------------------

help_menu = on_alconna(
    "jm.help",
    aliases=("jm.menu",),
    use_cmd_start=True
)

download = on_alconna(
    Alconna(
        "jm",
        Args["number?", str]
    ),
    use_cmd_start=True,
)

abstract = on_alconna(
    Alconna(
        "jm.q",
        Args["number?", str],
        Args["image?", str]
    ),
    use_cmd_start=True
)

randomId = on_alconna(
    Alconna(
        "jm.r",
        Args["query?", str]
    ),
    use_cmd_start=True,
    permission=SUPERUSER
)

getStat = on_alconna(
    Alconna(
        "jm.stat",
        Args["suffix?", str]
    ),
    use_cmd_start=True,
    permission=SUPERUSER
)


@help_menu.handle()
async def help_menu_handler():
    message = """
1> jm id 下载车牌为id的本子
2> jm.q id [-i] 查询车牌为id的本子信息，使用-i参数可以附带首图
3> jm.r [-q] 随机生成可用的车牌号，使用-q参数可以直接查询"""
    await UniMessage.text(message).finish(at_sender=True)


@getStat.handle()
async def stat_handler(suffix: Match[str] = AlconnaMatch("suffix")):
    if not suffix.available:
        suffix = "pdf"
    else:
        suffix = suffix.result
        if suffix != "jpg" and suffix != "pdf":
            suffix = "pdf"
    ret = mm.getCacheSize(suffix)
    cnt = mm.getCacheCnt(suffix)
    await UniMessage.text(f"当前缓存大小为{ret:.2f} MB，"
                          f"共{cnt}个文件。").finish()


@download.handle()
async def download_handler(number: Match[str] = AlconnaMatch("number")):
    if not number.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()

    number = number.result
    status = mm.add2queue(number)
    if status == Status.BAD:
        await UniMessage.text("出现了奇怪的错误！").finish()
    if status == Status.NOTFOUND:
        await UniMessage.text(f"[{number}]找不到该编号！你再看看呢").finish()
    if status == Status.BUSY:
        await UniMessage.text("当前排队的人太多啦！过会再来吧~").finish()
    if status == Status.REPEAT:
        await UniMessage.text(f"[{number}]已存在于下载队列中！").finish()
    if status == Status.RUDE:
        await UniMessage.text(f"[{number}]没有经过查询！别下载一些奇奇怪怪的东西哦~").finish()
    if status == Status.GOOD:
        message = f"[{number}]已加入下载！"
        if (info := mm.query(number))["size"] != 0:
            message += f"(预计大小：{info['size']:.2f}MB)"
        await UniMessage.text(message).send()
        mm.download()

    if status == Status.CACHED:
        await UniMessage.text("我早有准备！拿去吧！").send()

    await UniMessage.text(f"[{number}]发送中...({(mm.getFileSize(number, 'pdf')):.2f}MB)").send()
    await UniMessage.file(path=str(mm.getFilePath(number, 'pdf'))).finish()


async def intro_sender(session: Uninfo, album_id: str, info: dict, with_image=False):
    message = f"ID：{info['album_id']}\n" \
              f"标题：{info['title']}\n" \
              f"作者：{info['author']}\n" \
              f"标签：{info['tags']}"
    if info['size'] != 0:
        message += f"\n预计大小：{info['size']:.2f}MB"

    content = UniMessage.text(message)
    if with_image:
        content += UniMessage.image(path=mm.getFilePath(album_id, "jpg"))
    node = CustomNode(uid=session.self_id, name="Rift", content=content)
    await UniMessage.reference(node).finish()


@abstract.handle()
async def abstract_handler(
        session: Uninfo,
        number: Match[str] = AlconnaMatch("number"),
        image: Match[str] = AlconnaMatch("image")):
    if not number.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()
    else:
        await UniMessage.text("正在查询...").send()

    number = number.result
    with_image = (image.available and image.result == "-i")
    info = mm.query(number, with_image)
    if info is None:
        await UniMessage.text(f"[{number}]找不到该编号！你再看看呢").finish()
    else:
        await intro_sender(session, number, info, with_image)


@randomId.handle()
async def randomId_handler(
        session: Uninfo,
        query: Match[str] = AlconnaMatch("query")):
    await UniMessage.text("正在生成...").send()
    album_id = randint(0, 1000000)
    while not mm.isValidAlbumId(str(album_id)):
        album_id += 13
        if album_id >= 1000000:
            album_id = randint(0, 1000000)

    if query.available and query.result == "-q":
        info = mm.query(album_id, True)
        await intro_sender(session, str(album_id), info, True)
    else:
        await UniMessage.text(str(album_id)).finish()
