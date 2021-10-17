import datetime
import json
import os
import time


def get_publisher_list_file_path():
    return f'{os.getcwd()}/data/comics/publishers-{datetime.datetime.now().strftime("%Y-%m")}.json'


def get_publisher_list():
    file_path = get_publisher_list_file_path()
    if os.path.exists(file_path):
        with open(file_path) as json_file:
            return json.load(json_file)
    else:
        return {}


def set_publisher_list(publisher_list: list):
    with open(get_publisher_list_file_path(), 'w+', encoding='utf-8') as json_file:
        return json.dump(publisher_list, json_file)


def check_changes():
    publisher_list = get_publisher_list()
    if not publisher_list:
        print('file empty')
        exit()
    for publisher in publisher_list:
        pass


start_time = time.time()
check_changes()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
