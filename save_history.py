import httpx

from models import *

# settings.proxy = "http://192.168.31.94:7890"
database = Database("Database.db")


async def insert_history_data_into_db(db_instance: Database, values: list[list[str]]):
    """
    将列表内的内容插入数据库。

    Args:
        db_instance: 数据库实例
        values: 插入的值
                例：[
                        ["视频", "示例标题", "Bv114514", "https://bilibili.com/video/Bv114514", "2023年1月1日", "114514"]
                    ],
                    [
                        ...
                    ]
    """
    for i in values:
        await db_instance.insert_into_db(["类型", "标题", "BV号", "URL", "时间", "时间戳"],
                                         [i[0], i[1], i[2], i[3], i[4], i[5]])


async def try_to_get_history(history_num: int) -> Union[list[dict], False]:
    """
    尝试获取历史记录。

    Args:
        history_num: 获取历史记录数量

    Returns:
        list[dict]: 历史记录
        False: 连接超时
    """
    try:
        h = History(credential)
        new_history = await h.get_organised_history(history_num)
        return new_history
    except httpx.ConnectTimeout:
        logger.error("连接超时")
        return False


async def update_history_to_database(db_instance: Database, updated_history: list, history):
    logger.info("检测到历史记录有更新")
    # 若是更新正在看的视频的时间这种情况，则仅更新时间，不重复记录
    if updated_history[0]["URL"] == history[0][3]:
        logger.info("在看的视频的时间有更新")
        logger.debug("更新时间和时间戳")

        # 更新数据库中的时间戳和时间
        await database.update_data("history", "时间戳", updated_history[0]["时间戳"], "时间戳", history[0][5])
        await database.update_data("history", "时间", updated_history[0]["时间"], "时间", history[0][4])

    else:
        await insert_history_data_into_db(db_instance, updated_history)

if __name__ == "__main__":
    async def main():
        h = History(credential)
        db = Database("Database.db")
        while True:
            # 更新历史记录（断点续传）
            # 如已经有获取了的记录则读入并更新，否则跳过

            # 读取已经写入的记录
            history_data = await db.read_history_table()

            # 若为空，则获取历史记录并写入
            if not history_data:
                logger.info("历史记录为空")
                history = await h.get_organised_history(10)
                await insert_history_data_into_db(database, history)
            else:  # 若不为空，则将新的记录追加写入到开头，实现历史记录的更新
                # 获取新的记录
                logger.debug("读取历史记录文件")
                history = await db.read_history_table()
                print(history)  # DEBUG
                logger.debug("获取新记录")
                new_history = await try_to_get_history(10)
                updated_history = await h.get_updated_history(history, new_history)

                # 若有新的记录，则将其插入数据库
                if updated_history:
                    logger.info("新记录列表 {}", updated_history)
                    await update_history_to_database(updated_history, history)
                else:
                    logger.info("无新纪录")

                logger.debug("等待5秒")
                await asyncio.sleep(5)  # 防止访问过于频繁导致被封

    asyncio.get_event_loop().run_until_complete(main())
