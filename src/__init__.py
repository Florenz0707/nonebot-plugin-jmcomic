# ------------------------ import ------------------------
# import packages from python
from .MainManager import *

# import packages from nonebot or other plugins
from nonebot import require, logger
from nonebot.permission import SUPERUSER

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import *

require("nonebot_plugin_uninfo")
from nonebot_plugin_uninfo import *

# ------------------------ import ------------------------

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

getStat = on_alconna(
    "jm.stat",
    use_cmd_start=True,
    permission=SUPERUSER
)


@getStat.handle()
async def stat_handler():
    ret = mm.getCacheSize("pdf")
    cnt = mm.getCacheCnt("pdf")
    await UniMessage.text(f"当前缓存大小为{ret:.2f} MB({(ret / 1024):.2f} GB)，"
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
        await UniMessage.text(f"[{number}]已存在于下载队列中！").send()
    if status == Status.GOOD:
        message = f"[{number}]已加入下载！"
        if (info := mm.query(number))[4] != 0:
            message += f"(预计大小：{info[4]:.2f}MB)"
        await UniMessage.text(message).send()
        mm.download()

    if status == Status.CACHED:
        await UniMessage.text("我早有准备！拿去吧！").send()

    await UniMessage.text(f"[{number}]发送中...({(mm.getFileSize(number, 'pdf')):.2f}MB)").send()
    await UniMessage.file(path=str(mm.getFilePath(number, 'pdf'))).finish()


@abstract.handle()
async def abstract_handler(
        session: Uninfo,
        number: Match[str] = AlconnaMatch("number"),
        image: Match[str] = AlconnaMatch("image")):
    if not number.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()

    number = number.result
    with_image = (image.available and image.result == "-i")
    info = mm.query(number, with_image)
    if info is None:
        await UniMessage.text(f"[{number}]找不到该编号！你再看看呢").finish()
    else:
        message = f"ID：{info[0]}\n" \
                  f"标题：{info[1]}\n" \
                  f"作者：{info[2]}\n" \
                  f"标签：{info[3]}"
        if info[4] != 0:
            message += f"\n预计大小：{info[4]:.2f}MB"

        content = UniMessage.text(message)
        if with_image:
            content = content.image(path=mm.getFilePath(number, "jpg"))
        node = CustomNode(uid=session.self_id, name="Rift", content=content)
        await UniMessage.reference(node).finish()
