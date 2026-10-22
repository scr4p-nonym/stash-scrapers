"""Public Island Studs metadata. Python standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://www.islandstuds.com'
STUDIO = 'Island Studs'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def has_class(self, name):
        return name in (self.attrs.get('class') or '').split()

    def all(self, predicate):
        for child in self.children:
            if isinstance(child, Node):
                if predicate(child):
                    yield child
                yield from child.all(predicate)

    def first(self, predicate):
        return next(self.all(predicate), None)

    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def clean(text):
    return re.sub(r'\s+', ' ', text).strip()


def log(message):
    print(STUDIO + ': ' + message, file=sys.stderr)


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                    'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return Document(response.read().decode(charset, errors='replace')).root


def optional_portrait(root, profile_url):
    """Capture signed portraits immediately; an image failure is nonfatal."""
    image = cover(root)
    if not image:
        return None
    try:
        request = Request(image, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
            'Referer': profile_url, 'Accept': 'image/*'})
        with urlopen(request, timeout=15) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith('image/'):
                log('Skipping portrait: server did not return an image')
                return None
            data = response.read()
        return 'data:' + content_type + ';base64,' + base64.b64encode(data).decode('ascii')
    except Exception as error:
        log('Portrait unavailable; keeping performer metadata: ' + str(error))
        return None


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'islandstuds.com', 'www.islandstuds.com'}:
        raise ValueError('Expected an islandstuds.com URL')
    if parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected an HTTP(S) URL')
    return urlunsplit(('https', 'www.islandstuds.com', parts.path, '', ''))


def meta(root, property_name):
    node = root.first(lambda n: n.tag == 'meta' and n.attrs.get('property') == property_name)
    return node.attrs.get('content', '').strip() if node else ''


def cover(root):
    portrait = root.first(lambda n: n.tag == 'img' and n.has_class('model_bio_thumb'))
    if portrait:
        # Island Studs uses src0_1x/src0_2x/src0_3x instead of normal src.
        variants = [(int(match[1]), value) for key, value in portrait.attrs.items()
                    if (match := re.fullmatch(r'src0_(\d+)x', key)) and value]
        url = max(variants)[1] if variants else portrait.attrs.get('src')
        return urljoin(BASE, url) if url else None
    url = meta(root, 'og:image')
    return urljoin(BASE, url) if url else None


def readable_text(node):
    if node.tag in {'script', 'style'} or node.has_class('rating_text') or node.has_class('rating_box'):
        return ''
    if node.tag == 'br':
        return '\n'
    value = ''.join(readable_text(c) if isinstance(c, Node) else c for c in node.children)
    return '\n\n' + value + '\n\n' if node.tag in {'p', 'div'} else value


def description(node):
    if node is None:
        return ''
    text = readable_text(node).replace('\r', '')
    text = '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def performer(url):
    url = canonical(url)
    if not re.fullmatch(r'/tour/models/[^/]+\.html', urlsplit(url).path) or url.endswith('/models.html'):
        raise ValueError('Use an individual model profile URL')
    root = fetch(url)
    heading = root.first(lambda n: n.has_class('title_bar_hilite'))
    if heading is None or not clean(heading.text()):
        raise ValueError('Model name was not found on this page')
    result = {'name': clean(heading.text()), 'urls': [url], 'gender': 'Male',
              'disambiguation': STUDIO}
    bio = description(root.first(lambda n: n.has_class('model_bio')))
    if bio:
        result['details'] = bio
    image = optional_portrait(root, url)
    if image:
        result['images'] = [image]
    return result


def scene(url):
    url = canonical(url)
    if not re.fullmatch(r'/tour/scenes/[^/]+\.html', urlsplit(url).path):
        raise ValueError('Use an individual scene URL')
    root = fetch(url)
    heading = root.first(lambda n: n.has_class('set-title'))
    name = clean(heading.text()) if heading else meta(root, 'og:title')
    if not name:
        raise ValueError('Scene title was not found on this page')
    result = {'title': name, 'urls': [url],
              'studio': {'name': STUDIO, 'urls': [BASE + '/']}}
    text = description(root.first(lambda n: n.has_class('update_description')))
    if text:
        result['details'] = text
    image = cover(root)
    if image:
        result['image'] = image
    date_node = root.first(lambda n: n.has_class('update_date'))
    if date_node:
        match = re.search(r'\b\d{1,2}/\d{1,2}/\d{4}\b', date_node.text())
        if match:
            try:
                result['date'] = datetime.strptime(match[0], '%m/%d/%Y').strftime('%Y-%m-%d')
            except ValueError:
                log('Invalid publication date; leaving it empty')
    # Scope to the main Featuring block; later blocks belong to recommendations.
    cast = root.first(lambda n: n.has_class('update_models'))
    performers, seen = [], set()
    if cast:
        for anchor in cast.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                model_url = canonical(anchor.attrs['href'])
                if not re.fullmatch(r'/tour/models/[^/]+\.html', urlsplit(model_url).path):
                    continue
                if model_url in seen:
                    continue
                seen.add(model_url)
                model = {'name': clean(anchor.text()), 'urls': [model_url],
                         'gender': 'Male', 'disambiguation': STUDIO}
                if not model['name']:
                    continue
                try:
                    model = performer(model_url)
                except Exception as error:
                    log('Profile unavailable; keeping the credited performer: ' + str(error))
                performers.append(model)
            except ValueError:
                continue
    if performers:
        result['performers'] = performers
    return result


def main():
    try:
        data = json.load(sys.stdin)
        action = sys.argv[1]
        result = scene(data['url']) if action == 'scene' else performer(data['url']) if action == 'performer' else None
        if result is None:
            raise ValueError('Unknown scraper action')
        print(json.dumps(result, ensure_ascii=True))
    except Exception as error:
        log(str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
