"""Public WayBig post metadata for Stash. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://www.waybig.com'
STUDIO = 'WayBig'
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
    if parts.hostname not in {'waybig.com', 'www.waybig.com'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected a waybig.com HTTP(S) URL')
    if not re.fullmatch(r'/blog/\d{4}/\d{2}/\d{2}/[^/]+/?', parts.path):
        raise ValueError('Use an individual dated WayBig blog post URL')
    return urlunsplit(('https', 'www.waybig.com', parts.path.rstrip('/') + '/', '', ''))


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)', 'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        canonical(response.url)
        data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('Post exceeds download limit')
        return Document(data.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')).root


def excluded(node):
    return (node.tag in {'script', 'style', 'noscript', 'iframe', 'svg', 'form', 'nav', 'aside', 'footer'}
            or any(node.has_class(c) for c in {'awac-wrapper', 'awac', 'pazone_container', 'pasli',
                'ad-above-comments', 'yarpp', 'yarpp-related', 'related-posts', 'sharedaddy',
                'social-share', 'entry-meta', 'entry-footer', 'advertisement', 'adsbygoogle'}))


def text_without_links(node):
    if isinstance(node, str):
        return node
    if node.tag in {'a', 'img', 'svg'} or excluded(node):
        return ''
    return ''.join(text_without_links(c) for c in node.children)


def pure_promo(node):
    if node.tag not in {'p', 'div'}:
        return False
    links = list(node.all(lambda n: n.tag == 'a'))
    return (bool(links) and all(re.match(r'^(?:Watch|Visit|Join|Click|See)\b', clean(a.text()), re.I) for a in links)
            and not clean(text_without_links(node)).strip('|/•·–—:-'))


def post_text(node):
    if isinstance(node, str):
        return node
    if excluded(node) or pure_promo(node):
        return ''
    if node.tag == 'br':
        return '\n'
    value = ''.join(post_text(c) for c in node.children)
    if node.tag == 'li':
        return '\n- ' + value + '\n'
    return '\n\n' + value + '\n\n' if node.tag in {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'blockquote'} else value


def description(content):
    value = post_text(content)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(clean(line) for line in value.splitlines())).strip()


def publication_date(root):
    values = [n.attrs.get('content', '') for n in root.all(
        lambda n: n.tag == 'meta' and n.attrs.get('property') == 'article:published_time')]
    for item in schema_entries(root):
        kind = item.get('@type', [])
        kinds = [kind] if isinstance(kind, str) else kind
        if isinstance(kinds, list) and any(t in {'Article', 'BlogPosting', 'WebPage'} for t in kinds):
            values.append(item.get('datePublished', ''))
    values.extend(n.attrs.get('datetime', '') for n in root.all(
        lambda n: n.tag == 'time' and (n.has_class('published') or n.attrs.get('itemprop') == 'datePublished')))
    for value in values:
        if isinstance(value, str):
            try:
                return datetime.strptime(value[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                pass
    # Ignore modification dates and dates of recent/recommended posts.
    return None


def article_images(node):
    if isinstance(node, str) or excluded(node):
        return
    if node.tag == 'img':
        yield node
    for child in node.children:
        yield from article_images(child)


def cover_candidates(root, content, page_url):
    for meta in root.all(lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:image'):
        value = image_url(meta.attrs.get('content'), page_url)
        if value:
            yield value
    # A missing social image can fall back to the first real article image.
    for picture in article_images(content):
        if any(picture.attrs.get(k) == '1' for k in ['width', 'height']):
            continue
        values = []
        variants = []
        for key in ['data-srcset', 'srcset']:
            for value in (picture.attrs.get(key) or '').split(','):
                match = re.fullmatch(r'\s*(\S+)\s+(\d+)w\s*', value)
                if match:
                    variants.append((int(match[2]), match[1]))
        values.extend(url for _, url in sorted(variants, reverse=True))
        values.extend(picture.attrs.get(key) for key in ['data-lazy-src', 'data-src', 'src'])
        candidates = [url for value in values if value and (url := image_url(value, page_url))
                      and not re.search(r'(?:transparent|placeholder|blank)\.(?:gif|png)', url, re.I)]
        if candidates:
            yield from candidates
            break


def scene(url):
    url = canonical(url)
    root = fetch(url)
    titles = list(root.all(lambda n: n.tag in {'h1', 'h2'} and n.has_class('entry-title')))
    contents = list(root.all(lambda n: n.has_class('entry-content')))
    if len(titles) != 1 or len(contents) != 1 or not clean(titles[0].text()):
        raise ValueError('Expected one individual WayBig post with a title and main content')
    link = root.first(lambda n: n.tag == 'link' and n.attrs.get('rel') == 'canonical')
    if link:
        url = canonical(link.attrs.get('href', url))
    result = {'title': clean(titles[0].text()), 'urls': [url]}
    details = description(contents[0])
    if details:
        result['details'] = details
    date = publication_date(root)
    if date:
        result['date'] = date
    images = download_images(cover_candidates(root, contents[0], url), url)
    if images:
        result['image'] = images[0]
    # Blog authors, tags, studio names in titles, and recommendations are not
    # used to assign a studio or cast. The user can keep their existing values.
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


