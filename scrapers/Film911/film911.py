"""Public Film911 metadata. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://film911.net'
STUDIO = 'Film911'
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
    if node.tag == 'li':
        return '\n- ' + text + '\n'
    return '\n\n' + text + '\n\n' if node.tag in {'p', 'div', 'h1', 'h2', 'h3', 'h4'} else text


def description(node):
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(clean(line) for line in readable(node).splitlines())).strip()


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'film911.net', 'www.film911.net'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected a film911.net HTTP(S) URL')
    return urlunsplit(('https', 'film911.net', parts.path.rstrip('/') + '/', '', ''))


def fetch(url):
    def request(target):
        req = Request(target, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                       'Accept': 'text/html'})
        with urlopen(req, timeout=25) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return Document(response.read().decode(charset, errors='replace')).root
    root = request(url)
    if root.first(lambda n: n.tag == 'a' and 'ao_confirm' in n.attrs.get('href', '')):
        # Use the site's normal public entry view; keep it out of the identity URL.
        root = request(url + '?ao_confirm')
    return root


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


def clean_title(value):
    value = clean(unescape(value))
    while True:
        stripped = re.sub(r'\s*\((?:review|demo available|trailer available)\)\s*$', '', value, flags=re.I)
        stripped = re.sub(r'\s*[-–—:]\s*(?:all new|coming soon)\s*$', '', stripped, flags=re.I)
        if stripped == value:
            return value
        value = stripped.strip()


def has_type(item, types):
    value = item.get('@type', [])
    return value in types if isinstance(value, str) else any(t in types for t in value)


def release_date(title, url, entries, root):
    # Only fully specified, explicitly announced dates take precedence over post dates.
    for value in (title, urlsplit(url).path):
        match = re.search(r'\bcoming[\s:–—-]+(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})(?!\d)', value, re.I)
        if match:
            year = int(match[3])
            if year < 100:
                year += 2000
            try:
                return datetime(year, int(match[1]), int(match[2])).strftime('%Y-%m-%d')
            except ValueError:
                continue
    values = [item.get('datePublished', '') for item in entries if has_type(item, {'Article', 'WebPage', 'VideoObject'})]
    values.extend(n.attrs.get('content', '') for n in root.all(
        lambda n: n.tag == 'meta' and n.attrs.get('property') == 'article:published_time'))
    for value in values:
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            continue
    return None


def purchase_links(scope, page_url):
    known = {'watchfighters.com', 'clips4sale.com', 'iwantclips.com', 'manyvids.com',
             'gumroad.com', 'sellfy.com', 'sellfy.store', 'payhip.com'}
    candidates = [(a.attrs['href'], clean(a.text())) for a in scope.all(
        lambda n: n.tag == 'a' and n.attrs.get('href'))]
    candidates.extend((u.rstrip('.,;:!?)'), '') for u in re.findall(r'https?://[^\s<>"\u201c\u201d]+', readable(scope)))
    result = []
    for value, label in candidates:
        url = urljoin(page_url, unescape(value).strip())
        parts = urlsplit(url)
        if parts.scheme not in {'http', 'https'} or not parts.hostname:
            continue
        host = parts.hostname.lower().removeprefix('www.')
        product = any(host == h or host.endswith('.' + h) for h in known)
        explicit = bool(re.search(r'\b(?:purchase|buy|shop|download)\b', label, re.I))
        if not (product or explicit) or parts.path in {'', '/'}:
            continue
        if re.search(r'\.(?:mp4|mov|wmv|avi|mkv|jpg|jpeg|png|gif|webp|mp3|pdf|zip)$', parts.path, re.I):
            continue
        if host in {'film911.net', 'x.com', 'twitter.com', 'instagram.com'}:
            continue
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))
        if url not in result:
            result.append(url)
    return result


def cover_candidates(root, scope, content, page_url):
    values = [n.attrs.get('poster') for n in scope.all(lambda n: n.tag == 'video')]
    values.extend(n.attrs.get('content') for n in root.all(
        lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:image'))
    if content:
        for image in content.all(lambda n: n.tag == 'img'):
            variants = []
            for value in (image.attrs.get('srcset') or '').split(','):
                match = re.fullmatch(r'\s*(\S+)\s+(\d+)w\s*', value)
                if match:
                    variants.append((int(match[2]), match[1]))
            values.extend(url for _, url in sorted(variants, reverse=True))
            values.extend(image.attrs.get(k) for k in ('data-src', 'src'))
            # Keep alternatives for the first content image; later images are a gallery.
            break
    for value in values:
        if not value:
            continue
        # Some migrated posts have this broken src, while srcset remains correct.
        value = value.replace('https://film911.net-content/', BASE + '/wp-content/')
        url = image_url(value, page_url)
        if url:
            yield url


def scene(url):
    url = canonical(url)
    root = fetch(url)
    entries = list(schema_entries(root))
    article = next((e for e in entries if has_type(e, {'Article'})), {})
    scope = root.first(lambda n: n.has_class('vsingle')) or root.first(lambda n: n.tag == 'article')
    if scope is None:
        raise ValueError('Use an individual Film911 scene page, not a category or information page')
    heading = scope.first(lambda n: n.has_class('vsingle-title')) or scope.first(lambda n: n.has_class('entry-title'))
    raw_title = heading.text() if heading else article.get('headline', '')
    if not clean(raw_title):
        heading = scope.first(lambda n: n.tag in {'h1', 'h2'} and clean(n.text()).casefold() not in {'film 911', 'film911'})
        raw_title = heading.text() if heading else ''
    title = clean_title(raw_title)
    if not title:
        raise ValueError('Scene title not found')
    content = scope.first(lambda n: n.has_class('vsingle-desc')) or scope.first(
        lambda n: n.has_class('entry-content') or n.has_class('post-content'))
    result = {'title': title, 'urls': [url] + purchase_links(scope, url),
              'studio': {'name': STUDIO, 'urls': [BASE + '/']}}
    if content:
        text = description(content)
        if text:
            result['details'] = text
    date = release_date(raw_title, url, entries, root)
    if date:
        result['date'] = date
    images = download_images(cover_candidates(root, scope, content, url), url)
    if images:
        result['image'] = images[0]
    # WordPress's Person/author is the site administrator, not a cast credit.
    return result


def main():
    try:
        data = json.load(sys.stdin)
        if sys.argv[1] != 'scene':
            raise ValueError('Unknown scraper action')
        print(json.dumps(scene(data['url']), ensure_ascii=True))
    except Exception as error:
        log(str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
