# models.py line 437
async def insert_data(self, data_dic: dict):
    """
    插入数据到history table。

    Args:
        data_dic (dict): 形如{"column1": "'string'", "column2": "1234"}的字典，字典中的字符串键需要再次用引号包裹，非字符串值不需要。
    """
    column_list = []
    value_list = []
    # 从字典中获取要insert的值
    for c, v in data_dic.items():
        column_list.append(str(c))
        value_list.append(f"'{str(v)}'")
    # DEBUG
    print(
        f"INSERT INTO history({','.join(column_list)}) VALUES ({','.join(value_list)})")
    # DEBUG END
    self.cursor.execute(
        f"INSERT INTO history({','.join(column_list)}) VALUES ({','.join(value_list)})")
    # 提交更改使其生效
    self.connection.commit()


# save_history line 44
    # for i in updated_history:
    #     await database.insert_data(
    #         {
    #             "类型": f"'{history[0]}'",
    #             "标题": f"'{history[1]}'",
    #             "BV号": f"'{history[2]}'",
    #             "URL": f"'{history[3]}'",
    #             "时间": f"'{history[4]}'",
    #             "时间戳": history[5],
    #         }
    #     )
