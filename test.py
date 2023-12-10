from save_history import *
from models import *


if __name__ == "__main__":
    async def main():
        db = Database("database.db")
        h = History(credential)
        history = await h.get_organised_history(12)
        print(history)


    asyncio.get_event_loop().run_until_complete(main())
