#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException
from getpass import getpass
from time import sleep

import sqlite3, sys
from db_config import dbname, tablename
from config import login_id, login_pw, dp_email

# dbname = "./storage/mydb"
# tablename = "records"

def usage():
    print('Usage: python3 chromecat.py word_to_search1 word_to_search2')
    print('ex) python3 chromecat.py 개발 알바 "맥북  프로"')

class ara_crawler(object):
    url = "https://ara.kaist.ac.kr/"

    def __init__(self, keywords=["알바"], autologin=True):
        self.success = False
        chrome_options = Options()
        chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
        self.driver.implicitly_wait(10)
        self.driver.get(self.url)

        self.keywords = keywords
        self.login(autologin)
        self.db_init()


    def db_init(self):
        self.db = sqlite3.connect(dbname)

    def login(self, autologin):
        if autologin:
            self.id = login_id
            self.pw = login_pw
        else:
            self.id = input("id : ").strip()
            self.pw = getpass("pw : ").strip()

        while not self.try_login(self.id, self.pw):
            if autologin:
                print("autologin failed!")
                self.bye(-1)
            print ("login failed")
            self.id = input("id : ").strip()
            self.pw = getpass("pw : ").strip()

    def try_login(self, id, pw):
        id_field = self.driver.find_element_by_id("araId")
        pw_field = self.driver.find_element_by_id("araPw")
        button = self.driver.find_element_by_id("signinSubmit")

        id_field.clear()
        pw_field.clear()

        id_field.send_keys(id)
        pw_field.send_keys(pw)

        button.click()
        sleep(0.5)
        try:
            alert_box = self.driver.switch_to_alert()
            alert_text = alert_box.text.lower()
            alert_box.accept()
            if "fail" in alert_text:
                return False
            else:
                # weird case
                print ("[Warning] new alert text : " + alert_text)
                return False
        except NoAlertPresentException:
            return True

    # if error -> return (None, None, None) / good -> return (good_num, bad_num, read_num)
    def parse_rec(self, recField): # recField = <td class="recRead"><span class="rec">+8 -0</span> / 350</td>
        text = recField.get_property("innerText") # "+8 -0 / 350"
        lst = text.split() # ["+8", "-0", "/", "350"]
        if len(lst) != 4:
            return (None, None, None)
        return (int(lst[0]), -int(lst[1]), int(lst[3]))

    def search_word(self, word, maxpage=1):
        search_url = "https://ara.kaist.ac.kr/all/search/?search_word={}&chosen_search_method=title|content|author_nickname|author_username&page_no={}"
        selector = "#board_content > table > tbody > tr:nth-child({})" # #board_content > table > tbody > tr:nth-child(2)
        posts = []
        for page in range(1, maxpage + 1):
            self.driver.get(search_url.format(word, page))
            row = 0
            while 1:
                row += 1
                try:
                    content_row = self.driver.find_element_by_css_selector(selector.format(row))
                except NoSuchElementException:
                    break

                aid_field = content_row.find_element_by_css_selector("td.articleid.hidden")
                title_field = content_row.find_element_by_css_selector(".title > a")
                recommend_field = content_row.find_element_by_css_selector(".recRead")
                date_field = content_row.find_element_by_css_selector(".date")

                post = dict()
                post["article_id"] = int(aid_field.get_attribute("rel"))
                post["deleted"] = True if "deleted" in content_row.get_attribute("class") else False
                post["keyword"] = word
                post["title"] = self.driver.execute_script("return arguments[0].childNodes[0].nodeValue.trim()", title_field) # Only contains title (no reply count)
                post["url"] = title_field.get_attribute("href") # /all/12345/?page_no=2
                gn, bn, rn = self.parse_rec(recommend_field)
                if gn == None or bn == None or rn == None:
                    continue
                post["good_num"] = gn
                post["bad_num"] = bn
                post["read_num"] = rn
                post["date"] = date_field.get_property("innerText") # "2018/08/27"

                posts.append(post)

        return posts

    def crawl(self, maxpage=2):
        results = []
        for keyword in self.keywords:
            print(f"searching {{{keyword}}}...")
            posts = self.search_word (keyword, maxpage)
            print("search ended")

            new_posts = []
            cursor = self.db.cursor()

            for post in posts:
                if post["deleted"]:
                    # delete from db || record the fact that post is deleted || neglect
                    continue

                cursor.execute(f'''
                    select * from {tablename} where keyword=? and article_id=?
                ''', (post["keyword"], post["article_id"]))

                not_found = True
                for row in cursor:
                    not_found = False
                    cursor.execute(f'''update {tablename} set title=?, url=?, good_num=?,
                        bad_num=?, read_num=?, date=? where keyword=? and article_id=?''', 
                        (
                            post["title"],
                            post["url"],
                            post["good_num"],
                            post["bad_num"],
                            post["read_num"],
                            post["date"],
                            post["keyword"],
                            post["article_id"]
                        )
                    )

                if not_found:
                    # new data
                    print(f"keyword {post['keyword']} new data!")
                    print(post["title"])
                    new_posts.append(post)
                    cursor.execute(f'''
                        insert into {tablename}(article_id, keyword, title, url, good_num, bad_num, read_num, date)
                        values(?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            post["article_id"],
                            post["keyword"],
                            post["title"],
                            post["url"],
                            post["good_num"],
                            post["bad_num"],
                            post["read_num"],
                            post["date"]
                        )
                    )
            results.append({"keyword" : keyword, "new_posts" : new_posts})
        self.success = True
        return results


    def bye(self):
        # TODO: should be modified (wanna use __del__..)
        if hasattr(self, 'driver'):
            self.driver.quit()
        if hasattr(self, 'db'):
            if self.success:
                print("committing to db...")
                self.db.commit()
            else:
                self.db.rollback()
            self.db.close()
        print("bye :)")
        #super().__del__()

def send_summary(new_results, dm_email="", dm_uid=""):
    final_summaries = [] # "keyword : 3 new posts, ..."
    if dm_uid != "":
        dm_type = "uid"
    elif dm_email != "":
        dm_type = "email"
    else:
        dm_type = "none"

    if dm_type != "none":
        from slackcat import meerkat
        slackcat = meerkat()

    for result in new_results:
        keyword = result["keyword"]
        new_posts = result["new_posts"]
        texts = []
        print('-'*100)
        print(f"New posts about keyword {{{keyword}}}")
        for post in new_posts:
            print("\t" + post['title'])
            print("\t" + f"{ post['good_num'] }/{ post['bad_num'] }/{ post['read_num'] } { post['date'] }")

            if dm_email != "":
                texts.append(f"{ post['title'] }\ngood:{ post['good_num'] } / bad:{ post['bad_num'] }\t{ post['date'] }\n{ post['url'] }")

        print('-'*100)
        final_summaries.append(f"keyword {{ {keyword} }} : {len(new_posts)} new posts!")

        if dm_type != "none":
            msg_attachment = dict()
            msg_attachment["pretext"] = f"keyword {{ {keyword} }} : {len(new_posts)} new posts!"
            msg_attachment["text"] = '\n\n'.join(texts)
            
            if dm_type == "uid":
                success = slackcat.send_dm_by_uid(dm_uid, attachments=[msg_attachment])
            elif dm_type == "email":
                success = slackcat.send_dm_by_email(dm_email, attachments[msg_attachment])
            else:
                assert "Wrong situation" == None

            if success:
                print(f"Notified result successfully")
            else:
                print(f"Failed to notify result")

    print('\n'.join(final_summaries))

def search_and_report(keywords, dm_email="", dm_uid=""):
    crawler = ara_crawler(keywords=keywords)
    results = crawler.crawl(maxpage=1)
    send_summary(results, dm_email=dm_email, dm_uid=dm_uid)
    crawler.bye()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
    else:
        keywords = sys.argv[1:]
        search_and_report(keywords, dm_email=dp_email)












