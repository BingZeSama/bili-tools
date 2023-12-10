import asyncio
import json
import re
import time
import datetime
import sqlite3
from loguru import logger
from typing import *

from bilibili_api import dynamic
from bilibili_api import user
from bilibili_api import settings
from bilibili_api import video
from credential import *

logger.add("log/log_{time}.log")
# settings.proxy = "http://192.168.31.94:7890"  # 此处填写你的代理地址
logger.debug("配置sessdata为 {}", credential.sessdata)
logger.debug("配置bili_jct为 {}", credential.bili_jct)
logger.debug("配置buvid3为 {}", credential.buvid3)
logger.debug("配置dedeuserid为 {}", credential.dedeuserid)


async def find_hashtag_topics(text: str) -> Optional[list]:
    """
    查找话题，返回找到的话题列表。

    Args:
        text: 要寻找的文本

    Returns:
        找到的话题
    """
    hashtag_topics = re.findall(r"#\w+#", text)
    if not hashtag_topics:
        return None

    return hashtag_topics


class Up:
    def __init__(self, up_uid: int) -> None:
        self.uid: int = up_uid

    async def get_info(self) -> dict:
        """
        获取UP主的信息，包含UID、昵称、性别、头像URL、签名和等级。

        Returns:
            info_dic: 包含上述信息的字典
        """
        user_: user.User = user.User(self.uid)
        raw_info = await user_.get_user_info()
        info_dic = {
            "UID": raw_info["mid"],
            "昵称": raw_info["name"],
            "性别": raw_info["sex"],
            "头像": raw_info["face"],
            "签名": raw_info["sign"],
            "等级": raw_info["level"],
        }
        return info_dic

    async def get_dynamics_id(self, times: int) -> list[int]:
        """
        从UID获取其发布的动态ID。

        Args:
            times: 循环获取次数

        Returns:
            包含动态ID的列表
        """
        uids: list = []
        next_offset: int = 0
        user_ = user.User(self.uid)
        for i in range(times):
            raw = await user_.get_dynamics(
                offset=next_offset, need_top=False
            )  # need_top=False: 不获取置顶动态
            for j in raw["cards"]:
                uids.append(j["desc"]["dynamic_id"])
            # 获取next_offset的值，循环填充该值以获取所有动态
            next_offset = raw["next_offset"]
            time.sleep(2)

        return uids

    async def get_all_dynamics_id(self) -> list:
        """
        从UID获取其发布的动态ID。

        Returns:
            包含动态ID的列表
        """
        uids = []
        next_offset = 0
        user_ = user.User(self.uid)
        while True:
            # TODO 修复意外实参
            raw = await user_.get_dynamics(offset=next_offset, need_top=False)
            try:
                for j in raw["cards"]:
                    uids.append(j["desc"]["dynamic_id"])
                    print(j["desc"]["dynamic_id"])
                # 获取next_offset的值，循环填充该值以获取所有动态
                next_offset = raw["next_offset"]
                # time.sleep(1)
            except KeyError:
                pass
            if raw["has_more"] != 1:
                return uids

    async def update_dynamic(self):
        pass

    async def write_all_to_json(self, dynamic_ids: list, delay: int):
        """
        将所有位于dynamic_ids的动态写入json文件。支持断点续传。

        Args:
            dynamic_ids: 需要写入的所有动态ID
            delay: 写入的间隔时间，防止访问过于频繁导致封禁
        """
        json_data = await Database.read_history_table()
        if json_data:
            last_wrote_id = json_data[-1]["动态ID"]
            last_wrote_dynamic = Dynamic(last_wrote_id)
            next_id = await last_wrote_dynamic.get_next_write_id(dynamic_ids)
        else:
            next_id = dynamic_ids[0]

        while next_id:
            d = Dynamic(next_id)
            await d.async_init()
            await d.write_one_to_json(filename)
            next_id = await d.get_next_write_id(dynamic_ids)
            time.sleep(delay)


class Dynamic:
    def __init__(self, dynamic_id: int):
        """
        构造函数。

        Args:
            dynamic_id: 动态ID
        """
        self.dynamic_kind = None
        self.dynamic_id = dynamic_id

    async def async_init(self):
        self.dynamic_kind = await self.detect_dynamic_kind()

    async def get_info(self):
        """
        获取动态信息，包含内容、官方标签、井号标签、图片URL和发布日期。

        Returns:
            str: 如果动态类型是转发动态或视频动态则返回动态类型
            dict: 如果是普通动态，则返回包含以下信息的字典
                '动态ID': 动态ID (int of str)
                '类型': 动态类型 (str)
                '发布日期': 发布日期 (str)
                '内容': 动态内容 (str)
                '标签列表（官方）': 官方标签列表 (list of str)
                '标签列表（#）': 井号标签列表 (list of str)
                '图片URL': 图片URL列表 (list of str)
        """
        info_dict = {"动态ID": self.dynamic_id}

        # 非普通动态只有动态ID和类型这两个键
        print(self.dynamic_id)
        if self.dynamic_kind != "DYNAMIC_TYPE_DRAW":
            info_dict["类型"] = self.dynamic_kind
            return info_dict

        d = dynamic.Dynamic(self.dynamic_id)
        raw = await d.get_info()
        dynamic_text = raw["item"]["modules"]["module_dynamic"]["desc"]["text"]
        image_urls = []
        for i in raw["item"]["modules"]["module_dynamic"]["major"]["draw"]["items"]:
            image_urls.append(i["src"])
        image_urls = None if not image_urls else image_urls

        info_dict["发布日期"] = raw["item"]["modules"]["module_author"]["pub_time"]
        info_dict["内容"] = dynamic_text
        info_dict["标签（官方）"] = (
            raw["item"]["modules"]["module_dynamic"]["topic"]["name"]
            if raw["item"]["modules"]["module_dynamic"]["topic"]
            else None,
        )
        info_dict["标签（#）"] = await find_hashtag_topics(dynamic_text)
        info_dict["图片URL"] = image_urls

        return info_dict

    async def detect_dynamic_kind(self) -> str:
        """
        判断动态类型。

        Returns:
            str:
                DYNAMIC_TYPE_DRAW: 普通动态
                DYNAMIC_TYPE_FORWARD: 转发动态
                DYNAMIC_TYPE_AV: 视频动态
                DYNAMIC_TYPE_WORD: 直播预约动态
                DYNAMIC_TYPE_ARTICLE: 文章
                DYNAMIC_TYPE_COMMON_SQUARE: 评分

        Raises:
            ValueError: 无法判断动态类型
        """
        dynamic_ = dynamic.Dynamic(self.dynamic_id)
        raw = await dynamic_.get_info()
        type_ = raw["item"]["type"]
        if type_ == "DYNAMIC_TYPE_DRAW":
            return "DYNAMIC_TYPE_DRAW"
        elif type_ == "DYNAMIC_TYPE_FORWARD":
            return "DYNAMIC_TYPE_FORWARD"
        elif type_ == "DYNAMIC_TYPE_AV":
            return "DYNAMIC_TYPE_AV"
        elif type_ == "DYNAMIC_TYPE_WORD":
            return "DYNAMIC_TYPE_WORD"
        elif type_ == "DYNAMIC_TYPE_ARTICLE":
            return "DYNAMIC_TYPE_ARTICLE"
        elif type_ == "DYNAMIC_TYPE_COMMON_SQUARE":
            return "DYNAMIC_TYPE_COMMON_SQUARE"
        else:
            self.dynamic_kind = None
            raise ValueError("无法判断动态类型")

    async def get_next_write_id(self, dynamic_ids: list):
        """
        获取下一次应该写入的动态ID

        Args:
            dynamic_ids: 需要写入的所有动态ID

        Returns:
            有下一个需要写入的动态ID时返回该动态ID。没有时返回None
        """
        # 如果不是列表的最后一项，代表还未写入完成，则接着上次继续写入
        index = dynamic_ids.index(self.dynamic_id)
        if index != len(dynamic_ids) - 1:
            return dynamic_ids[index + 1]
        else:
            return None

    async def write_one_to_json(self, filename: str):
        """
        写入一个动态到json文件。

        Args:
            filename: json文件
        """
        raise Exception("未定义。")
        # data_list = await load_from_json(filename)
        #
        # data = await self.get_info()
        # print(data, "\n")
        # data_list.append(data)
        #
        # # 写入整个列表
        # with open(filename, "w+") as j:
        #     json.dump(data_list, j, ensure_ascii=False)


class DataProcess:
    # TODO 待重构
    def __init__(self, filename: str):
        """
        构造函数。

        Args:
            filename: json文件
        """
        self.filename = filename

    def read_data_from_json(self) -> list:
        with open(self.filename, "r") as json_file:
            data_list = json.load(json_file)

        return data_list

    def count_key(self, key: str):
        pass


class History:
    def __init__(self, credential: credential):
        self.credential = credential
        self.view_at = None
        self.raw_list_data = None

    async def get_raw_list_data(self, history_num: int) -> list[dict]:
        """
        获取历史记录源数据下的"list"下的内容(list)

        Args:
            history_num: 需要获取的历史记录总数

        Returns:
            原始数据
        """
        iteration = (history_num - 1) // 20 + 1
        data_list = []
        for i in range(iteration):
            data = await user.get_self_history_new(
                credential, view_at=self.view_at, ps=20
            )
            data_list.append(data["list"])
        data_list_one_layer = []
        # 将每次获取的列表拼合
        for i in data_list:
            for j in i:
                data_list_one_layer.append(j)

        # 只返回指定数量的历史记录
        self.raw_list_data = data_list_one_layer[:history_num]

        return data_list_one_layer[:history_num]

    async def _get_info_list(self, index: int) -> list[list[str]]:
        """
        获取位于["list"]下的索引为index的信息。
        列表顺序：类型（视频或直播）、标题、BV号、URL、时间、时间戳

        Args:
            index: 索引

        Returns:
            具有上述信息的列表
        """
        # 获取history中的指定信息
        video_type = (
            "直播" if self.raw_list_data[index]["history"]["business"] == "live" else "视频"
        )
        info_list = [video_type, self.raw_list_data[index]["title"]]
        url = None

        bvid = self.raw_list_data[index]["history"]["bvid"]
        info_list.append(bvid)

        if video_type == "视频":
            url = "https://www.bilibili.com/video/" + bvid
        elif video_type == "直播":
            url = self.raw_list_data[index]["uri"]
        info_list.append(url)

        time_stamp = self.raw_list_data[index]["view_at"]
        time_ = datetime.datetime.fromtimestamp(time_stamp)
        time_formatted = time_.strftime("%Y/%m/%d %H:%M:%S")
        info_list.append(time_formatted)
        info_list.append(int(time_stamp))

        return info_list

    async def get_organised_history(self, history_num: int) -> list[list]:
        """
        获取指定数量并整理过的历史记录。

        Args:
            history_num: 需要获取的历史记录总数

        Returns:
            历史记录
        """
        self.raw_list_data: list[dict] = await self.get_raw_list_data(history_num)
        info_list = []
        for i in range(len(self.raw_list_data)):
            info_list.append(await self._get_info_list(i))

        return info_list

    async def get_updated_history(self, old_history: list[tuple], new_history: list[tuple]) -> Optional[list[tuple]]:
        """
        返回所有更新的历史记录组成列表。

        Args:
            old_history: 包含多个字典的列表，每个字典都包含时间戳信息。旧历史记录
            new_history: 包含多个字典的列表，每个字典都包含时间戳信息。新历史记录

        Returns:
            list[dict]: 更新的历史记录
            None: 无更新的历史记录
        """
        latest_timestamp = old_history[0][5]
        # 在列表中查找包含特定时间戳的字典的索引
        for index, item in enumerate(new_history):
            if item["时间戳"] > latest_timestamp:
                return new_history[:index + 1]

        return None


class Database:
    def __init__(self, db_path: str):
        """
        Args:
            db_path: 数据库路径
        """
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()

    async def touch_history_table(self):
        """
        history table不存在时创建。
        """
        # Create "history" table if it doesn't exist
        self.cursor.execute(
            """
            CREATE TABLE if NOT EXISTS history(
            类型 TEXT NOT NULL,
            标题 TEXT NOT NULL,
            BV号 TEXT,
            URL TEXT NOT NULL,
            时间 TEXT NOT NULL,
            时间戳 INTEGER NOT NULL
            )
            """
        )

    async def read_history_table(self):
        """
        读取history table。

        Returns:
            list[tuple]: 在table内的每条数据
        """
        await self.touch_history_table()
        # Read "history"(list) to "history_records"
        self.cursor.execute("SELECT * FROM history")
        # 获取SQLite的输出
        output = self.cursor.fetchall()

        return output

    async def insert_into_db(self, column_list: list[str], value_list: list) -> None:
        """
        插入数据到数据库。

        Args:
            column_list: 插入的行
            value_list: 插入的列

        Raises:
            ValueError: 表头和值的长度不匹配
        """
        if len(column_list) != len(value_list):
            raise ValueError("表头和值的长度不匹配。")

        # 将每个值都转为str并加上双引号
        quoted_values = [f"\"{str(i)}\"" for i in value_list]

        column_string = ','.join(column_list)
        values_string = ','.join(quoted_values)

        insert_query = f"INSERT INTO history({column_string}) VALUES ({values_string})"

        self.cursor.execute(insert_query)
        self.connection.commit()

    async def update_data(self, table: str, changed_column: str, changed_value: str, where_column: str, where_value: str):
        """
        在数据库中更新一个column。

        Args:
            table (str): 要更改的table名称
            changed_column (str): 要更改的column
            changed_value (str): 要将column改成的value
            where_column (str): 用于定位数据的column
            where_value (str): 用于定位数据的value
        """
        # 将传入的下列参数格式化，头尾加上双引号
        changed_value_formatted = f"\"{str(changed_value)}\""
        where_value_formatted = f"\"{str(where_value)}\""

        # 更新数据的SQL命令
        sqlite_command = f"UPDATE {table} SET {changed_column} = {changed_value_formatted} WHERE {where_column} = {where_value_formatted}"
        print(sqlite_command)  # DEBUG
        self.cursor.execute(sqlite_command)
        self.connection.commit()


class Video:
    def __init__(self, credential: credential):
        self.credential = credential

    async def add_to_favorite(self, bvids: list, favorite_list_id: list):
        for i in bvids:
            v = video.Video(credential=self.credential, bvid=i)
            await v.set_favorite(add_media_ids=favorite_list_id)


if __name__ == "__main__":
    async def main():
        pass
    asyncio.get_event_loop().run_until_complete(main())
