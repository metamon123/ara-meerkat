from slacker import Slacker
from config import bot_token
from threading import Thread
import websockets
import asyncio
import re, json

from chromecat import search_and_report

class meerkat(object):
    def __init__(self):
        self.slack = Slacker(bot_token)
        self.update_lists()

    def update_lists(self):
        self.mems = self.slack.users.list().body["members"]
        self.ims = self.slack.im.list().body["ims"]

    def get_imid_by_email(self, email):
        return self.get_imid_by_uid(self.get_userid_by_email(email))

    def get_imid_by_uid(self, uid):
        if uid == "":
            return ""
        for im in self.ims:
            if im["user"] == uid:
                return im["id"]
        return ""

    def get_userid_by_email(self, email):
        for mem in self.mems:
            if "email" in mem["profile"].keys() and mem["profile"]["email"] == email:
                return mem["id"]
        return ""

    def send_dm_by_email(self, email, text=None, attachments=None):
        return self.send_dm_by_uid(self.get_userid_by_email(email), text, attachments)

    def send_dm_by_uid(self, uid, text=None, attachments=None):
        if uid == "":
            return False
        self.slack.im.open(uid)
        self.slack.chat.post_message(self.get_imid_by_uid(uid), text=text, attachments=attachments, as_user=True)
        return True

    async def listen(self):
        resp = self.slack.rtm.start()
        self.endpoint = resp.body["url"]
        self.socket = await websockets.connect(self.endpoint)
        while True:
            '''
            msg_json =
                {
                    "type":"message",
                    "user":"UAV2C5B70",
                    "text":"hi",
                    "client_msg_id":"~",
                    "team":"~",
                    "channel":"~",
                    "ts":"~",
                    "event_ts":"~"
                }
            '''
            msg_json = json.loads(await self.socket.recv())

            if msg_json["type"] != "message" or "bot_id" in msg_json: # bot's response is also read...
                continue
            print("received : ", msg_json)
            msg = msg_json["text"]
            uid = msg_json["user"]
            pattern = re.compile("\S+")
            msg_tokens = pattern.findall(msg)
            if msg_tokens[0] == "!검색":
                if len(msg_tokens) == 1:
                    wrong_search_msg = "Wrong usage of !검색. It needs at least one keyword"
                    self.slack.im.open(uid)
                    self.slack.chat.post_message(self.get_imid_by_uid(uid), text=wrong_search_msg, attachments=None, as_user=True)
                else:
                    t = Thread(target=search_and_report, args=(msg_tokens[1:], self, "", uid, ))
                    t.start()
                    self.slack.im.open(uid)
                    self.slack.chat.post_message(self.get_imid_by_uid(uid), text=f"Searching {msg_tokens[1:]!s}", attachments=None, as_user=True)
            elif msg_tokens[0] == "!구독":
                pass
            elif msg_tokens[0] == "!도움":
                slack_cmd_usage = '''!도움\n!검색 맥북\n=> "맥북" 검색 \n!구독 알바 (미구현)\n=> "알바" 검색 결과 주기적으로 체크, 새로운 글 등록 시 슬랙 메시지'''
                self.slack.im.open(uid)
                self.slack.chat.post_message(self.get_imid_by_uid(uid), text=slack_cmd_usage, attachments=None, as_user=True)

if __name__ == "__main__":
    cat = meerkat()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.get_event_loop().run_until_complete(cat.listen())
    asyncio.get_event_loop().run_forever()
    
    #print(cat.slack.im.list().body)
    #print(cat.slack.users.list().body["members"])
