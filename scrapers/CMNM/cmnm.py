"""CMNM.net member metadata. Standard library only. AGPL-3.0."""
import base64
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

BASE = 'https://members.cmnm.net'
MEMBERS = BASE + '/membersarea/'
STUDIO = 'CMNM.net'
STUDIO_URL = 'https://www.cmnm.net/'
STUDIO_ID = '676de83f-55d2-4025-9602-6f7c3c1d93df'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def has_class(self, name):
        return name in (self.attrs.get('class') or '').split()
    def all(self, predicate):
        for child in self.children:
            if isinstance(child, Node):
                if predicate(child): yield child
                yield from child.all(predicate)
    def first(self, predicate):
        return next(self.all(predicate), None)
    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root, self.stack = Node(), []
        self.stack = [self.root]
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs); self.stack[-1].children.append(n)
        if tag not in VOID: self.stack.append(n)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID: self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]; break
    def handle_data(self, data):
        self.stack[-1].children.append(data)

def clean(value):
    return re.sub(r'\s+', ' ', value).strip()

def readable(node):
    if node.tag in {'script', 'style', 'img', 'video', 'form'}: return ''
    if node.tag == 'br': return '\n'
    value = ''.join(readable(c) if isinstance(c, Node) else c for c in node.children)
    return '\n' + value + '\n' if node.tag in {'p', 'div', 'li'} else value

def text_blocks(node):
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(clean(v) for v in readable(node).splitlines())).strip()

def credentials_path():
    return Path(os.environ.get('CMNM_CREDENTIALS_FILE', str(Path.home()/'.stash'/'cmnm-credentials.json')))

def load_credentials():
    try:
        data = json.loads(credentials_path().read_text(encoding='utf-8'))
        if not data.get('username') or not data.get('password'): raise ValueError()
        return data
    except (OSError, ValueError, TypeError):
        raise ValueError('Configure the private CMNM login file outside the scraper directory; see README.') from None

def old_identity(url):
    parts=urlsplit(urljoin(MEMBERS,url))
    if parts.hostname!='members.cmnm.net' or parts.scheme not in {'http','https'} or parts.username or parts.password:
        raise ValueError('Expected an individual CMNM member scene URL')
    match=re.fullmatch(r'/membersarea/men/session([1-9]\d*)/part([1-9]\d*)\.php',parts.path)
    if not match: raise ValueError('Expected an individual CMNM archive part URL')
    return int(match[1]),int(match[2])

def old_url(identity):
    session,part=identity
    return MEMBERS+f'men/session{session}/part{part}.php'

PLAYER = MEMBERS+'oandccms/episode-player.php'

def modern_identity(value):
    match=re.fullmatch(r'session(\d+(?:ai)?)/part([1-9]\d*)',value)
    if not match: raise ValueError('Invalid CMNM player scene identifier')
    return match[1],int(match[2])

def modern_url(identity):
    session,part=identity
    value=f'session{session}/part{part}'
    modern_identity(value)
    return PLAYER+'?'+urlencode({'partToPlay':value})

def canonical(url):
    parts=urlsplit(url)
    if parts.scheme not in {'http','https'} or parts.hostname!='members.cmnm.net' or parts.username or parts.password:
        raise ValueError('Expected an individual CMNM member scene URL')
    if parts.path==urlsplit(PLAYER).path:
        values=parse_qs(parts.query).get('partToPlay',[])
        if len(values)!=1:
            raise ValueError('For newer scenes, use Copy URL in the catalog to identify the exact part')
        return modern_url(modern_identity(values[0]))
    return old_url(old_identity(url))

def part_title(title,part):
    title=re.sub(r'\s*[-–—:]?\s*Part\s+\d+\s*$', '', clean(title),flags=re.I).rstrip(' :–—-')
    return title+' — Part '+str(part)

def archive_records(root):
    result={}
    for card in root.all(lambda n:n.has_class('allmen-info')):
        name=card.first(lambda n:n.has_class('allmen-info-name'))
        if not name: continue
        for a in card.all(lambda n:n.tag=='a' and n.attrs.get('href')):
            try: identity=old_identity(a.attrs['href'])
            except ValueError: continue
            url=old_url(identity)
            result[url]={'title':part_title(name.text(),identity[1]),'url':url,'site':STUDIO,
                         'date':'','date_source':'','archive':MEMBERS+'archive.php','models':[]}
    return result

def form_identity(form):
    match=re.fullmatch(r'part-viewer-session(\d+(?:ai)?)-([1-9]\d*)',form.attrs.get('name',''))
    return (match[1],int(match[2])) if match else None

def now_showing_records(root):
    records={}
    for panel in root.all(lambda n:n.has_class('nrgUpdatePanel') or n.attrs.get('id')=='bonusUpdate'):
        name=panel.first(lambda n:n.has_class('nrgUpdateName') or n.has_class('bonusName'))
        if not name: continue
        for a in panel.all(lambda n:n.tag=='a' and n.attrs.get('href')):
            try:identity=old_identity(a.attrs['href'])
            except ValueError:continue
            url=old_url(identity)
            records[url]={'title':part_title(name.text(),identity[1]),'url':url,'site':STUDIO,
                          'date':'','date_source':'','archive':MEMBERS,'models':[]}
        for form in panel.all(lambda n:n.tag=='form'):
            identity=form_identity(form)
            if identity is None:continue
            field=form.first(lambda n:n.tag=='input' and n.attrs.get('name')=='partToPlay')
            if field and field.attrs.get('value'):
                try:actual=modern_identity(field.attrs['value'])
                except ValueError:continue
                if actual!=identity:continue
            url=modern_url(identity)
            records[url]={'title':part_title(name.text(),identity[1]),'url':url,'site':STUDIO,
                          'date':'','date_source':'','archive':MEMBERS,'models':[],
                          'view_url':MEMBERS,'view_label':'Open listing'}
    return records

def listing_titles(client):
    """Cache member listing titles privately; never persist cookies or passwords here."""
    path=credentials_path().parent/'cmnm-cache'/'listing-titles.json'
    try:
        if time.time()-path.stat().st_mtime<3600:
            return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
    try:
        rows=now_showing_records(client.page(MEMBERS))
        titles={url:row['title'] for url,row in rows.items()}
        try:
            path.parent.mkdir(mode=0o700,exist_ok=True)
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as handle:json.dump(titles,handle)
        except OSError:pass
        return titles
    except Exception:
        return {}

def parse_legacy_scene(root,url,listing_title=None):
    identity=old_identity(url)
    heading=root.first(lambda n:n.tag=='table' and n.has_class('sectiontitle'))
    cell=heading.first(lambda n:n.tag=='td') if heading else None
    desc=root.first(lambda n:n.has_class('description0') or n.has_class('description-new'))
    if not cell or not desc: raise ValueError('CMNM scene title or description unavailable')
    title=part_title(listing_title or cell.text(),identity[1])
    result={'title':title,'urls':[old_url(identity)],'studio':{'name':STUDIO,'urls':[STUDIO_URL]}}
    details=text_blocks(desc)
    if details:result['details']=details
    # "Subject" and fullinfo.php identify a story/session, not reliable cast profiles.
    # Availability expiry dates are not release dates. Never infer dates from them.
    return result

def parse_modern_scene(root,url):
    identity=modern_identity(parse_qs(urlsplit(url).query)['partToPlay'][0])
    heading=root.first(lambda n:n.tag=='table' and n.has_class('sectiontitle'))
    cell=heading.first(lambda n:n.tag=='td') if heading else None
    desc=root.first(lambda n:n.has_class('description-new'))
    if not cell or not desc:raise ValueError('This CMNM part is unavailable or lacks scene metadata')
    declared=cover_candidates(root,PLAYER)
    expected=f'/content/session{identity[0]}/part{identity[1]}/'
    if not any(expected in urlsplit(image).path for image in declared):
        raise ValueError('CMNM returned a different scene part')
    result={'title':part_title(cell.text(),identity[1]),'urls':[url],
            'studio':{'name':STUDIO,'urls':[STUDIO_URL]}}
    details=text_blocks(desc)
    if details:result['details']=details
    return result

def cover_candidates(root,page_url):
    values=[n.attrs.get('poster') for n in root.all(lambda n:n.tag=='video')]
    gallery=root.first(lambda n:n.has_class('thumbs'))
    if gallery:
        full=gallery.first(lambda n:n.tag=='a' and re.search(r'\.(?:jpg|jpeg|png|gif|webp)$',n.attrs.get('href',''),re.I))
        if full:values.append(full.attrs['href'])
    return list(dict.fromkeys(urljoin(page_url,value) for value in values if value))

def scene(url,client=None):
    url=canonical(url)
    client=client or Client()
    if urlsplit(url).path==urlsplit(PLAYER).path:
        value=parse_qs(urlsplit(url).query)['partToPlay'][0]
        root=client.page(PLAYER,{'partToPlay':value})
        result=parse_modern_scene(root,url)
        page_url=PLAYER
    else:
        root=client.page(url)
        title=listing_titles(client).get(url)
        result=parse_legacy_scene(root,url,title)
        page_url=url
    for candidate in cover_candidates(root,page_url):
        try:
            result['image']=client.image(candidate,url)
            break
        except Exception:
            print('CMNM.net: optional scene image unavailable; trying the declared fallback',file=sys.stderr)
    return result

class RestrictedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != 'https' or parts.hostname != 'members.cmnm.net' or parts.username or parts.password:
            raise ValueError('CMNM request redirected outside the member site')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Client:
    def __init__(self, credentials=None):
        self.credentials = credentials if credentials is not None else load_credentials()
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies), RestrictedRedirect())
        self.authenticated = False

    def raw(self, url, fields=None, limit=4*1024*1024):
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.hostname != 'members.cmnm.net' or parts.username or parts.password:
            raise ValueError('Expected a CMNM HTTPS member URL')
        payload = urlencode(fields).encode('utf-8') if fields is not None else None
        request = Request(url, data=payload, headers={'User-Agent':'Mozilla/5.0 (compatible; StashMetadataScraper)',
                                                    'Referer': MEMBERS})
        with self.opener.open(request, timeout=30) as response:
            data = response.read(limit+1)
            if len(data)>limit: raise ValueError('CMNM response exceeds size limit')
            return data, response.geturl(), response.headers.get_content_charset() or 'utf-8'

    def login(self):
        data, login_url, encoding = self.raw(BASE+'/login.aspx?ReturnUrl=%2fmembersarea%2farchive.php')
        root = Document(data.decode(encoding,errors='replace')).root
        form = root.first(lambda n:n.tag=='form' and n.first(lambda x:x.tag=='input' and x.attrs.get('type')=='password'))
        if form is None:
            if '/membersarea/' in login_url: self.authenticated=True; return
            raise ValueError('CMNM login form not found')
        fields = {n.attrs['name']: n.attrs.get('value','') for n in form.all(
            lambda n:n.tag=='input' and n.attrs.get('name') and n.attrs.get('type') in {'hidden','submit'})}
        fields['ctl00$Main$UserName'] = self.credentials['username']
        fields['ctl00$Main$UserPass'] = self.credentials['password']
        target = urljoin(login_url, form.attrs.get('action',''))
        if urlsplit(target).path.lower() != '/login.aspx': raise ValueError('Unexpected CMNM sign-in destination')
        data, final_url, encoding = self.raw(target, fields)
        fields.clear()
        if '/login.aspx' in final_url.lower() or b'Main_UserPass' in data:
            raise ValueError('CMNM sign-in failed; check the private login and membership access')
        self.authenticated = True

    def page(self, url, fields=None):
        if not self.authenticated: self.login()
        data, final_url, encoding = self.raw(url, fields)
        if '/login.aspx' in final_url.lower() or b'Main_UserPass' in data:
            raise ValueError('CMNM session expired or the account cannot access this page')
        return Document(data.decode(encoding,errors='replace')).root

    def image(self, url, referer):
        parts=urlsplit(url)
        if parts.scheme!='https' or parts.hostname not in {'members.cmnm.net','videos.cmnm.net'}:
            raise ValueError('Unsupported CMNM image host')
        if not re.search(r'\.(?:jpg|jpeg|png|gif|webp)$',parts.path,re.I):
            raise ValueError('Expected a still image URL')
        if parts.hostname == 'members.cmnm.net':
            if not self.authenticated: self.login()
            data, _, _ = self.raw(url, limit=8*1024*1024)
        else:
            # Never forward member-site credentials or cookies to the video host.
            opener=build_opener(RestrictedRedirect())
            with opener.open(Request(url,headers={'Referer':referer,'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                data=response.read(8*1024*1024+1)
        if len(data)>8*1024*1024: raise ValueError('Image exceeds download limit')
        if data.startswith(b'\xff\xd8\xff'): mime='image/jpeg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png'
        elif data[:6] in {b'GIF87a',b'GIF89a'}: mime='image/gif'
        elif data.startswith(b'RIFF') and data[8:12]==b'WEBP': mime='image/webp'
        else: raise ValueError('No supported still image returned')
        return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')

def main():
    try:
        data=json.load(sys.stdin)
        if len(sys.argv)<2 or sys.argv[1]!='scene': raise ValueError('Unsupported CMNM action')
        print(json.dumps(scene(data['url']),ensure_ascii=True))
    except Exception as error:
        # Exceptions must never contain request bodies, passwords, cookies or config data.
        print('CMNM.net: '+str(error),file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__': main()
