"""Public Beefcake Hunter metadata. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import unicodedata
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://beefcakehunter.com'
STUDIO = 'Beefcake Hunter'
VICTOR = {'name': 'Victor', 'disambiguation': STUDIO, 'gender': 'Male',
          'urls': [BASE + '/about-the-hunter/',
                   'https://stashdb.org/performers/cc7e6bb9-6140-41da-a748-7d306c8a31c6']}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


def site_index():
    try:
        data = json.loads(Path(__file__).with_name('site_index.json').read_text(encoding='utf-8'))
        if isinstance(data.get('scenes'), dict) and isinstance(data.get('performers'), dict):
            return data
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return {'scenes': {}, 'performers': {}}


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


def image_url(value, page_url):
    value = (value or '').strip()
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
    if node.tag == 'li':
        return '\n- ' + text + '\n'
    return '\n\n' + text + '\n\n' if node.tag in {'p', 'div', 'h1', 'h2', 'h3', 'h4'} else text


def description(node):
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(clean(line) for line in readable(node).splitlines())).strip()


def schema_entries(root):
    def walk(value):
        if isinstance(value, list):
            for child in value:
                yield from walk(child)
        elif isinstance(value, dict):
            yield value
            if '@graph' in value:
                yield from walk(value['@graph'])
    for script in root.all(lambda n: n.tag == 'script' and n.attrs.get('type') == 'application/ld+json'):
        try:
            yield from walk(json.loads(script.text()))
        except (ValueError, TypeError):
            continue


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'beefcakehunter.com', 'www.beefcakehunter.com'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected a beefcakehunter.com HTTP(S) URL')
    return urlunsplit(('https', 'beefcakehunter.com', parts.path.rstrip('/') + '/', '', ''))


def fetch(url):
    url = canonical(url)
    path = urlsplit(url).path
    if not (re.fullmatch(r'/video/[^/]+/', path) or
            re.fullmatch(r'/video-category/[^/]+/(?:page/\d+/)?', path) or path == '/about-the-hunter/'):
        raise ValueError('Expected an individual scene or performer category')
    cache = None
    try:
        cache = Path(tempfile.gettempdir()) / 'stash-beefcakehunter-cache-v1'
        cache.mkdir(exist_ok=True)
        cache = cache / (hashlib.sha256(url.encode()).hexdigest() + '.html')
        if cache.exists() and time.time() - cache.stat().st_mtime < 6 * 3600:
            return Document(cache.read_text(encoding='utf-8')).root
    except OSError:
        cache = None
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)', 'Accept': 'text/html'})
    with urlopen(req, timeout=25) as response:
        if canonical(response.url) != url:
            raise ValueError('Page redirected away from public metadata')
        html = response.read(4 * 1024 * 1024 + 1)
        if len(html) > 4 * 1024 * 1024:
            raise ValueError('Page exceeds download limit')
        html = html.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
    if cache:
        try:
            cache.write_bytes(html.encode('utf-8'))
        except OSError:
            pass
    return Document(html).root


def date_value(value):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y'):
        try:
            return datetime.strptime(clean(value)[:10] if fmt == '%Y-%m-%d' else clean(value), fmt).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pass
    return None


def category_name(root, url):
    for item in schema_entries(root):
        if item.get('@type') == 'CollectionPage' and canonical(item.get('url', url)) == canonical(url).split('/page/')[0].rstrip('/') + '/':
            return clean(unescape(re.sub(r'\s*[-–—]\s*Beef\s*Cake\s*Hunter\s*$', '', item.get('name', ''), flags=re.I)))
    return None


def listing(root):
    """Only main category cards, excluding recommendations/footer links."""
    for heading in root.all(lambda n: n.has_class('t7-video-title')):
        anchor = heading.first(lambda n: n.tag == 'a' and n.attrs.get('href'))
        if anchor:
            try:
                url = canonical(anchor.attrs['href'])
            except ValueError:
                continue
            if re.fullmatch(r'/video/[^/]+/', urlsplit(url).path):
                yield url, clean(anchor.text())


def next_page(root, url):
    path = urlsplit(url).path.split('/page/')[0].rstrip('/') + '/'
    current = re.search(r'/page/(\d+)/', url)
    wanted = int(current[1]) + 1 if current else 2
    target = BASE + path + 'page/' + str(wanted) + '/'
    return target if any(canonical(a.attrs['href']) == target for a in root.all(
        lambda n: n.tag == 'a' and n.attrs.get('href', '').startswith(BASE + path))) else None


def model_result(name, url):
    result = {'name': name, 'gender': 'Male', 'disambiguation': STUDIO, 'urls': [url]}
    portrait = site_index()['performers'].get(url, {})
    if portrait.get('name') == name and portrait.get('image'):
        images = download_images([portrait['image']], url)
        if images:
            result['images'] = images
    return result


def performer(url):
    url = canonical(url)
    if url == BASE + '/about-the-hunter/':
        return dict(VICTOR)
    if not re.fullmatch(r'/video-category/[^/]+/', urlsplit(url).path):
        raise ValueError('Expected an individual performer category URL')
    root = fetch(url)
    name = category_name(root, url)
    if not name or not list(listing(root)) or name.casefold() in {
            'oral', 'anal', 'solo', 'glory hole', 'latino', 'black', 'white', 'asian',
            'european', 'arabic', 'mixed', 'keywords', 'categories'}:
        raise ValueError('This category is not an individual model profile')
    return model_result(name, url)


def key(value):
    return re.sub(r'[^a-z0-9]+', '', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().casefold())


def cast(content, scene_url):
    # Snapshot entries come from an explicit model card joined to its exact scene
    # URL or a unique exact listing title, never from story character mentions.
    indexed = site_index()['scenes'].get(scene_url)
    if indexed:
        for item in indexed:
            yield model_result(item['name'], item['url'])
        return
    names = []
    for a in content.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
        try:
            target = canonical(a.attrs['href'])
        except ValueError:
            continue
        if target != BASE + '/beefcakes/':
            continue
        label = clean(a.text())
        match = re.fullmatch(r'Beefcake\s+(.+?)(?:[’\']s)?', label, re.I)
        if match:
            name = match[1].strip()
            if 1 <= len(name.split()) <= 3 and key(name) not in {key(n) for n in names}:
                names.append(name)
    for name in names[:6]:
        slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().casefold()).strip('-')
        url = BASE + '/video-category/' + slug + '/'
        try:
            page_url = url
            for _ in range(20):
                root = fetch(page_url)
                if key(category_name(root, page_url) or '') != key(name):
                    break
                if scene_url in {u for u, _ in listing(root)}:
                    yield model_result(category_name(root, page_url), url)
                    break
                page_url = next_page(root, page_url)
                if not page_url:
                    break
        except Exception as error:
            log('Optional verified guest credit unavailable: ' + str(error))


def scene(url):
    url = canonical(url)
    if not re.fullmatch(r'/video/[^/]+/', urlsplit(url).path):
        raise ValueError('Expected an individual /video/ scene URL')
    root = fetch(url)
    title = root.first(lambda n: n.has_class('sunday-funday-video-title'))
    content = root.first(lambda n: n.has_class('t7-video-content'))
    if not title or not clean(title.text()) or not content:
        raise ValueError('Public scene metadata unavailable; no login required by this scraper')
    result = {'title': clean(title.text()), 'details': description(content), 'urls': [url],
              'studio': {'name': STUDIO, 'urls': [BASE + '/']},
              'performers': [dict(VICTOR)] + list(cast(content, url))}
    date = root.first(lambda n: n.has_class('video-ui-date'))
    values = [date.text()] if date else []
    values.extend(n.attrs.get('content', '') for n in root.all(
        lambda n: n.tag == 'meta' and n.attrs.get('property') == 'article:published_time'))
    values.extend(item.get('datePublished', '') for item in schema_entries(root)
                  if item.get('@type') in {'WebPage', 'Article', 'VideoObject'})
    for value in values:
        parsed = date_value(value)
        if parsed:
            result['date'] = parsed
            break
    covers = [n.attrs['poster'] for n in root.all(lambda n: n.tag == 'video' and n.attrs.get('poster'))]
    covers.extend(item['image']['url'] for item in schema_entries(root)
                  if item.get('@type') == 'WebPage' and isinstance(item.get('image'), dict) and item['image'].get('url'))
    images = download_images(covers, url)
    if images:
        result['image'] = images[0]
    return result


def main():
    try:
        data = json.load(sys.stdin)
        action = {'scene': scene, 'performer': performer}.get(sys.argv[1])
        if not action:
            raise ValueError('Unknown scraper action')
        print(json.dumps(action(data['url']), ensure_ascii=True))
    except Exception as error:
        log(str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()


