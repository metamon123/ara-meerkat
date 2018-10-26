#! /usr/bin/env python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException
import getpass
from time import sleep

import sqlite3
from db_config import dbname, tablename

# dbname = "./storage/mydb"
# tablename = "records"

class ara_crawler(object):
    url = "https://ara.kaist.ac.kr"

    def __init__(self):
        self.success = False
        chrome_options = Options()
        #chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
        self.driver.implicitly_wait(10)
        self.driver.get(self.url)

        self.get_keywords()
        self.login()
        self.db_init()


    def db_init(self):
        self.db = sqlite3.connect(dbname)

    def login(self):
        self.id = input("id : ").strip()
        self.pw = getpass.getpass("pw : ").strip()

        while not self.try_login(self.id, self.pw):
            print ("login failed")
            self.id = input("id : ").strip()
            self.pw = getpass.getpass("pw : ").strip()

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

    def get_keywords(self, test=False):
        if test:
            self.keywords = ["알바"]
        else:
            self.keywords = [input("keyword : ").strip()]

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

    def crawl(self):
        results = []
        for keyword in self.keywords:
            print(f"searching {{{keyword}}}...")
            posts = self.search_word (keyword, maxpage=2)
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

def summary(new_results):
    final_summaries = [] # "keyword : 3 new items, ..."
    for result in new_results:
        keyword = result["keyword"]
        new_posts = result["new_posts"]
        print('-'*100)
        print(f"New posts about keyword {{{keyword}}}")
        for post in new_posts:
            print("\t" + f"{post['title']}")
            print("\t" + f"{post['good_num']}/{post['bad_num']}/{post['read_num']} {post['date']}")
        print('-'*100)
        final_summaries.append(f"{{ {keyword} }} : {len(new_posts)} new item!")
    print('\n'.join(final_summaries))

if __name__ == "__main__":
    crawler = ara_crawler()
    results = crawler.crawl()
    summary(results)
    input("type enter to quit")
    crawler.bye()













