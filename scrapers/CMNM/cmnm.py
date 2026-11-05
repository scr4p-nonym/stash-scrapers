"""CMNM.net member metadata. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import struct
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

def options():
    try:return json.loads((credentials_path().parent/'cmnm-options.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def image_dates(raw):
    """Read actual JPEG EXIF date tags; never use server/file modification times."""
    if not raw.startswith(b'\xff\xd8'):return {}
    pos=2;data=None
    while pos+4<=len(raw) and raw[pos]==255:
        marker=raw[pos+1];pos+=2
        if marker in {0xda,0xd9}:break
        if marker==1 or 0xd0<=marker<=0xd7:continue
        length=int.from_bytes(raw[pos:pos+2],'big')
        if length<2 or pos+length>len(raw):break
        block=raw[pos+2:pos+length]
        if marker==0xe1 and block.startswith(b'Exif\x00\x00'):
            data=block[6:];break
        pos+=length
    if not data or len(data)<8:return {}
    endian='<' if data[:2]==b'II' else '>' if data[:2]==b'MM' else None
    if not endian:return {}
    result={};seen=set()
    def word(offset,fmt):return struct.unpack_from(endian+fmt,data,offset)[0]
    def read_ifd(offset):
        if offset in seen or len(seen)>8:return
        seen.add(offset)
        try:
            for i in range(min(word(offset,'H'),256)):
                item=offset+2+12*i;tag=word(item,'H');kind=word(item+2,'H');length=word(item+4,'I');value=word(item+8,'I')
                if tag==0x8769:read_ifd(value)
                elif tag in {0x0132,0x9003,0x9004} and kind==2 and 0<length<80:
                    text=data[value:value+length].rstrip(b'\x00').decode('ascii',errors='replace')
                    try:
                        parsed=datetime.strptime(text[:19],'%Y:%m:%d %H:%M:%S')
                        if 1980<=parsed.year<=datetime.now().year:result[tag]=text[:19]
                    except ValueError:pass
        except (struct.error,IndexError):pass
    try:
        if word(2,'H')==42:read_ifd(word(4,'I'))
    except struct.error:pass
    return result

def add_image_year(result,dates):
    mode=options().get('image_year_mode','none')
    if mode not in {'notes','date'}:return
    tag=0x9003 if dates.get(0x9003) else 0x0132 if dates.get(0x0132) else None
    if tag is None:return
    value=dates[tag];year=value[:4]
    source='EXIF DateTimeOriginal' if tag==0x9003 else 'EXIF image-editing DateTime'
    note=f'Image metadata year: {year} ({source}: {value}). This is not a verified release year.'
    if mode=='date' and not result.get('date'):
        result['date']=year
        note=f'Estimated year used for Date: {year}, based on {source}: {value}. Original release year is unverified.'
    if re.fullmatch(r'\d{4}',result.get('date','')):
        tags=result.setdefault('tags',[])
        if not any(t.get('name')=='Missing Date' for t in tags):
            tags.append({'name':'Missing Date'})
    result['details']=(result.get('details','').rstrip()+'\n\n'+note).strip()

def subject_name(label):
    label=re.sub(r'\s*[-–—:]?\s*Part\s+\d+\s*$','',clean(label),flags=re.I).strip(' :')
    if ':' in label:label=label.rsplit(':',1)[1].strip()
    if any(c.isdigit() for c in label) or '&' in label:return None
    words=label.split()
    blocked={'the','and','dad','daddy','lad','lads','caught','wanking','prison','jail','break','debt','collectors',
             'ink','squad','footballer','bodybuilder','sale','security','club','rugby','secret','exposure','unknown',
             'guest','staff','soldier','worker','bouncer','cock','naked','catholic','fraudster'}
    if not 1<=len(words)<=2 or any(w.casefold().strip(".'’") in blocked for w in words):return None
    if not all(re.fullmatch(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*\.?",w) for w in words):return None
    return label

def subject_index(client):
    path=credentials_path().parent/'cmnm-cache'/'subject-index.json'
    try:
        if time.time()-path.stat().st_mtime<21600:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
    root=client.page(MEMBERS+'archive.php');records={};names={}
    for card in root.all(lambda n:n.has_class('allmen-info')):
        heading=card.first(lambda n:n.has_class('allmen-info-name'))
        if not heading:continue
        value=parse_qs(urlsplit(urljoin(MEMBERS,heading.attrs.get('href',''))).query).get('nm',[''])[0]
        if not value.isdecimal():continue
        name=subject_name(heading.text())
        if not name:continue
        image=card.first(lambda n:n.tag=='img' and n.attrs.get('src'))
        records[value]={'name':name,'url':MEMBERS+'fullinfo.php?'+urlencode({'nm':str(int(value))}),
                        'image':urljoin(MEMBERS,image.attrs['src']) if image else ''}
        names[name.casefold()]=names.get(name.casefold(),0)+1
    for row in records.values():row['ambiguous']=names[row['name'].casefold()]>1
    try:
        path.parent.mkdir(mode=0o700,exist_ok=True)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as handle:json.dump(records,handle)
    except OSError:pass
    return records

def subject_performer(record,client,with_image=True):
    result={'name':record['name'],'gender':'Male','disambiguation':STUDIO,'urls':[record['url']]}
    if with_image and record.get('image'):
        try:result['images']=[client.image(record['image'],MEMBERS+'archive.php')]
        except Exception:pass
    return result

def performer(url,client=None):
    p=urlsplit(url)
    if p.hostname!='members.cmnm.net' or p.scheme not in {'http','https'} or p.path!='/membersarea/fullinfo.php':
        raise ValueError('Expected an individual CMNM subject reference URL')
    values=parse_qs(p.query).get('nm',[])
    if len(values)!=1 or not values[0].isdecimal():raise ValueError('Expected one CMNM subject identifier')
    client=client or Client()
    record=subject_index(client).get(str(int(values[0])))
    if not record:raise ValueError('This entry is a story/group or has no clear individual subject name')
    return subject_performer(record,client)

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
            add_image_year(result,getattr(client,'last_image_dates',{}))
            break
        except Exception:
            print('CMNM.net: optional scene image unavailable; trying the declared fallback',file=sys.stderr)
    session=(modern_identity(parse_qs(urlsplit(url).query)['partToPlay'][0])[0]
             if urlsplit(url).path==urlsplit(PLAYER).path else str(old_identity(url)[0]))
    try:
        subject=subject_index(client).get(session)
        if subject and not subject['ambiguous']:result['performers']=[subject_performer(subject,client)]
    except Exception:
        # A missing subject reference must not discard scene metadata.
        pass
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
        self.last_image_dates = {}

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
        self.last_image_dates=image_dates(data)
        if data.startswith(b'\xff\xd8\xff'): mime='image/jpeg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png'
        elif data[:6] in {b'GIF87a',b'GIF89a'}: mime='image/gif'
        elif data.startswith(b'RIFF') and data[8:12]==b'WEBP': mime='image/webp'
        else: raise ValueError('No supported still image returned')
        return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')

def main():
    try:
        data=json.load(sys.stdin)
        if len(sys.argv)<2 or sys.argv[1] not in {'scene','performer'}: raise ValueError('Unsupported CMNM action')
        result=scene(data['url']) if sys.argv[1]=='scene' else performer(data['url'])
        print(json.dumps(result,ensure_ascii=True))
    except Exception as error:
        # Exceptions must never contain request bodies, passwords, cookies or config data.
        print('CMNM.net: '+str(error),file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__': main()
