#! /usr/bin/env python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import getpass
from time import sleep


def print_response(resp):
    print ("status : {}".format(response.status_code))
    print ("cookies : ", response.cookies)
    print ("text : \n", response.text)
    print ("-" * 100)

base_url = "./"
storage_url = base_url + "storage/" # contents will be stored in server directory OR database.

keyword = input("keyword : ").strip()
login_id = input("id : ").strip()
login_pw = getpass.getpass("pw : ").strip()

main_url = "https://ara.kaist.ac.kr"
chrome_options = Options()
#chrome_options.add_argument("--headless")

d = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
d.implicitly_wait(10)
d.get(main_url)

def login(driver, id, pw):
    id_field = driver.find_element_by_id("araId")
    pw_field = driver.find_element_by_id("araPw")
    button = driver.find_element_by_id("signinSubmit")

    id_field.send_keys(id)
    pw_field.send_keys(pw)

    button.click()
    sleep(0.5)

# if error -> return (None, None, None) / good -> return (good_num, bad_num, read_num)
def parse_rec(recField): # recField = <td class="recRead"><span class="rec">+8 -0</span> / 350</td>
    text = recField.get_property("innerText") # "+8 -0 / 350"
    lst = text.split() # ["+8", "-0", "/", "350"]
    if len(lst) != 4:
        return (None, None, None)
    return (int(lst[0]), int(lst[1]), int(lst[3]))

def search_word(driver, word, maxpage=1):
    '''
    if not driver.current_url.startswith(main_url + "/all"):
        driver.get(main_url + "/all")
        sleep(0.5)
    search_word_field = driver.find_element_by_id("searchText")
    search_button = driver.find_element_by_id("searchButton")

    search_word_field.send_keys(word)
    search_button.click()
    # -> can be replaced with GET https://ara.kaist.ac.kr/all/search/?search_word={}&chosen_search_method=title|content|author_nickname|author_username&page_no={}
    '''

    search_url = "https://ara.kaist.ac.kr/all/search/?search_word={}&chosen_search_method=title|content|author_nickname|author_username&page_no={}"
    selector = "#board_content > table > tbody > tr:nth-child({})" # #board_content > table > tbody > tr:nth-child(2)
    result_list = []
    for page in range(1, maxpage + 1):
        driver.get(search_url.format(word, page))
        row = 0
        while 1:
            row += 1
            try:
                content_row = driver.find_element_by_css_selector(selector.format(row))
            except NoSuchElementException:
                break

            title_field = content_row.find_element_by_css_selector(".title > a")
            recommend_field = content_row.find_element_by_css_selector(".recRead")
            date_field = content_row.find_element_by_css_selector(".date")

            post = dict()
            post["title"] = title_field.get_property("innerText") # 
            post["url"] = title_field.get_attribute("href") # /all/12345/?page_no=2
            gn, bn, rn = parse_rec(recommend_field)
            if gn == None or bn == None or rn == None:
                continue
            post["good_num"] = gn
            post["bad_num"] = bn
            post["read_num"] = rn
            post["date"] = date_field.get_property("innerText") # "2018/08/27"

            result_list.append(post)

    print ("results : ")
    print (result_list)
    print ("-" * 100)



login(d, login_id, login_pw)
search_word(d, keyword)



print ("[Cookie]")
print (d.get_cookies())

input("type enter to quit")
d.quit()








