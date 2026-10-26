"""Public All Australian Boys metadata. Standard library only. AGPL-3.0."""
import base64
from html import unescape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://www.allaustralianboys.com'
STUDIO = 'All Australian Boys'
PROFILE = r'/(sex-scenes|solos)_([A-Za-z0-9_-]+)\.php'
VIDEO = r'/video-[A-Za-z0-9_-]+\.php'
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
        # Known public template typo: <h3 class="title"Kane</h3>.
        # Repair that missing delimiter without inventing a name from the URL.
        html = re.sub(r'(<h3\b[^>]*\bclass=["\']title["\'])([^<>\s][^<>]*)(</h3\s*>)',
                      r'\1>\2\3', html, flags=re.I)
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
    parts = urlsplit(url)
    if parts.hostname in {'allaustralianboys.com', 'www.allaustralianboys.com'}:
        url = urlunsplit(('https', 'www.allaustralianboys.com', parts.path, parts.query, ''))
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


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'allaustralianboys.com', 'www.allaustralianboys.com'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected an allaustralianboys.com HTTP(S) URL')
    return urlunsplit(('https', 'www.allaustralianboys.com', parts.path, '', ''))


def decode_html(data, charset=None):
    if not charset:
        declared = re.search(br'charset=["\']?\s*([A-Za-z0-9_-]+)', data[:4096], re.I)
        charset = declared[1].decode('ascii') if declared else 'utf-8'
    if charset.lower().replace('-', '') in {'utf8', 'utf_8'}:
        # Some legacy previews mix UTF-8 with Windows-1252 curly quotes.
        text = data.decode('utf-8', errors='surrogateescape')
        return ''.join(bytes([ord(c) - 0xdc00]).decode('cp1252', errors='replace')
                       if 0xdc80 <= ord(c) <= 0xdcff else c for c in text)
    if charset.lower() in {'iso-8859-1', 'latin-1', 'latin1'}:
        charset = 'cp1252'
    try:
        return data.decode(charset, errors='replace')
    except LookupError:
        return data.decode('utf-8', errors='replace')


def site_index():
    try:
        data = json.loads(Path(__file__).with_name('site_index.json').read_text(encoding='utf-8'))
        if isinstance(data.get('profiles'), dict) and isinstance(data.get('videos'), dict):
            return data
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return {'profiles': {}, 'videos': {}}


def fetch(url):
    url = canonical(url)
    if not (re.fullmatch(PROFILE, urlsplit(url).path) or re.fullmatch(VIDEO, urlsplit(url).path)):
        raise ValueError('Expected an individual public preview/profile URL')
    cache = None
    try:
        cache = Path(tempfile.gettempdir()) / 'stash-allaustralianboys-cache-v1'
        cache.mkdir(exist_ok=True)
        cache = cache / (hashlib.sha256(url.encode()).hexdigest() + '.html')
        if cache.exists() and time.time() - cache.stat().st_mtime < 6 * 3600:
            return Document(cache.read_text(encoding='utf-8')).root
    except OSError:
        cache = None
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)', 'Accept': 'text/html'})
    with urlopen(req, timeout=25) as response:
        if canonical(response.url) != url:
            raise ValueError('Public page redirected elsewhere')
        html = response.read(4 * 1024 * 1024 + 1)
        if len(html) > 4 * 1024 * 1024:
            raise ValueError('Page exceeds download limit')
        html = decode_html(html, response.headers.get_content_charset())
    if cache:
        try:
            cache.write_bytes(html.encode('utf-8'))
        except OSError:
            pass
    return Document(html).root


def profile_data(root, url):
    """Retain the displayed name and exact URL code as separate values."""
    match = re.fullmatch(PROFILE, urlsplit(url).path)
    heading = root.first(lambda n: n.tag == 'h3' and n.has_class('title'))
    article = root.first(lambda n: n.tag == 'article')
    name = clean(heading.text()) if heading else ''
    if not match or not name or len(name) > 80 or re.search(r'Join Now|\b(?:Age|Height|Weight|Sports):', name, re.I) or not article:
        raise ValueError('No individual public model preview found')
    player = root.first(lambda n: n.tag == 'p' and n.has_class('player'))
    videos = []
    if player:
        for a in player.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                target = canonical(a.attrs['href'])
                if re.fullmatch(VIDEO, urlsplit(target).path) and target not in videos:
                    videos.append(target)
            except ValueError:
                pass
    image = player.first(lambda n: n.tag == 'img' and n.attrs.get('src')) if player else None
    stats = root.first(lambda n: n.has_class('stats'))
    names = [clean(value) for value in re.split(r'\s*&\s*|\s+and\s+', name, flags=re.I) if clean(value)]
    return {'url': url, 'name': name, 'names': names, 'code': match[2],
            'kind': 'Solo' if match[1] == 'solos' else 'Sex Scene',
            'details': description(article), 'cover': image_url(image.attrs['src'], url) if image else None,
            'videos': videos, 'stats': description(stats) if stats else ''}


def resolve_profile(url):
    url = canonical(url)
    if re.fullmatch(PROFILE, urlsplit(url).path):
        return profile_data(fetch(url), url)
    if not re.fullmatch(VIDEO, urlsplit(url).path):
        raise ValueError('Use an individual preview/profile or teaser URL')
    index = site_index()
    if url in index.get('ambiguous_videos', []):
        raise ValueError('This teaser is shared by different previews; use the individual sex-scenes_ or solos_ URL')
    candidates = [index['videos'][url]] if url in index['videos'] else []
    # The video title is only an internal code. Verify a candidate's exact
    # player link before using its human name or description.
    code = re.fullmatch(r'/video-(.+?)(?:-sexscene|-solo)?\.php', urlsplit(url).path)[1]
    candidates.extend(BASE + '/' + kind + '_' + code + '.php' for kind in ('sex-scenes', 'solos'))
    seen = set()
    matches = []
    for target in candidates:
        if target in seen:
            continue
        seen.add(target)
        try:
            record = profile_data(fetch(target), target)
            if url in record['videos']:
                if index['videos'].get(url) == target:
                    return record
                matches.append(record)
        except Exception as error:
            log('Optional teaser-to-preview lookup unavailable: ' + str(error))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError('This teaser is shared by different previews; use the individual preview URL')
    raise ValueError('No public preview explicitly links to this teaser URL')


def model(record, images=True, name=None):
    result = {'name': name or record['name'], 'gender': 'Male',
              'disambiguation': STUDIO + ' (' + record['code'] + ')', 'urls': [record['url']]}
    if len(record['names']) > 1:
        # Shared group portraits, measurements and prose are not individual bios.
        return result
    if record.get('details'):
        result['details'] = record['details']
    # A shoot age does not establish a birthdate.
    for label, field, unit in [('Height', 'height', 'cm'), ('Weight', 'weight', 'kg')]:
        match = re.search(r'\b' + label + r':\s*(\d+(?:\.\d+)?)\s*' + unit + r's?\b', record.get('stats', ''), re.I)
        if match:
            result[field] = match[1]
    portrait = site_index()['profiles'].get(record['url'], {}).get('portrait')
    if images:
        values = download_images([u for u in [portrait, record.get('cover')] if u], record['url'])
        if values:
            result['images'] = values
    return result


def scene(url):
    record = resolve_profile(url)
    ambiguous = site_index().get('ambiguous_videos', [])
    result = {'title': record['name'] + ' [' + record['code'] + '] — ' + record['kind'],
              'details': record['details'], 'urls': [record['url']] + [v for v in record['videos'] if v not in ambiguous],
              'studio': {'name': STUDIO, 'urls': [BASE + '/']},
              'performers': [model(record, name=name) for name in record['names']]}
    images = download_images([record['cover']] if record['cover'] else [], record['url'])
    if images:
        result['image'] = images[0]
    # These public previews have no reliable release dates. Do not infer one
    # from an image timestamp, model's age, site copyright, or HTTP Last-Modified.
    return result


def performer(url):
    url = canonical(url)
    if not re.fullmatch(PROFILE, urlsplit(url).path):
        raise ValueError('Use the individual public model preview URL')
    record = profile_data(fetch(url), url)
    if len(record['names']) != 1:
        raise ValueError('This preview credits multiple models; scrape it as a scene instead')
    return model(record)


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


