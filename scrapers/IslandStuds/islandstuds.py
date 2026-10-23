"""Public Island Studs metadata. Python standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = 'https://www.islandstuds.com'
STUDIO = 'Island Studs'
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


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                    'Accept': 'text/html'})
    with urlopen(request, timeout=25) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return Document(response.read().decode(charset, errors='replace')).root


def optional_portrait(root, profile_url):
    return optional_image(root, profile_url, portrait=True)


def first_available_image(candidates, page_url):
    """Download one valid image, trying smaller declared versions on failure."""
    for image in candidates:
        try:
            request = Request(image, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; StashMetadataScraper)',
                'Referer': page_url, 'Accept': 'image/*'})
            with urlopen(request, timeout=15) as response:
                data = response.read()
            if data.startswith(b'\xff\xd8\xff'):
                content_type = 'image/jpeg'
            elif data.startswith(b'\x89PNG\r\n\x1a\n'):
                content_type = 'image/png'
            elif data[:6] in (b'GIF87a', b'GIF89a'):
                content_type = 'image/gif'
            elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
                content_type = 'image/webp'
            else:
                log('Skipping image: server did not return supported image bytes')
                continue
            return 'data:' + content_type + ';base64,' + base64.b64encode(data).decode('ascii')
        except Exception as error:
            log('Image alternative unavailable: ' + str(error))
    return None


def optional_image(root, page_url, portrait=False, preferred=()):
    """Try declared image alternatives; never return an unusable remote URL."""
    candidates = list(image_urls(preferred)) + list(image_candidates(root, portrait))
    image = first_available_image(candidates, page_url)
    if not image:
        log(('Portrait' if portrait else 'Scene image') + ' unavailable; keeping other metadata')
    return image


def performer_images(root, profile_url, name):
    """Offer the portrait plus up to seven distinct solo-scene preview pictures."""
    portrait = optional_portrait(root, profile_url)
    images = [portrait] if portrait else []
    seen_urls, seen_images = set(), set(images)
    attempts = 0
    for card in root.all(lambda n: n.has_class('update_details')):
        cast = card.first(lambda n: n.has_class('update_models'))
        if cast is None:
            continue
        credits = [clean(a.text()) for a in cast.all(lambda n: n.tag == 'a')]
        # A profile may list group scenes too; these are not individual portraits.
        if credits != [name]:
            continue
        thumbnail = card.first(lambda n: n.tag == 'img' and n.has_class('update_thumb'))
        if thumbnail is None:
            continue
        indexes = sorted({int(match[1]) for key in thumbnail.attrs
                          if (match := re.fullmatch(r'src(\d+)(?:_\d+x)?', key))})
        for index in indexes:
            candidates = [u for u in image_urls(thumbnail_values(thumbnail, index))
                          if u not in seen_urls]
            if not candidates:
                continue
            seen_urls.update(candidates)
            attempts += 1
            image = first_available_image(candidates, profile_url)
            if image and image not in seen_images:
                seen_images.add(image)
                images.append(image)
            if len(images) >= 8 or attempts >= 12:
                return images
    return images


def scene_profile_images(root, profile_url, scene_url):
    """Find this exact scene's official thumbnail on a credited model's page."""
    base_node = root.first(lambda n: n.tag == 'base' and n.attrs.get('href'))
    document_base = urljoin(profile_url, base_node.attrs['href']) if base_node else profile_url
    for card in root.all(lambda n: n.has_class('update_details')):
        for anchor in card.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                if canonical(urljoin(document_base, anchor.attrs['href'])) != scene_url:
                    continue
            except ValueError:
                continue
            image = card.first(lambda n: n.tag == 'img' and n.has_class('update_thumb'))
            if image:
                return thumbnail_values(image)
    return []


def canonical(url):
    parts = urlsplit(urljoin(BASE + '/', url))
    if parts.hostname not in {'islandstuds.com', 'www.islandstuds.com'}:
        raise ValueError('Expected an islandstuds.com URL')
    if parts.scheme not in {'http', 'https'}:
        raise ValueError('Expected an HTTP(S) URL')
    query = ''
    if parts.path == '/tour/sets.php':
        model_ids = parse_qs(parts.query).get('id', [])
        if len(model_ids) != 1 or not model_ids[0].isdigit():
            raise ValueError('Legacy model links require a numeric id')
        query = urlencode({'id': model_ids[0]})
    return urlunsplit(('https', 'www.islandstuds.com', parts.path, query, ''))


def is_model_url(url):
    parts = urlsplit(url)
    return bool(re.fullmatch(r'/tour/models/[^/]+\.html', parts.path)
                or (parts.path == '/tour/sets.php' and parse_qs(parts.query).get('id')))


def is_collection(name, url):
    return clean(name).casefold() == 'duos' or urlsplit(url).path.casefold().endswith('/duos.html')


def meta(root, property_name):
    node = root.first(lambda n: n.tag == 'meta' and n.attrs.get('property') == property_name)
    return node.attrs.get('content', '').strip() if node else ''


def cover(root):
    portrait = root.first(lambda n: n.tag == 'img' and n.has_class('model_bio_thumb'))
    return next(image_candidates(root, portrait is not None), None)


def thumbnail_values(image, index=0):
    variants = [(int(match[1]), value) for key, value in image.attrs.items()
                if (match := re.fullmatch(r'src' + str(index) + r'_(\d+)x', key)) and value]
    values = [value for _, value in sorted(variants, reverse=True)]
    values.append(image.attrs.get('src' + str(index)))
    if index == 0:
        values.append(image.attrs.get('src'))
    return values


def image_candidates(root, portrait=False):
    candidates = []

    if portrait:
        image = root.first(lambda n: n.tag == 'img' and n.has_class('model_bio_thumb'))
        if image:
            candidates.extend(thumbnail_values(image))
    else:
        candidates.append(meta(root, 'og:image'))
        for script in root.all(lambda n: n.tag == 'script'):
            candidates.extend(re.findall(r'''\bthumbnail\s*:\s*["']([^"']+)["']''', script.text()))
        image = root.first(lambda n: n.tag == 'img' and n.has_class('small_update_thumb'))
        if image:
            candidates.extend(thumbnail_values(image))
    yield from image_urls(candidates)


def image_urls(candidates):
    seen = set()
    for value in candidates:
        if not value:
            continue
        image_url = urljoin(BASE, value.replace('\\/', '/'))
        # A few older pages advertise the thumbnail folder, not an image.
        parts = urlsplit(image_url)
        if parts.scheme not in {'http', 'https'} or parts.path.endswith('/'):
            continue
        if image_url not in seen:
            seen.add(image_url)
            yield image_url


def readable_text(node):
    if node.tag in {'script', 'style'} or node.has_class('rating_text') or node.has_class('rating_box'):
        return ''
    if node.tag == 'br':
        return '\n'
    value = ''.join(readable_text(c) if isinstance(c, Node) else c for c in node.children)
    return '\n\n' + value + '\n\n' if node.tag in {'p', 'div'} else value


def description(node):
    if node is None:
        return ''
    text = readable_text(node).replace('\r', '')
    text = '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def performer(url, multiple_images=True, root=None):
    url = canonical(url)
    if not is_model_url(url) or url.endswith('/models.html') or is_collection('', url):
        raise ValueError('Use an individual model profile URL')
    if root is None:
        root = fetch(url)
    heading = root.first(lambda n: n.has_class('title_bar_hilite'))
    if heading is None or not clean(heading.text()):
        raise ValueError('Model name was not found on this page')
    if is_collection(heading.text(), url):
        raise ValueError('Duos is a collection, not an individual performer')
    result = {'name': clean(heading.text()), 'urls': [url], 'gender': 'Male',
              'disambiguation': STUDIO}
    bio = description(root.first(lambda n: n.has_class('model_bio')))
    if bio:
        result['details'] = bio
    if multiple_images:
        images = performer_images(root, url, result['name'])
    else:
        image = optional_portrait(root, url)
        images = [image] if image else []
    if images:
        result['images'] = images
    return result


def scene(url):
    url = canonical(url)
    if not re.fullmatch(r'/tour/scenes/[^/]+\.html', urlsplit(url).path):
        raise ValueError('Use an individual scene URL')
    root = fetch(url)
    heading = root.first(lambda n: n.has_class('set-title'))
    name = clean(heading.text()) if heading else meta(root, 'og:title')
    if not name:
        raise ValueError('Scene title was not found on this page')
    result = {'title': name, 'urls': [url],
              'studio': {'name': STUDIO, 'urls': [BASE + '/']}}
    text = description(root.first(lambda n: n.has_class('update_description')))
    if text:
        result['details'] = text
    date_node = root.first(lambda n: n.has_class('update_date'))
    if date_node:
        match = re.search(r'\b\d{1,2}/\d{1,2}/\d{4}\b', date_node.text())
        if match:
            try:
                result['date'] = datetime.strptime(match[0], '%m/%d/%Y').strftime('%Y-%m-%d')
            except ValueError:
                log('Invalid publication date; leaving it empty')
    # Scope to the main Featuring block; later blocks belong to recommendations.
    cast = root.first(lambda n: n.has_class('update_models'))
    base_node = root.first(lambda n: n.tag == 'base' and n.attrs.get('href'))
    document_base = urljoin(url, base_node.attrs['href']) if base_node else url
    performers, seen, preferred_images = [], set(), []
    if cast:
        for anchor in cast.all(lambda n: n.tag == 'a' and n.attrs.get('href')):
            try:
                model_url = canonical(urljoin(document_base, anchor.attrs['href']))
                if not is_model_url(model_url) or is_collection(anchor.text(), model_url):
                    continue
                if model_url in seen:
                    continue
                seen.add(model_url)
                model = {'name': clean(anchor.text()), 'urls': [model_url],
                         'gender': 'Male', 'disambiguation': STUDIO}
                if not model['name']:
                    continue
                try:
                    profile = fetch(model_url)
                    preferred_images.extend(scene_profile_images(profile, model_url, url))
                    model = performer(model_url, multiple_images=False, root=profile)
                except Exception as error:
                    log('Profile unavailable; keeping the credited performer: ' + str(error))
                performers.append(model)
            except ValueError:
                continue
    if performers:
        result['performers'] = performers
    image = optional_image(root, url, preferred=preferred_images)
    if image:
        result['image'] = image
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
