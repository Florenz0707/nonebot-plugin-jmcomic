from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger


class GroupFileManager:
    def __init__(self, bot: Bot, group_id: str):
        self.group_id = group_id
        self.bot = bot

    async def getFileList(self) -> list:
        group_files: dict = await self.bot.call_api("get_group_root_files", group_id=self.group_id)
        # logger.warning(group_files)
        files = [file.get("file_name") for file in group_files.get("files")]
        # logger.warning(files)
        return files

    async def albumExist(self, album_id: str) -> bool:
        return f"{album_id}.pdf" in await self.getFileList()
