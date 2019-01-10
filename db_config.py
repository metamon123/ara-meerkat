import sqlite3

dbname = './storage/mydb'
tablename = 'records'

db = sqlite3.connect(dbname)
cursor = db.cursor()
cursor.execute(f'''
    create table if not exists {tablename}
    (
        id integer primary key,
        uid text,
        article_id integer,
        keyword text,
        title text,
        url text,
        good_num integer,
        bad_num integer,
        read_num integer,
        date text
    )
''')
# cf) date : '2018/10/24'

# if you want to clear the db data, just type `echo 'y' | python db_config.py
if __name__ == '__main__':
    if input("wanna drop table? y/n\n").strip().lower() == 'y':
        cursor.execute(f'''drop table if exists {tablename}''')

db.commit()
