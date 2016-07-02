import urllib.parse as parse
import html.parser as parser


class BayParser(parser.HTMLParser):
    title = ''
    q = ''
    state = 'looking'
    results = []

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.state = 'title'
        if tag == 'magnet' and self.state == 'matched':
            self.state = 'magnet'

    def handle_data(self, data):
        if self.state == 'title':
            if data.lower().find(self.q) != -1:
                self.title = data
                self.state = 'matched'
            else:
                self.state = 'looking'
        if self.state == 'magnet':
            self.results.append([
                'magnet:?xt=urn:btih:' +
                parse.quote(data) +
                '&dn=' +
                parse.quote(self.title), '?', '?'])
            self.state = 'looking'


def search(db, terms):
    f = open(db)
    xml = f.readlines()
    f.close()
    parser = BayParser()
    parser.q = (' '.join(terms)).lower()
    parser.feed(''.join(xml))
    return parser.results
