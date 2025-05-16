# ------------------------ import ------------------------
# import packages from python
from random import *

import nonebot.adapters.onebot.v12.exception
# import packages from nonebot or other plugins
from nonebot import require
from nonebot.permission import Permission, SUPERUSER, SuperUser, Event

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
        "jm.d",
        Args["album_id?", str],
        Args["force?", str]
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
    permission=SUPERUSER | ADMIN()
)

queryXP = on_alconna(
    Alconna(
        "jm.xp",
        Option("-u", Args["user_id?", str]),
        Option("-l", Args["length?", int])
    ),
    use_cmd_start=True
)

remoteControl = on_alconna(
    Alconna(
        "jm.m",
        Subcommand("cache"),
        Subcommand("proxy"),
        Subcommand("f_s"),
        Subcommand("d_s"),
        Subcommand("d_c"),
        Subcommand("u_s"),
        Subcommand("u_c"),
        Subcommand("r_s"),
        Subcommand(
            "r_i",
            Args["type?", str],
            Args["info", str]
        ),
        Subcommand(
            "r_d",
            Args["type?", str],
            Args["info", str]
        ),
        Subcommand(
            "l_s",
            Args["user_id?", str]
        ),
        Subcommand(
            "l_i",
            Args["user_id?", str],
            Args["limit", int]
        ),
        Subcommand(
            "l_d",
            Args["user_id?", str]
        )
    ),
    use_cmd_start=True,
    permission=SUPERUSER
)

remoteControl_cache = remoteControl.dispatch("cache")
remoteControl_proxy = remoteControl.dispatch("proxy")
remoteControl_fs = remoteControl.dispatch("f_s")
remoteControl_ds = remoteControl.dispatch("d_s")
remoteControl_dc = remoteControl.dispatch("d_c")
remoteControl_us = remoteControl.dispatch("u_s")
remoteControl_uc = remoteControl.dispatch("u_c")
remoteControl_rs = remoteControl.dispatch("r_s")
remoteControl_ri = remoteControl.dispatch("r_i")
remoteControl_rd = remoteControl.dispatch("r_d")
remoteControl_ls = remoteControl.dispatch("l_s")
remoteControl_li = remoteControl.dispatch("l_i")
remoteControl_ld = remoteControl.dispatch("l_d")

test = on_alconna(
    Alconna(
        "test",
        Args["force", str]
    ),
    use_cmd_start=True,
    permission=SUPERUSER
)


@test.handle()
async def test_handler(
        arg: Match[str] = AlconnaMatch("force")):
    if arg.available:
        arg = arg.result
        await UniMessage.text(arg).finish()


@help_menu.handle()
async def help_menu_handler():
    message = """
1> .jm.d <id> 下载车牌为id的本子
2> .jm.q <id> [-i] 查询车牌为id的本子信息，使用-i参数可以附带首图
3> .jm.r [-q] 随机生成可用的车牌号，使用-q参数可以直接查询
4> .jm.xp [-u QQ] [-l 长度] 查询指定用户的XP，默认查询自己，默认长度为5，最大为20
?> .jm.m <cache/proxy/f_s/(d/u)_(s/c)/(r/l)_(s/i/d)>"""
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
        event: Event,
        session: Uninfo,
        album_id: Match[str] = AlconnaMatch("album_id"),
        force: Match[str] = AlconnaMatch("force")):
    if not album_id.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()

    await userFreqCheck(session.user.id)

    album_id = album_id.result
    if session.scene.type == SceneType.GROUP:
        group_file_manager = GroupFileManager(bot, session.group.id)
        if await group_file_manager.albumExist(album_id):
            await UniMessage.text(f"[{album_id}]群文件里已经有了哦~去找找看吧！").finish()

    perm = Permission(SuperUser())
    forced: bool = (force.available and force.result == "-f" and await perm(bot, event))
    status = mm.add2queue(album_id, forced)
    if status == Status.BAD:
        await UniMessage.text("出现了奇怪的错误！").finish()
    if status == Status.NOTFOUND:
        await UniMessage.text(f"[{album_id}]找不到该编号！你再看看呢").finish()
    if status == Status.BUSY:
        await UniMessage.text("当前排队的人太多啦！过会再来吧~").finish()
    if status == Status.DOWNLOADING:
        await UniMessage.text(f"[{album_id}]已存在于下载队列中！").finish()
    if status == Status.UPLOADING:
        await UniMessage.text(f"[{album_id}]已经在上传了！等一会吧！").finish()
    if status == Status.RUDE:
        await UniMessage.text(f"[{album_id}]没有经过查询！别下载一些奇奇怪怪的东西哦~").finish()
    if status == Status.RESTRICT:
        info = mm.getRestrictedInfo(album_id)
        await UniMessage.text(f"[{album_id}]被禁止下载！\n原因：{info}").finish()
    if status == Status.CACHED:
        await UniMessage.text("我早有准备！拿去吧！").send()
    if status == Status.GOOD:
        mm.increaseUserXPByAlbumID(session.user.id, album_id)
        message = f"[{album_id}]已加入下载！"
        if (info := await mm.getAlbumInfo(album_id)).get('size') != 0:
            message += f"(预计大小：{info.get('size'):.2f}MB)"
        await UniMessage.text(message).send()
        try:
            await mm.download(album_id)
        except jmcomic.JmcomicException as error:
            await UniMessage.text(f"[{album_id}]发生错误：{str(error).strip()}").finish()
        else:
            pass
        finally:
            mm.downloadDone(album_id)

    mm.upload(album_id)
    await UniMessage.text(f"[{album_id}]发送中...({(mm.getFileSize(album_id, FileType.PDF)):.2f}MB)").send()
    try:
        await UniMessage.file(path=str(mm.getFilePath(album_id, FileType.PDF))).send()
    except nonebot.adapters.onebot.v11.exception.NetworkError as error:
        logger.error(str(error))
    else:
        pass
    finally:
        mm.uploadDone(album_id)


async def intro_sender(
        album_id: str,
        info: dict,
        uid: str,
        with_image=False):
    message = f"ID：{info.get('album_id')}\n" \
              f"标题：{info.get('title')}\n" \
              f"作者：{info.get('author')}\n" \
              f"标签：{info.get('tags')}"
    if info.get('page') != 0:
        message += f"\n页数：{info.get('page')}"
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
        session: Uninfo,
        album_id: Match[str] = AlconnaMatch("album_id"),
        image: Match[str] = AlconnaMatch("image")):
    if not album_id.available:
        await UniMessage.text("看不懂！再试一次吧~").finish()

    await userFreqCheck(session.user.id)

    album_id = album_id.result
    with_image = (image.available and image.result == "-i")
    await UniMessage.text("正在查询...").send()
    info = await mm.getAlbumInfo(album_id, with_image)
    if info is None:
        await UniMessage.text(f"[{album_id}]找不到该编号！你再看看呢").finish()
    else:
        await intro_sender(album_id, info, session.self_id, with_image)


@randomId.handle()
async def randomId_handler(
        session: Uninfo,
        query: Match[str] = AlconnaMatch("query")):
    await userFreqCheck(session.user.id)
    await UniMessage.text("正在生成...").send()

    retry = 0
    left_bound = 100000
    right_bound = 1200000
    album_id = randint(left_bound, right_bound)
    while not mm.isValidAlbumId(str(album_id)):
        album_id += 13
        retry += 1
        if retry > 9:
            retry = 0
            album_id = randint(left_bound, right_bound)

    album_id = str(album_id)
    if query.available and query.result == "-q":
        info = await mm.getAlbumInfo(album_id, True)
        await intro_sender(album_id, info, session.self_id, True)
    else:
        await UniMessage.text(album_id).finish()


@queryXP.handle()
async def queryXP_handler(
        session: Uninfo,
        user_id: Query[str] = Query("user_id"),
        length: Query[int] = Query("length", 5)):
    if user_id.available:
        user_id = user_id.result
    else:
        user_id = session.user.id

    length = min(length.result, 20)
    info = mm.getUserXP(user_id, length)
    if info is None:
        await UniMessage.text(f"{user_id}目前还没有XP记录！").finish()
    message = f"这是{user_id}的XP记录！\n（此处展示前{length}条）"
    for cnt in range(len(info)):
        message += f"\n{cnt + 1}. #{info[cnt][0]} -> {info[cnt][1]}"
    await UniMessage.text(message).finish()


@remoteControl_cache.handle()
async def remoteControl_cache_handler():
    message = f"当前共有{mm.getCacheCnt(FileType.PDF)}个PDF文件，共计占用空间{mm.getCacheSize(FileType.PDF):.2f}MB。\n" \
              f"当前共有{mm.getCacheCnt(FileType.JPG)}个JPG文件，共计占用空间{mm.getCacheSize(FileType.JPG):.2f}MB。"
    await UniMessage.text(message).finish()


@remoteControl_proxy.handle()
async def remoteControl_proxy_handler():
    mm.switchProxy()
    proxy = "开启" if mm.getProxy() else "关闭"
    await UniMessage.text(f"已{proxy}代理。").finish()


@remoteControl_fs.handle()
async def remoteControl_fs_handler():
    date = currentDate()
    info = mm.getAllFreq(date)
    message = f"{date2words(date)}的使用记录："
    for user_id, use_cnt in info:
        message += f"\n{user_id}: {use_cnt}"
    await UniMessage.text(message).finish()


@remoteControl_ds.handle()
async def remoteControl_ds_handler():
    download_queue: list = mm.getDownloadQueue()
    if len(download_queue) == 0:
        await UniMessage.text("当前下载队列为空。").finish()
    else:
        message = ""
        for album_id in download_queue:
            message += f"[{album_id}] "
        await UniMessage.text(f"当前下载队列共有{len(download_queue)}个任务：{message}").finish()


@remoteControl_dc.handle()
async def remoteControl_dc_handler():
    mm.clearDownloadQueue()
    await UniMessage.text("下载队列已清空。").finish()


@remoteControl_us.handle()
async def remoteControl_us_handler():
    upload_queue: list = mm.getUploadQueue()
    if len(upload_queue) == 0:
        await UniMessage.text("当前上传队列为空。").finish()
    else:
        message = ""
        for album_id in upload_queue:
            message += f"[{album_id}] "
        await UniMessage.text(f"当前上传队列共有{len(upload_queue)}个任务：{message}").finish()


@remoteControl_uc.handle()
async def remoteControl_uc_handler():
    mm.clearUploadQueue()
    await UniMessage.text("上传队列已清空。").finish()


@remoteControl_rs.handle()
async def remoteControl_rs_handler():
    tag_list, album_id_list = mm.getRestriction()
    tags = "Tags："
    album_ids = "Album_ids："
    for tag in tag_list:
        tags += f"\n#{tag[1]}"
    for album_id in album_id_list:
        album_ids += f"\n[{album_id[1]}]"
    await UniMessage.text(tags).send()
    await UniMessage.text(album_ids).send()


@remoteControl_ri.handle()
async def remoteControl_ri_handler(
        kind: Match[str] = AlconnaMatch("type"),
        info: Match[str] = AlconnaMatch("info")):
    if not (kind.available and info.available):
        await UniMessage.text("参数错误。").finish()
    kind = kind.result
    info = info.result
    if kind != "tag" and kind != "album_id":
        await UniMessage.text("参数错误。").finish()
    error = mm.insertRestriction(kind, info)
    if error is not None:
        await UniMessage.text(f"发生错误：{error}").finish()
    else:
        await UniMessage.text(f"成功处理条目：{kind} {info}").finish()


@remoteControl_rd.handle()
async def remoteControl_rd_handler(
        kind: Match[str] = AlconnaMatch("type"),
        info: Match[str] = AlconnaMatch("info")):
    if not (kind.available and info.available):
        await UniMessage.text("参数错误。").finish()
    kind = kind.result
    info = info.result
    if kind != "tag" and kind != "album_id":
        await UniMessage.text("参数错误。").finish()
    error = mm.deleteRestriction(kind, info)
    if error is not None:
        await UniMessage.text(f"发生错误：{error}").finish()
    else:
        await UniMessage.text(f"成功处理条目：{kind} {info}").finish()


@remoteControl_ls.handle()
async def remoteControl_ls_handler(
        user_id: Match[str] = AlconnaMatch("user_id")):
    if user_id.available:
        user_id = user_id.result
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


@remoteControl_li.handle()
async def remoteControl_li_handler(
        user_id: Match[str] = AlconnaMatch("user_id"),
        limit: Match[str] = AlconnaMatch("limit")):
    if not (user_id.available and limit.available):
        await UniMessage.text("参数错误。").finish()
    user_id = user_id.result
    daily_limit = limit.result
    mm.setUserLimit(user_id, daily_limit)
    await UniMessage.text(f"[{user_id}: {daily_limit}] 已加入限制。").finish()


@remoteControl_ld.handle()
async def remoteControl_li_handler(user_id: Match[str] = AlconnaMatch("user_id")):
    if not user_id.available:
        await UniMessage.text("参数错误。").finish()
    user_id = user_id.result
    mm.deleteUserLimit(user_id)
    await UniMessage.text(f"[{user_id}] 已解除限制。").finish()
