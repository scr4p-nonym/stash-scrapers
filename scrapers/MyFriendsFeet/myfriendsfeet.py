"""Public My Friends Feet metadata. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = 'https://www.myfriendsfeet.com'
STUDIO = 'My Friends Feet'
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


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'myfriendsfeet.com', 'www.myfriendsfeet.com'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected a myfriendsfeet.com HTTP(S) URL')
    path = parts.path.rstrip('/')
    match = re.fullmatch(r'/directory/(\d+)/[^/]+/([^/]+)', path)
    if match:
        path = '/directory/' + match[1] + '/all/' + match[2]
    # Affiliate tracking and pagination never belong in an identity URL.
    return urlunsplit(('https', 'www.myfriendsfeet.com', path, '', ''))


def scene_id(url):
    match = re.fullmatch(r'/scenes/(\d+)/[^/]+', urlsplit(canonical(url)).path)
    return match[1] if match else None


def model_url(url):
    return bool(re.fullmatch(r'/directory/\d+/all/[^/]+', urlsplit(url).path))


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                    'Accept': 'text/html'})
    for attempt in range(2):
        try:
            with urlopen(request, timeout=25) as response:
                charset = response.headers.get_content_charset() or 'utf-8'
                return Document(response.read().decode(charset, errors='replace')).root
        except HTTPError as error:
            if attempt or error.code not in {500, 502, 503, 504, 520, 521, 522, 524}:
                raise
            log('Temporary page error; retrying once')


def image_url(value, page_url):
    value = (value or '').strip()
    # The directory emits ///cdn-host/path, which otherwise becomes a local path.
    if value.startswith('//'):
        value = 'https://' + value.lstrip('/')
    url = urljoin(page_url, value)
    if not value or urlsplit(url).scheme not in {'http', 'https'}:
        return None
    return url


def download_images(values, page_url, limit=1):
    images, seen_urls, seen_images = [], set(), set()
    for value in values:
        url = image_url(value, page_url)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                            'Referer': page_url, 'Accept': 'image/*'})
            with urlopen(request, timeout=12) as response:
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError('Image exceeds download limit')
            if data.startswith(b'\xff\xd8\xff'):
                content_type = 'image/jpeg'
            elif data.startswith(b'\x89PNG\r\n\x1a\n'):
                content_type = 'image/png'
            elif data[:6] in (b'GIF87a', b'GIF89a'):
                content_type = 'image/gif'
            elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
                content_type = 'image/webp'
            else:
                raise ValueError('Server returned no supported image')
            encoded = 'data:' + content_type + ';base64,' + base64.b64encode(data).decode('ascii')
            if encoded not in seen_images:
                seen_images.add(encoded)
                images.append(encoded)
            if len(images) >= limit:
                break
        except Exception as error:
            log('Optional image unavailable: ' + str(error))
    return images


def readable(node):
    if node.tag in {'script', 'style'}:
        return ''
    if node.tag == 'br':
        return '\n'
    text = ''.join(readable(c) if isinstance(c, Node) else c for c in node.children)
    return '\n\n' + text + '\n\n' if node.tag in {'p', 'div'} else text


def description(node):
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(clean(line) for line in readable(node).splitlines())).strip()


def person_data(root):
    def find_person(value):
        if isinstance(value, list):
            return next((p for item in value if (p := find_person(item))), None)
        if isinstance(value, dict):
            types = value.get('@type', [])
            if types == 'Person' or isinstance(types, list) and 'Person' in types:
                return value
            return find_person(value.get('@graph', [])) if '@graph' in value else None
        return None
    for script in root.all(lambda n: n.tag == 'script' and n.attrs.get('type') == 'application/ld+json'):
        try:
            person = find_person(json.loads(script.text()))
            if person:
                return person
        except (ValueError, TypeError):
            continue
    return {}


def performer(url, multiple_images=True):
    url = canonical(url)
    if not model_url(url):
        raise ValueError('Use an individual /directory/ model URL')
    root = fetch(url)
    data = person_data(root)
    heading = root.first(lambda n: n.has_class('section-heading'))
    name = clean(data.get('name') or re.sub(r'\s+-\s+Page\s+\d+$', '', heading.text() if heading else ''))
    if not name:
        raise ValueError('Model name not found')
    result = {'name': name, 'urls': [url], 'gender': 'Male', 'disambiguation': STUDIO}
    candidates = []
    for card in root.all(lambda n: n.has_class('thumbs-result')):
        image = card.first(lambda n: n.tag == 'img')
        if image:
            candidates.append(image.attrs.get('data-src') or image.attrs.get('src'))
        if len(candidates) >= 8:
            break
    if isinstance(data.get('image'), str):
        candidates.append(data['image'])
    images = download_images(candidates, url, limit=8 if multiple_images else 1)
    if images:
        result['images'] = images
    return result


def listed_date(root, target):
    for card in root.all(lambda n: n.has_class('scene-thumbnail')):
        matches = False
        for anchor in card.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                if scene_id(anchor.attrs['href']) == target:
                    matches = True
                    break
            except ValueError:
                continue
        if not matches:
            continue
        date = card.first(lambda n: n.has_class('scene-thumbnail-info-date'))
        if date:
            value = date.attrs.get('title', '').strip()[:10]
            try:
                return datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                try:
                    return datetime.strptime(clean(date.text()), '%b %d, %Y').strftime('%Y-%m-%d')
                except ValueError:
                    pass
    return None


def publication_date(root, url):
    target = scene_id(url)
    for node in root.all(lambda n: n.tag == 'meta' and n.attrs.get('property') == 'article:published_time'):
        try:
            return datetime.strptime(node.attrs.get('content', '')[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            continue
    date = listed_date(root, target)
    if date:
        return date
    # Some public scenes expose their date only on another scene's related card.
    related = []
    for card in root.all(lambda n: n.has_class('scene-thumbnail')):
        anchor = card.first(lambda n: n.tag == 'a' and n.attrs.get('href'))
        if not anchor:
            continue
        try:
            other = canonical(anchor.attrs['href'])
            if scene_id(other) and scene_id(other) != target and other not in related:
                related.append(other)
        except ValueError:
            continue
        if len(related) == 2:
            break
    for other in related:
        try:
            date = listed_date(fetch(other), target)
            if date:
                return date
        except Exception as error:
            log('Optional publication-date lookup unavailable: ' + str(error))
    return None


def scene(url):
    url = canonical(url)
    if not scene_id(url):
        raise ValueError('Use an individual /scenes/ URL')
    root = fetch(url)
    heading = root.first(lambda n: n.tag == 'h1' and n.has_class('mb'))
    if heading is None or not clean(heading.text()):
        raise ValueError('Scene title not found')
    result = {'title': clean(heading.text()), 'urls': [url],
              'studio': {'name': STUDIO, 'urls': [BASE + '/']}}
    paragraphs, cast, seen = [], [], set()
    for paragraph in root.all(lambda n: n.tag == 'p' and n.has_class('desc')):
        links = []
        for anchor in paragraph.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                model = canonical(anchor.attrs['href'])
                if model_url(model):
                    links.append((anchor, model))
            except ValueError:
                continue
        if not links:
            text = description(paragraph)
            if text:
                paragraphs.append(text)
        for anchor, model in links:
            if model in seen:
                continue
            seen.add(model)
            name = clean(re.sub(r'\s*Model\s+Directory\s*$', '', anchor.text(), flags=re.I))
            if not name:
                continue
            person = {'name': name, 'urls': [model], 'gender': 'Male', 'disambiguation': STUDIO}
            try:
                person = performer(model, multiple_images=False)
            except Exception as error:
                log('Profile unavailable; keeping credited name and URL: ' + str(error))
            cast.append(person)
    if paragraphs:
        result['details'] = '\n\n'.join(paragraphs)
    if cast:
        result['performers'] = cast
    candidates = [n.attrs.get('content') for n in root.all(
        lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:image')]
    images = download_images(candidates, url)
    if images:
        result['image'] = images[0]
    date = publication_date(root, url)
    if date:
        result['date'] = date
    return result


def main():
    try:
        data = json.load(sys.stdin)
        action = sys.argv[1]
        if action == 'scene':
            result = scene(data['url'])
        elif action == 'performer':
            result = performer(data['url'])
        else:
            raise ValueError('Unknown scraper action')
        print(json.dumps(result, ensure_ascii=True))
    except Exception as error:
        log(str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()

