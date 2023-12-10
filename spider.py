from models import *


async def main():
    # lei2_lang2 = Up(13692281)
    # dynamic_ids = await lei2_lang2.get_all_dynamics_id()
    # await lei2_lang2.write_all_to_json(dynamic_ids, 3)

    up = Up(519095739)
    dynamic_ids = await up.get_all_dynamics_id()
    print(dynamic_ids)
    await up.write_all_to_json(dynamic_ids, 3)

    up2 = Up(358895809)
    dynamic_ids = await up2.get_all_dynamics_id()
    print(dynamic_ids)
    await up2.write_all_to_json(dynamic_ids, 3)

    up3 = Up(2050603042)
    dynamic_ids = await up3.get_all_dynamics_id()
    print(dynamic_ids)
    await up3.write_all_to_json(dynamic_ids, 3)

asyncio.get_event_loop().run_until_complete(main())
