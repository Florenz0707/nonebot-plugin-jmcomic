# ------------------------ import ------------------------
# import packages from python
from random import *

import nonebot.adapters.onebot.v11.exception
# import packages from nonebot or other plugins
from nonebot import require, get_bot
from nonebot.permission import SUPERUSER

from .GroupFileManager import *
from .MainManager import *

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
        Args["album_id?", str]
    ),
    use_cmd_start=True,
)

abstract = on_alconna(
    Alconna(
        "jm.q",
        Args["album_id?", str],
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

remoteControl = on_alconna(
    Alconna(
        "jm.m",
        Args["option?", str],
        Args["arg1?", str],
        Args["arg2?", str]
    ),
    use_cmd_start=True,
    permission=SUPERUSER
)

test = on_alconna(
    "test",
    use_cmd_start=True,
    permission=SUPERUSER
)


@test.handle()
async def test_handler(bot: Bot):
    group_files: dict = await bot.call_api("get_group_root_files", group_id="271480569")
    info = [(file.get("file_name"), file.get("modify_time")) for file in group_files.get("files")]
    info.sort(key=lambda x: int(x[1]))
    message = ""
    for name, time in info:
        message += f"{name} | {time}\n"
    await UniMessage.text(f"{message} Count: {len(info)}").finish()


@help_menu.handle()
async def help_menu_handler():
    message = """
1> .jm <id> 下载车牌为id的本子
2> .jm.q <id> [-i] 查询车牌为id的本子信息，使用-i参数可以附带首图
3> .jm.r [-q] 随机生成可用的车牌号，使用-q参数可以直接查询
?> .jm.m <cache/f_s/(d/u)_(s/c)/(r/l)_(s/i/d)>"""
    await UniMessage.text(message).finish(at_sender=True)


async def userFreqCheck(user_id: str):
    date = currentDate()
    daily_limit = mm.getUserLimit(user_id)
    mm.increaseUserFreq(user_id, date)
    if daily_limit is not None:
        use_cnt = mm.getUserFreq(user_id, date)
        if use_cnt > daily_limit:
            await UniMessage.text(" 不准用😡😡😡").finish(at_sender=True)
        await UniMessage.text(f" 你今天已经使用{use_cnt}/{daily_limit}次了哦~").send(at_sender=True)


@download.handle()
async def download_handler(
        bot: Bot,
        session: Uninfo,
        album_id: Match[str] = AlconnaMatch("album_id")):
    if not album_id.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()

    await userFreqCheck(session.user.id)

    album_id = album_id.result
    if session.scene.type == SceneType.GROUP:
        group_file_manager = GroupFileManager(bot, session.group.id)
        if await group_file_manager.albumExist(album_id):
            await UniMessage.text(f"[{album_id}]群文件里已经有了哦~去找找看吧！").finish()

    status = mm.add2queue(album_id)
    if status == Status.BAD:
        await UniMessage.text("出现了奇怪的错误！").finish()
    if status == Status.NOTFOUND:
        await UniMessage.text(f"[{album_id}]找不到该编号！你再看看呢").finish()
    if status == Status.BUSY:
        await UniMessage.text("当前排队的人太多啦！过会再来吧~").finish()
    if status == Status.REPEAT:
        await UniMessage.text(f"[{album_id}]已存在于下载队列中！").finish()
    if status == Status.RUDE:
        await UniMessage.text(f"[{album_id}]没有经过查询！别下载一些奇奇怪怪的东西哦~").finish()
    if status == Status.RESTRICT:
        await UniMessage.text(f"[{album_id}]被禁止下载！").finish()
    if status == Status.GOOD:
        message = f"[{album_id}]已加入下载！"
        if (info := await mm.getAlbumInfo(album_id)).get('size') != 0:
            message += f"(预计大小：{info['size']:.2f}MB)"
        await UniMessage.text(message).send()
        await mm.download()

    if not mm.upload(album_id):
        await UniMessage.text(f"[{album_id}]已经在上传了！等一会吧！").finish()
    if status == Status.CACHED:
        await UniMessage.text("我早有准备！拿去吧！").send()

    await UniMessage.text(f"[{album_id}]发送中...({(mm.getFileSize(album_id, FileType.PDF)):.2f}MB)").send()

    await UniMessage.file(path=str(mm.getFilePath(album_id, FileType.PDF))).send()
    mm.uploadDone(album_id)


async def intro_sender(
        album_id: str,
        info: dict,
        uid: str,
        bot: Bot,
        with_image=False):
    message = f"ID：{info.get('album_id')}\n" \
              f"标题：{info.get('title')}\n" \
              f"作者：{info.get('author')}\n" \
              f"标签：{info.get('tags')}"
    if info.get('size') != 0:
        message += f"\n预计大小：{info.get('size'):.2f}MB"

    content = UniMessage.text(message)
    if with_image:
        content += UniMessage.image(path=mm.getFilePath(album_id, FileType.JPG))
    node = CustomNode(uid=uid, name="Rift", content=content)
    try:
        await UniMessage.reference(node).finish()
    except nonebot.adapters.onebot.v11.exception.ActionFailed as error:
        error = str(error)
        if "发送转发消息" in error and "失败" in error:
            await UniMessage.text(f"[{album_id}]发送转发消息失败了！").finish()
        # logger.warning(error)


@abstract.handle()
async def abstract_handler(
        bot: Bot,
        session: Uninfo,
        album_id: Match[str] = AlconnaMatch("album_id"),
        image: Match[str] = AlconnaMatch("image")):
    if not album_id.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()
    else:
        await UniMessage.text("正在查询...").send()

    await userFreqCheck(session.user.id)

    album_id = album_id.result
    with_image = (image.available and image.result == "-i")
    info = await mm.getAlbumInfo(album_id, with_image)
    if info is None:
        await UniMessage.text(f"[{album_id}]找不到该编号！你再看看呢").finish()
    else:
        await intro_sender(album_id, info, session.self_id, bot, with_image)


@randomId.handle()
async def randomId_handler(
        bot: Bot,
        session: Uninfo,
        query: Match[str] = AlconnaMatch("query")):
    await UniMessage.text("正在生成...").send()
    album_id = randint(0, 1000000)
    while not mm.isValidAlbumId(str(album_id)):
        album_id += 13
        if album_id >= 1000000:
            album_id = randint(0, 1000000)

    if query.available and query.result == "-q":
        info = await mm.getAlbumInfo(album_id, True)
        await intro_sender(str(album_id), info, session.self_id, bot, True)
    else:
        await UniMessage.text(str(album_id)).finish()


@remoteControl.handle()
async def remoteControl_handler(
        option: Match[str] = AlconnaMatch("option"),
        arg1: Match[str] = AlconnaMatch("arg1"),
        arg2: Match[str] = AlconnaMatch("arg2")):
    if not option.available:
        return

    option = option.result
    if option == "cache":
        message = f"当前共有{mm.getCacheCnt(FileType.PDF)}个PDF文件，共计占用空间{mm.getCacheSize(FileType.PDF):.2f}MB。\n" \
                  f"当前共有{mm.getCacheCnt(FileType.JPG)}个JPG文件，共计占用空间{mm.getCacheSize(FileType.JPG):.2f}MB。"
        await UniMessage.text(message).finish()

    if option == "d_s":
        download_queue: list = mm.getDownloadQueue()
        if len(download_queue) == 0:
            await UniMessage.text("当前下载队列为空。").finish()
        else:
            message = ""
            for album_id in download_queue:
                message += f"{album_id} "
            await UniMessage.text(f"当前下载队列共有{len(download_queue)}个任务：'{message}'").finish()

    if option == "d_c":
        mm.clearDownloadQueue()
        await UniMessage.text("下载队列已清空。").finish()

    if option == "u_s":
        upload_queue: list = mm.getUploadQueue()
        if len(upload_queue) == 0:
            await UniMessage.text("当前上传队列为空。").finish()
        else:
            message = ""
            for album_id in upload_queue:
                message += f"{album_id} "
            await UniMessage.text(f"当前上传队列共有{len(upload_queue)}个任务：'{message}'").finish()

    if option == "u_c":
        mm.clearUploadQueue()
        await UniMessage.text("上传队列已清空。").finish()

    if option == "r_s":
        tag_list, album_id_list = mm.getRestriction()
        tags = "Tags："
        album_ids = "Album_ids："
        for tag in tag_list:
            tags += f"\n#{tag[1]}"
        for album_id in album_id_list:
            album_ids += f"\n\"{album_id[1]}\""
        await UniMessage.text(tags).send()
        await UniMessage.text(album_ids).send()

    if option == "r_i" or option == "r_d":
        if not (arg1.available and arg2.available):
            await UniMessage.text("参数错误。").finish()
        kind = arg1.result
        info = arg2.result
        if kind != "tag" and kind != "album_id":
            await UniMessage.text("参数错误。").finish()
        error = mm.insertRestriction(kind, info) if option == "r_i" else mm.deleteRestriction(kind, info)
        if error is not None:
            await UniMessage.text(f"发生错误：{error}").finish()
        else:
            await UniMessage.text(f"成功处理条目：{kind} {info}").finish()

    if option == "f_s":
        date = currentDate()
        info = mm.getAllFreq(date)
        message = f"以下是{date}的使用记录："
        for user_id, use_cnt in info:
            message += f"\n{user_id}: {use_cnt}"
        await UniMessage.text(message).finish()

    if option == "l_s":
        if arg1.available:
            user_id = arg1.result
            if (daily_limit := mm.getUserLimit(user_id)) is None:
                await UniMessage.text("暂无数据信息。").finish()
            else:
                await UniMessage.text(f"{user_id}: {daily_limit}").finish()
        else:
            info = mm.getAllLimit()
            if len(info) == 0:
                await UniMessage.text("暂无数据信息。").finish()
            message = f"共有{len(info)}条数据："
            for user_id, daily_limit in info:
                message += f"\n{user_id}: {daily_limit}"
            await UniMessage.text(message).finish()

    if option == "l_i":
        if not (arg1.available and arg2.available):
            await UniMessage.text("参数错误。").finish()
        user_id = arg1.result
        daily_limit = arg2.result
        mm.setUserLimit(user_id, daily_limit)
        await UniMessage.text(f"[{user_id}: {daily_limit}] 已加入限制。").finish()

    if option == "l_d":
        if not arg1.available:
            await UniMessage.text("参数错误。").finish()
        user_id = arg1.result
        mm.deleteUserLimit(user_id)
        await UniMessage.text(f"[{user_id}] 已解除限制。").finish()
