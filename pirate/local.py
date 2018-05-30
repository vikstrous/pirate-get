import urllib.parse as parse
import base64
import csv

# this is used to remove null bytes from the input stream because
# apparently they exist
def replace_iter(iterable):
    for value in iterable:
        yield value.replace("\0", "")

# https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size#1094933
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)

def search(db, terms):
    with open(db, 'r') as f:
        results = []
        reader = csv.reader(replace_iter(f), delimiter=';')
        for row in reader:
            # skip comments
            if row[0][0] == '#':
                continue
            # 0 is date in rfc 3339 format
            # 1 magnet link hash
            # 2 is title
            # 3 is size in bytes
            if ' '.join(terms).lower() in row[2].lower():
                result = {
                    'date': row[0],
                    'size': sizeof_fmt(int(row[3])),
                    'magnet':
                        'magnet:?xt=urn:btih:' +
                        base64.b16encode(base64.b64decode(row[1])).decode('utf-8') +
                        '&dn=' +
                        parse.quote(row[2]),
                    }
                results.append(result)
        # limit page size to not print walls of results
        # TODO: consider pagination
        results = results[:30]
        return results
