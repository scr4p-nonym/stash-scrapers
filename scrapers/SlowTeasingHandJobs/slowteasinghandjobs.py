"""Public Slow Teasing Hand Jobs archive metadata. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import quote, quote_plus, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://slowteasinghandjobs.com'
STUDIO = 'Slow Teasing Hand Jobs'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}
CACHE = Path(tempfile.gettempdir()) / 'stash-slowteasinghandjobs-v1'
INDEX = Path(__file__).with_name('archive_index.json')


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


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.scheme not in {'http', 'https'} or parts.hostname not in {'slowteasinghandjobs.com', 'www.slowteasinghandjobs.com'}:
        raise ValueError('Expected a slowteasinghandjobs.com HTTP(S) URL')
    path = quote(unquote(parts.path), safe='/-._~,')
    return urlunsplit(('https', 'slowteasinghandjobs.com', path, '', ''))


def scene_key(url):
    path = unquote(urlsplit(canonical(url)).path)
    if not path.startswith('/members_sthj/') or not re.search(r'\.html?$', path, re.I):
        raise ValueError('Use an individual members_sthj scene URL')
    return path


def public_page(url):
    url = canonical(url)
    if not re.fullmatch(r'/sthj_(?:archive_\d+|updates)\.htm', urlsplit(url).path):
        raise ValueError('Only public update/archive pages may be fetched')
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                    'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError('Archive exceeds download limit')
        charset = response.headers.get_content_charset()
    if not charset:
        match = re.search(br'charset\s*=\s*["\']?([a-zA-Z0-9_-]+)', data[:4096], re.I)
        charset = match[1].decode('ascii') if match else 'cp1252'
    return Document(data.decode(charset, errors='replace')).root


MONTHS = {name: i for i, name in enumerate(('January', 'February', 'March', 'April', 'May', 'June',
                                          'July', 'August', 'September', 'October', 'November', 'December'), 1)}
DATE = re.compile(r'\b(' + '|'.join(MONTHS) + r')\s+(\d{1,2})\s*,\s*(\d{4})\b', re.I)


def parse_date(text):
    match = DATE.search(clean(text))
    if match:
        try:
            month = next(number for name, number in MONTHS.items() if name.casefold() == match[1].casefold())
            return datetime(int(match[3]), month, int(match[2])).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def metadata_text(node):
    if node.tag in {'script', 'style', 'img'}:
        return ''
    if node.tag == 'a' and (re.search(r'\.(?:mp4|wmv|mov|avi)(?:\?|$)', node.attrs.get('href', ''), re.I)
                            or clean(node.text()).casefold() in {'preview', 'download'}):
        return ''
    if node.tag == 'br':
        return '\n'
    return ''.join(metadata_text(c) if isinstance(c, Node) else c for c in node.children)


def parse_archive(root, archive_url):
    records, current_date = {}, None
    for row in root.all(lambda n: n.tag == 'tr'):
        # Outer layout rows may contain a complete nested table; process its leaf rows.
        if row.first(lambda n: n.tag == 'tr'):
            continue
        links = []
        for anchor in row.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                key = scene_key(urljoin(archive_url, anchor.attrs['href']))
                if key not in [k for k, _ in links]:
                    links.append((key, anchor))
            except ValueError:
                continue
        if not links:
            text = clean(row.text())
            if len(text) < 150:
                date = parse_date(text)
                if date:
                    current_date = date
            continue
        # Never merge two different scenes or guess which text belongs to which URL.
        if len(links) != 1:
            continue
        key, anchor = links[0]
        cells = [c for c in row.children if isinstance(c, Node) and c.tag == 'td']
        text_cells = [c for c in cells if clean(metadata_text(c))]
        if not text_cells:
            continue
        cell = text_cells[-1]
        paragraphs = list(cell.all(lambda n: n.tag == 'p'))
        lines = [clean(metadata_text(p)) for p in paragraphs]
        if not any(lines):
            bold = cell.first(lambda n: n.tag in {'b', 'strong'} and clean(metadata_text(n)))
            if not bold:
                continue
            lines = [clean(metadata_text(bold))]
        first = next(i for i, line in enumerate(lines) if line)
        title = lines[first]
        if title.casefold() in {'preview', 'download'}:
            continue
        chunks, chunk = [], []
        for line in lines[first + 1:]:
            if line:
                chunk.append(line)
            elif chunk:
                chunks.append(' '.join(chunk))
                chunk = []
        if chunk:
            chunks.append(' '.join(chunk))
        picture = anchor.first(lambda n: n.tag == 'img' and n.attrs.get('src'))
        record = {'title': title, 'url': canonical(key), 'archive': canonical(archive_url)}
        if current_date:
            record['date'] = current_date
        if chunks:
            record['details'] = '\n\n'.join(chunks)
        if picture:
            record['cover'] = image_url(picture.attrs['src'], archive_url)
        records[key] = record
    archives = set()
    for anchor in root.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
        try:
            url = canonical(urljoin(archive_url, anchor.attrs['href']))
            if re.fullmatch(r'/sthj_archive_\d+\.htm', urlsplit(url).path):
                archives.add(url)
        except ValueError:
            continue
    return {'records': records, 'archives': sorted(archives)}


def archive_data(url, force=False):
    url = canonical(url)
    name = urlsplit(url).path.rsplit('/', 1)[-1] + '.json'
    cached, path = None, CACHE / name
    try:
        cached = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(cached, dict) or not isinstance(cached.get('data'), dict):
            cached = None
            raise ValueError('Invalid metadata cache')
        if not isinstance(cached['data'].get('records'), dict) or not isinstance(cached['data'].get('archives'), list):
            cached = None
            raise ValueError('Invalid cached archive records')
        ttl = 3600 if '/sthj_updates.htm' in url else 86400
        if not force and time.time() - cached['fetched'] < ttl:
            return cached['data']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        data = parse_archive(public_page(url), url)
        if not data['records']:
            raise ValueError('No scene records found on this archive')
    except Exception:
        if cached and isinstance(cached.get('data'), dict) and not force:
            log('Archive temporarily unavailable; using previously cached public metadata')
            return cached['data']
        raise
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=CACHE, delete=False) as handle:
            temp = Path(handle.name)
            json.dump({'fetched': time.time(), 'data': data}, handle, ensure_ascii=True)
        temp.replace(path)
    except OSError as error:
        log('Optional metadata cache unavailable: ' + str(error))
    return data


def find_record(url):
    key = scene_key(url)
    manifest = json.loads(INDEX.read_text(encoding='utf-8'))
    checked = set()
    pages = set(manifest.get('archives', []))

    def check(page):
        checked.add(page)
        data = archive_data(page)
        pages.update(data['archives'])
        return data['records'].get(key)

    known = manifest.get('scenes', {}).get(key)
    if known:
        record = check(known)
        if record:
            return record
    # New scenes can be found without waiting for a scraper/index update.
    updates = BASE + '/sthj_updates.htm'
    record = check(updates)
    if record:
        return record
    # An unknown URL usually moved from updates into the newest archive.
    # Year ranges prioritize older pages; exact URL matching remains mandatory.
    year = re.search(r'/(\d{4})\s+Sets/', key, re.I)
    ranges = manifest.get('years', {})

    def priority(page):
        number = int(re.search(r'archive_(\d+)', page)[1])
        span = ranges.get(page, [])
        likely = bool(year and span and span[0] <= int(year[1]) <= span[1])
        return (not likely, -number)

    for page in sorted(pages, key=priority):
        if page in checked:
            continue
        try:
            record = check(page)
            if record:
                return record
        except Exception as error:
            log('Public archive unavailable: ' + str(error))
    raise ValueError('This exact scene link was not found in the public archives; no metadata guessed')


def normalized_title(value):
    value = re.sub(r'\s*[-–—:]\s*(?:high\s*def(?:inition)?|standard\s*def(?:inition)?|hd|sd|4k|full\s*hd)\s*$', '', value, flags=re.I)
    return re.sub(r'[^\w]+', '', value).casefold()


def c4s_page(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname != 'www.clips4sale.com' or not parts.path.startswith('/studio/1336/'):
        raise ValueError('Expected the public Clips4Sale store 1336')
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                    'Accept': 'text/html'})
    with urlopen(request, timeout=12) as response:
        data = response.read(3 * 1024 * 1024 + 1)
    if len(data) > 3 * 1024 * 1024:
        raise ValueError('Store page exceeds download limit')
    return Document(data.decode('utf-8', errors='replace')).root


def c4s_match(record):
    """Optional public cover lookup. Archive text and dates remain authoritative."""
    title = record['title']
    query = clean(re.sub(r'[^\w\s]+', ' ', title))
    search = ('https://www.clips4sale.com/studio/1336/slow-teasing-hand-jobs/'
              'Cat0-AllCategories/Page1/C4SSort-recommended/Limit24/search/' + quote_plus(query))
    try:
        root = c4s_page(search)
        candidates = {}
        for anchor in root.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            name = clean(anchor.text())
            if normalized_title(name) != normalized_title(title):
                continue
            url = urljoin('https://www.clips4sale.com', anchor.attrs['href'])
            parts = urlsplit(url)
            if parts.hostname == 'www.clips4sale.com' and re.fullmatch(r'/studio/1336/\d+/[^/]+', parts.path):
                candidates[urlunsplit(('https', parts.netloc, parts.path, '', ''))] = name
        ordered = sorted(candidates, key=lambda u: ('high def' not in candidates[u].casefold(), u))
        for clip_url in ordered[:3]:
            clip = c4s_page(clip_url)
            for script in clip.all(lambda n: n.tag == 'script' and n.attrs.get('type') == 'application/ld+json'):
                try:
                    video = json.loads(script.text())
                except (ValueError, TypeError):
                    continue
                if not isinstance(video, dict) or video.get('@type') != 'VideoObject':
                    continue
                if normalized_title(video.get('name', '')) != normalized_title(title):
                    continue
                original = re.sub(r'[^\w]+', '', record.get('details', '')).casefold()
                mirrored = re.sub(r'[^\w]+', '', video.get('description', '')).casefold()
                # Matching only a common first name/title would be unsafe.
                if len(original) < 80 or len(mirrored) < 80:
                    continue
                if original != mirrored and not (len(original) >= 200 and len(mirrored) >= 200 and original[:200] == mirrored[:200]):
                    continue
                images = [n.attrs.get('content') for n in clip.all(
                    lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:image')]
                thumbs = video.get('thumbnailUrl', [])
                images.extend([thumbs] if isinstance(thumbs, str) else thumbs)
                images = [u for value in images if value and (u := image_url(value, clip_url))
                          and urlsplit(u).hostname == 'imagecdn.clips4sale.com'
                          and re.search(r'/1336/clip_images/(?:previewlg|rect_ex_lrg)_\d+\.', urlsplit(u).path)]
                return clip_url, images
    except Exception as error:
        log('Optional Clips4Sale cover lookup unavailable: ' + str(error))
    return None


def scene(url):
    record = find_record(url)
    result = {'title': record['title'], 'urls': [record['url'], record['archive']],
              'studio': {'name': STUDIO, 'urls': [BASE + '/']}}
    for key in ('date', 'details'):
        if record.get(key):
            result[key] = record[key]
    images = []
    mirror = c4s_match(record)
    if mirror:
        clip_url, covers = mirror
        result['urls'].append(clip_url)
        images = download_images(covers, clip_url)
    if not images:
        cover = urlsplit(record.get('cover', ''))
        if cover.hostname in {'slowteasinghandjobs.com', 'www.slowteasinghandjobs.com'} and cover.path.startswith('/sthj_images/'):
            images = download_images([record['cover']], record['archive'])
    if images:
        result['image'] = images[0]
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
