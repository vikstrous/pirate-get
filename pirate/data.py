import json

categories = json.load(open('data/categories.json'))
sorts = json.load(open('data/sorts.json'))

default_headers = {'User-Agent': 'pirate get'}
default_timeout = 10
colored_output = True
