"""Public metadata for My Best Friend's Dad. Python standard library only.

AGPL-3.0. Cast candidates are verified against actual model filmographies;
names mentioned in prose alone are never returned as scene performers.
"""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from datetime import datetime
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://mybestfriendsdad.com'
STUDIO = "My Best Friend's Dad"
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


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'mybestfriendsdad.com', 'www.mybestfriendsdad.com'}:
        raise ValueError('Expected a mybestfriendsdad.com URL')
    if parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected an HTTP(S) URL')
    return urlunsplit(('https', 'mybestfriendsdad.com', parts.path.rstrip('/'), '', ''))


def log(message):
    print(STUDIO + ': ' + message, file=sys.stderr)


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                    'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return Document(response.read().decode(charset, errors='replace')).root


def cached(key, ttl, loader):
    """Only cache directory/filmography metadata; never signed image URLs."""
    path = Path(tempfile.gettempdir()) / 'stash-mybestfriendsdad-cache-v1'
    file = path / (hashlib.sha256(key.encode()).hexdigest() + '.json')
    try:
        value = json.loads(file.read_text(encoding='utf-8'))
        if time.time() - value['time'] < ttl:
            return value['data']
    except (OSError, ValueError, KeyError):
        pass
    data = loader()
    try:
        path.mkdir(exist_ok=True)
        # A failed or concurrent cache write must never prevent a scrape.
        file.write_text(json.dumps({'time': time.time(), 'data': data}), encoding='utf-8')
    except OSError:
        pass
    return data


def title(root):
    node = root.first(lambda n: n.tag == 'h1' and n.attrs.get('itemprop') == 'name')
    if node is None or not clean(node.text()):
        raise ValueError('Page has no scene/model heading; it may be unavailable')
    return clean(node.text())


def description(root):
    node = root.first(lambda n: n.has_class('update_view_content'))
    if node is None:
        node = root.first(lambda n: n.has_class('single-project-content'))
    if node is None:
        return ''
    return '\n\n'.join(clean(n.text()) for n in node.children
                       if isinstance(n, Node) and n.tag == 'p' and clean(n.text()))


def cover(root):
    gallery = root.first(lambda n: n.has_class('portfolio_single_gallery'))
    image = gallery.first(lambda n: n.tag == 'img' and n.attrs.get('src')) if gallery else None
    return urljoin(BASE, image.attrs['src']) if image else None


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


def date_from_text(text):
    # The first calendar date is publication, before any later Updated date.
    match = re.search(r'\b([A-Z][a-z]+ \d{1,2}, \d{4})\b', clean(text))
    if match:
        try:
            return datetime.strptime(match[1], '%B %d, %Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def model_directory():
    def load():
        root = fetch(BASE + '/models')
        result = {}
        for a in root.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            url = urljoin(BASE, a.attrs['href'])
            if re.fullmatch(r'https?://(?:www\.)?mybestfriendsdad\.com/models/[^/?#]+/?', url):
                name = clean(a.text())
                if name and name != '+':
                    result[canonical(url)] = name
        return [{'name': name, 'url': url} for url, name in result.items()]
    return cached('directory', 86400, load)


def filmography(url):
    def load():
        root = fetch(url)
        name = title(root)
        scenes = {}
        for article in root.all(lambda n: n.tag == 'article'):
            header = article.first(lambda n: n.has_class('entry-title'))
            anchor = header.first(lambda n: n.tag == 'a' and '/updates/' in n.attrs.get('href', '')) if header else None
            if anchor:
                posted = article.first(lambda n: n.has_class('posted-on'))
                scenes[canonical(anchor.attrs['href'])] = date_from_text(posted.text()) if posted else None
        return {'name': name, 'scenes': scenes}
    return cached('profile:' + url, 21600, load)


def performer(url):
    url = canonical(url)
    if not re.fullmatch(r'/models/[^/]+', urlsplit(url).path):
        raise ValueError('Use an individual model profile URL')
    root = fetch(url)
    result = {'name': title(root), 'urls': [url], 'gender': 'Male',
              'disambiguation': STUDIO}
    details, image = description(root), optional_portrait(root, url)
    if details:
        result['details'] = details
    if image:
        result['images'] = [image]
    return result


def scene(url):
    url = canonical(url)
    if not re.fullmatch(r'/updates/[^/]+', urlsplit(url).path):
        raise ValueError('Use an individual update URL')
    root = fetch(url)
    result = {'title': title(root), 'urls': [url], 'details': description(root),
              'studio': {'name': STUDIO, 'urls': [BASE + '/']}}
    image = cover(root)
    if image:
        result['image'] = image  # Keep the CDN signature and expiry query intact.
    dates = set()
    for meta in root.all(lambda n: n.tag == 'meta' and n.attrs.get('property') == 'article:published_time'):
        value = meta.attrs.get('content', '')
        if re.match(r'^\d{4}-\d{2}-\d{2}(?:T|$)', value):
            result['date'] = value[:10]
    try:
        directory = model_directory()
        filename = unquote(urlsplit(image or '').path.rsplit('/', 1)[-1])
        primary = result['title'] + ' ' + re.sub(r'[_\d.]+', ' ', filename)
        prose = result['details']
        candidates = []
        for model in directory:
            pattern = r'(?<!\w)' + re.escape(model['name']) + r'(?!\w)'
            if re.search(pattern, primary, re.I):
                candidates.append((0, model))
            elif re.search(pattern, prose):
                candidates.append((2, model))
            else:
                # Scene filenames/prose often use only a surname/first name.
                # These are candidates only: the exact scene URL must still
                # appear on the profile before any performer is returned.
                parts = re.findall(r'[A-Za-z]{3,}', model['name'])
                patterns = [r'(?<!\w)' + re.escape(part) + r'(?!\w)' for part in parts]
                if any(re.search(p, primary, re.I) for p in patterns):
                    candidates.append((1, model))
                elif any(re.search(p, prose) for p in patterns):
                    candidates.append((3, model))
        candidates.sort(key=lambda item: (item[0], -len(item[1]['name'])))
        if len(candidates) > 16:
            log('Checking the first 16 model candidates; cast may be incomplete')
        found = []
        for _, model in candidates[:16]:
            try:
                profile = filmography(model['url'])
                if url in profile['scenes']:
                    model_result = {'name': profile['name'], 'urls': [model['url']],
                                    'gender': 'Male', 'disambiguation': STUDIO}
                    try:
                        # Fetch a fresh profile for its expiring portrait URL.
                        # Returning image bytes keeps delayed imports working.
                        model_result = performer(model['url'])
                    except Exception as error:
                        log('Profile details unavailable; keeping verified performer: ' + str(error))
                    found.append(model_result)
                    if profile['scenes'][url]:
                        dates.add(profile['scenes'][url])
            except Exception as error:
                log('Could not verify profile ' + model['url'] + ': ' + str(error))
        if found:
            result['performers'] = found
    except Exception as error:
        log('Model lookup unavailable; returning scene metadata: ' + str(error))
    if 'date' not in result and len(dates) == 1:
        result['date'] = dates.pop()
    elif 'date' not in result and len(dates) > 1:
        log('Conflicting profile publication dates; leaving date empty')
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
