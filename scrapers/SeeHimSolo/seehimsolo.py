"""Public See Him Solo performer metadata for Stash. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://seehimsolo.com'
STUDIO = 'See Him Solo'
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


def canonical(url):
    parts = urlsplit(url)
    if parts.hostname not in {'seehimsolo.com', 'www.seehimsolo.com'} or parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected a See Him Solo HTTP(S) URL')
    if not re.fullmatch(r'/models/[^/]+\.html', parts.path):
        raise ValueError('Use an individual model profile, not the model directory')
    return urlunsplit(('https', 'seehimsolo.com', parts.path, '', ''))


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)', 'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        if canonical(response.url) != url:
            raise ValueError('Profile redirected to a different model')
        data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('Profile exceeds download limit')
        return Document(data.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')).root


def paragraphs(node):
    if isinstance(node, str):
        return node
    if node.tag in {'script', 'style', 'noscript'}:
        return ''
    if node.tag == 'br':
        return '\n'
    value = ''.join(paragraphs(c) for c in node.children)
    return value + ('\n\n' if node.tag == 'p' else '')


def performer(url):
    url = canonical(url)
    root = fetch(url)
    profile = root.first(lambda n: n.has_class('profile-details'))
    heading = profile.first(lambda n: n.tag in {'h1', 'h3'}) if profile else None
    name = re.sub(r'^Bio\s+For\s+', '', clean(heading.text()), flags=re.I) if heading else ''
    if not name:
        raise ValueError('Individual model profile heading missing')
    result = {'name': name, 'urls': [url], 'gender': 'Male', 'disambiguation': STUDIO}
    stats_node = profile.first(lambda n: n.has_class('stats'))
    stats, links = {}, []
    if stats_node:
        for row in stats_node.all(lambda n: n.tag == 'li'):
            label_node = row.first(lambda n: n.tag == 'strong')
            if label_node is None:
                continue
            label = clean(label_node.text()).rstrip(':').casefold()
            value = paragraphs(row).strip()
            value = value[len(label_node.text()):].strip() if value.startswith(label_node.text()) else re.sub(r'^[^:]+:\s*', '', value)
            value = '\n'.join(clean(line) for line in value.splitlines() if clean(line))
            if value and value.casefold() not in {'unknown', 'n/a', 'na', 'not specified', '-'}:
                stats[label] = value
            # Only explicit external profile/social links from the model's stats.
            for a in row.all(lambda n: n.tag == 'a'):
                target = (a.attrs.get('href') or '').strip()
                parts = urlsplit(target)
                if parts.scheme in {'http', 'https'} and parts.hostname and parts.hostname not in {'seehimsolo.com', 'www.seehimsolo.com'}:
                    links.append(target)
    result['urls'] += list(dict.fromkeys(links))
    birth = stats.get('date of birth', '')
    for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d']:
        try:
            result['birthdate'] = datetime.strptime(birth, fmt).date().isoformat()
            break
        except ValueError:
            pass
    for label, field, unit in [('height', 'height', 'cm'), ('weight', 'weight', 'kg'), ('penis length', 'penis_length', 'cm')]:
        match = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*' + unit + r'\b', stats.get(label, ''), re.I)
        if match:
            result[field] = match.group(1)
    for label, field in [('ethnicity', 'ethnicity'), ('hair color', 'hair_color'), ('eye color', 'eye_color'), ('tattoos', 'tattoos'), ('piercings', 'piercings')]:
        if stats.get(label):
            result[field] = stats[label]
    cut = stats.get('circumcised', '').casefold()
    if cut in {'yes', 'no'}:
        result['circumcised'] = 'Cut' if cut == 'yes' else 'Uncut'
    details = []
    about = profile.first(lambda n: n.has_class('profile-about'))
    if about:
        for p in about.all(lambda n: n.tag == 'p'):
            value = paragraphs(p).strip()
            if value and not re.match(r'^Bio for .+ last updated \d', clean(value), re.I):
                details.append(value)
    for label, title in [('birthplace', 'Birthplace'), ('shoe size', 'Shoe size'), ('penis girth', 'Penis girth'), ('fun fact', 'Fun fact')]:
        if stats.get(label):
            details.append(title + ': ' + stats[label])
    if details:
        result['details'] = '\n\n'.join(details)
    portrait = root.first(lambda n: n.has_class('profile-pic'))
    img = portrait.first(lambda n: n.tag == 'img') if portrait else None
    if img:
        # Only versions declared for the actual model portrait; no logo/scene fallbacks.
        keys = sorted((k for k in img.attrs if re.fullmatch(r'src0_\d+x', k)), key=lambda k: int(re.search(r'_(\d+)x', k)[1]), reverse=True)
        base_node = root.first(lambda n: n.tag == 'base')
        declared_base = base_node.attrs.get('href', '') if base_node else ''
        portrait_base = declared_base if urlsplit(declared_base).hostname in {'seehimsolo.com', 'www.seehimsolo.com'} else BASE + '/'
        candidates = [urljoin(portrait_base, value) for value in
                      [img.attrs[k] for k in keys] + [img.attrs.get('src')] if value]
        images = download_images(candidates, url)
        if images:
            result['images'] = images
    return result


if __name__ == '__main__':
    try:
        args = json.load(sys.stdin)
        if len(sys.argv) != 2 or sys.argv[1] != 'performer':
            raise ValueError('Expected performer operation')
        print(json.dumps(performer(args.get('url', '')), ensure_ascii=False))
    except Exception as error:
        log(str(error))
        print('null')
        sys.exit(1)


