"""Public UK Naked Men metadata for Stash. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs, urlencode
from urllib.request import Request, urlopen

BASE = 'https://www.uknakedmen.com/tour/'
STUDIO = 'UK Naked Men'
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


def canonical(url, kind):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or parts.hostname not in {'uknakedmen.com', 'www.uknakedmen.com'}:
        raise ValueError('Expected a UK Naked Men HTTP(S) URL')
    query = parse_qs(parts.query)
    lid = ''
    if parts.path == '/tour/refstat.php':
        lid = query.get('lid', [''])[0]
    elif parts.path == '/tour/showgal.php':
        group = query.get('g', [''])[0]
        match = re.fullmatch(r'(?:content/.+|groups)/(\d+)/\d+_\d+', group)
        if match:
            lid = match[1]
    if not lid.isdigit():
        raise ValueError('Use an individual video/model link from the public tour, not a directory')
    return BASE + 'refstat.php?' + urlencode({'lid': lid, 'sid': '669' if kind == 'scene' else '670'})


def fetch(url, kind):
    from urllib.request import HTTPRedirectHandler, build_opener

    class PublicRedirects(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            parts = urlsplit(newurl)
            if (parts.scheme not in {'http', 'https'} or parts.hostname not in {'uknakedmen.com', 'www.uknakedmen.com'}
                    or parts.path not in {'/tour/refstat.php', '/tour/showgal.php'}):
                raise ValueError('Link redirected outside an individual public tour page')
            if canonical(newurl, kind) != url:
                raise ValueError('Link redirected to a different item')
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)', 'Accept': 'text/html'})
    with build_opener(PublicRedirects()).open(request, timeout=25) as response:
        if canonical(response.url, kind) != url:
            raise ValueError('Response identity differs from requested item')
        data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('Page exceeds download limit')
        return Document(data.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')).root


def visible_text(node):
    if isinstance(node, str):
        return '' if 'Rate this model:' in node else node
    if node.tag in {'script', 'style', 'noscript', 'form'} or node.has_class('star-rating'):
        return ''
    if node.tag == 'br':
        return '\n'
    value = ''.join(visible_text(c) for c in node.children)
    return value + ('\n\n' if node.tag == 'p' else '')


def scene(url):
    url = canonical(url, 'scene')
    root = fetch(url, 'scene')
    sections = list(root.all(lambda n: n.has_class('videonewinfo')))
    heading = next((h for section in sections for h in section.all(lambda n: n.tag in {'h1', 'h2'})), None)
    player = root.first(lambda n: n.tag == 'script' and 'jwplayer(' in n.text() and 'videoPlayer' in n.text())
    if heading is None or player is None:
        raise ValueError('This is not an individual public video page; use its model link on a performer')
    name = clean(heading.text())
    if not name:
        raise ValueError('Scene title missing')
    result = {'title': name, 'urls': [url], 'studio': {'name': STUDIO}}
    details = []
    for section in sections:
        for p in section.all(lambda n: n.tag == 'p'):
            value = visible_text(p).strip()
            if value:
                details.append(value)
    if details:
        result['details'] = '\n\n'.join(details)
    # Use only the main player's declared still poster. Never fetch trailer media.
    match = re.search(r'\bimage\s*:\s*[\'"]([^\'"]+)[\'"]', player.text())
    candidates = [urljoin(BASE, match[1])] if match else []
    faceimage = root.first(lambda n: n.tag == 'img' and n.attrs.get('id') == 'scene_faceimage')
    if faceimage and faceimage.attrs.get('src'):
        candidates.append(urljoin(BASE, faceimage.attrs['src']))
    if candidates:
        images = download_images(candidates, url)
        if images:
            result['image'] = images[0]
    # Public pages inspected have no release date or explicit cast profile links.
    return result


def performer(url):
    url = canonical(url, 'performer')
    root = fetch(url, 'performer')
    info = root.first(lambda n: n.has_class('modelinfo'))
    heading = info.first(lambda n: n.tag in {'h1', 'h2'}) if info else None
    if heading is None:
        raise ValueError('This is not an individual public model page; use its video link on a scene')
    name = clean(heading.text())
    if not name:
        raise ValueError('Model name missing')
    result = {'name': name, 'urls': [url], 'gender': 'Male', 'disambiguation': STUDIO}
    # Extract biography only; rating controls and filmography are separate content.
    body = ''.join(visible_text(c) for c in info.children if not (isinstance(c, Node) and c is heading))
    lines = [clean(line) for line in body.splitlines() if clean(line)]
    if lines:
        result['details'] = '\n\n'.join(lines)
    picture = root.first(lambda n: n.has_class('modelpic'))
    img = picture.first(lambda n: n.tag == 'img') if picture else None
    if img and img.attrs.get('src'):
        images = download_images([urljoin(BASE, img.attrs['src'])], url)
        if images:
            result['images'] = images
    return result


if __name__ == '__main__':
    try:
        args = json.load(sys.stdin)
        if len(sys.argv) != 2 or sys.argv[1] not in {'scene', 'performer'}:
            raise ValueError('Expected scene or performer operation')
        handler = scene if sys.argv[1] == 'scene' else performer
        print(json.dumps(handler(args.get('url', '')), ensure_ascii=False))
    except Exception as error:
        log(str(error))
        print('null')
        sys.exit(1)


