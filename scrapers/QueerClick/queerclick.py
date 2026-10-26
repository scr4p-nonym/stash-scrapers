"""Public QueerClick post metadata for Stash. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://www.queerclick.com'
STUDIO = 'QueerClick'
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
    if parts.hostname not in {'queerclick.com', 'www.queerclick.com'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected a queerclick.com HTTP(S) URL')
    if not re.fullmatch(r'/qc/\d{4}/\d{2}/[^/]+/?', parts.path):
        raise ValueError('Use an individual dated QueerClick post URL')
    return urlunsplit(('https', 'www.queerclick.com', parts.path, '', ''))


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)', 'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        canonical(response.url)  # Reject redirects away from individual public posts.
        data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('Post exceeds download limit')
        return Document(data.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')).root


def excluded(node):
    return (node.tag in {'script', 'style', 'noscript', 'iframe', 'svg', 'form', 'nav', 'aside', 'footer'}
            or node.attrs.get('id') in {'StudioButts', 'postrelated', 'disqus_thread', 'crp_related', 'extrainfos'}
            or any(node.has_class(c) for c in {'entry-title', 'taxonomy', 'postdetails', 'pagination',
                                              'entry-footer', 'sharedaddy', 'social-share', 'banana',
                                              'advertisement', 'adsbygoogle', 'related-posts'}))


def body_nodes(scope):
    content = scope.first(lambda n: n.has_class('entry-content') or n.has_class('post-content')) or scope
    for child in content.children:
        if not isinstance(child, Node):
            if clean(child):
                yield child
            continue
        if child.attrs.get('id') in {'StudioButts', 'postrelated', 'disqus_thread'} or child.has_class('postdetails'):
            break
        if not excluded(child):
            yield child


def post_text(node):
    if isinstance(node, str):
        return node
    if excluded(node):
        return ''
    if node.tag == 'br':
        return '\n'
    value = ''.join(post_text(child) for child in node.children)
    # Omit the site's short trailing affiliate call-to-action, not the story.
    if (node.tag == 'p' and len(clean(value)) < 240 and re.match(r'^Head over to\b', clean(value), re.I)
            and node.first(lambda n: n.tag == 'a')):
        return ''
    if node.tag == 'li':
        return '\n- ' + value + '\n'
    return '\n\n' + value + '\n\n' if node.tag in {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'blockquote'} else value


def post_description(nodes):
    value = ''.join(post_text(n) for n in nodes)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(clean(line) for line in value.splitlines())).strip()


def norm(value):
    return re.sub(r'[\W_]+', '', value).casefold()


def studio(scope):
    labels = {}
    for anchor in scope.all(lambda n: n.tag == 'a' and n.has_class('visitstudio')):
        match = re.fullmatch(r'Visit\s+(.+?)(?:\s*[»›→]+)?', clean(anchor.text()), re.I)
        if match and norm(match[1]) not in {'site', 'website', 'studio', 'queerclick'}:
            labels[norm(match[1])] = match[1]
    if len(labels) != 1:
        return None
    key, label = next(iter(labels.items()))
    # Explicit producer-label aliases for the studios already supported here.
    known = {norm(name): name for name in ['All Australian Boys', 'Beefcake Hunter', 'CumClub',
             'Film911', 'Island Studs', "My Best Friend's Dad", 'My Friends Feet',
             'Slow Teasing Hand Jobs', 'The Full English']}
    return {'name': known.get(key, label)}


def publication_date(root, scope):
    values = [n.attrs.get('content', '') for n in root.all(
        lambda n: n.tag == 'meta' and n.attrs.get('property') == 'article:published_time')]
    for entry in schema_entries(root):
        kind = entry.get('@type', [])
        kinds = [kind] if isinstance(kind, str) else kind
        if isinstance(kinds, list) and any(t in {'Article', 'BlogPosting', 'WebPage'} for t in kinds):
            values.append(entry.get('datePublished', ''))
    for value in values:
        if isinstance(value, str):
            try:
                return datetime.strptime(value[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                pass
    details = scope.first(lambda n: n.has_class('postdetails'))
    if details:
        date = details.first(lambda n: n.has_class('date'))
        if date:
            for value in [clean(date.text()), date.attrs.get('title', '')]:
                match = re.match(r'([A-Za-z]+\s+\d{1,2},\s*\d{4})', value)
                if match:
                    for fmt in ['%b %d, %Y', '%B %d, %Y']:
                        try:
                            return datetime.strptime(match[1], fmt).strftime('%Y-%m-%d')
                        except ValueError:
                            pass
    # No day is guessed from the year/month in the URL or image upload path.
    return None


def image_nodes(node):
    if isinstance(node, str) or excluded(node):
        return
    if node.tag == 'img':
        yield node
    for child in node.children:
        yield from image_nodes(child)


def cover_candidates(root, nodes, page_url):
    for node in nodes:
        for picture in image_nodes(node):
            if picture.attrs.get('data-lazy-type') == 'iframe':
                continue
            if any(picture.attrs.get(k) == '1' for k in ['width', 'height']):
                continue
            values = []
            variants = []
            for key in ['data-srcset', 'srcset']:
                for variant in (picture.attrs.get(key) or '').split(','):
                    match = re.fullmatch(r'\s*(\S+)\s+(\d+)w\s*', variant)
                    if match:
                        variants.append((int(match[2]), match[1]))
            values.extend(value for _, value in sorted(variants, reverse=True))
            values.extend(picture.attrs.get(key) for key in ['data-lazy-src', 'data-src', 'src'])
            candidates = []
            for value in values:
                if not value or value.lstrip().startswith('<'):
                    continue
                url = image_url(value, page_url)
                if url and not re.search(r'/cloud/default-thumb\.|/delivery/|/avw\.php', url, re.I):
                    candidates.append(url)
            if candidates:
                yield from candidates
                # This is the first real article image; do not import a gallery.
                break
        else:
            continue
        break
    for meta in root.all(lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:image'):
        value = image_url(meta.attrs.get('content'), page_url)
        if value:
            yield value


def scene(url):
    url = canonical(url)
    root = fetch(url)
    scopes = list(root.all(lambda n: n.tag == 'article' and n.first(lambda c: c.has_class('entry-title'))))
    if len(scopes) != 1:
        raise ValueError('Expected one individual QueerClick post, not a listing or archive')
    scope = scopes[0]
    title = scope.first(lambda n: n.has_class('entry-title'))
    if not title or not clean(title.text()):
        raise ValueError('Post title unavailable')
    link = root.first(lambda n: n.tag == 'link' and n.attrs.get('rel') == 'canonical')
    if link:
        url = canonical(link.attrs.get('href', url))
    nodes = list(body_nodes(scope))
    result = {'title': clean(title.text()), 'urls': [url]}
    details = post_description(nodes)
    if details:
        result['details'] = details
    date = publication_date(root, scope)
    if date:
        result['date'] = date
    producer = studio(scope)
    if producer:
        result['studio'] = producer
    images = download_images(cover_candidates(root, nodes, url), url)
    if images:
        result['image'] = images[0]
    # WordPress authors and miscellaneous post tags are not performer credits.
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


