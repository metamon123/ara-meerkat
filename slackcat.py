from slacker import Slacker
from config import bot_token, dp_email

class meerkat(object):
    def __init__(self):
        self.slack = Slacker(bot_token)
        self.update_lists()

    def update_lists(self):
        self.mems = self.slack.users.list().body["members"]
        self.ims = self.slack.im.list().body["ims"]

    def get_imid_by_email(self, email):
        uid = self.get_userid_by_email(email)
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
        uid = self.get_userid_by_email(email)
        if uid == "":
            return False
        self.slack.im.open(uid)
        self.slack.chat.post_message(self.get_imid_by_email(email), text=text, attachments=attachments, as_user=True)
        return True


if __name__ == "__main__":
    # test for slack api
    cat = meerkat()
    cat.send_dm_by_email(dp_email, "The Events API is a bot's equivalent of eyes and ears.")

#print(slack.im.list().body)
#print(slack.users.list().body["members"])
