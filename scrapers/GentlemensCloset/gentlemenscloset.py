"""Public Gentlemen's Closet metadata. Standard library only. AGPL-3.0."""
import base64
from datetime import datetime
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin,urlsplit,urlunsplit
from urllib.request import Request,urlopen

BASE='https://gentlemenscloset.com'
STUDIO="Gentlemen's Closet"
HOSTS={'gentlemenscloset.com','www.gentlemenscloset.com'}
IMAGE_HOSTS={'thumbs.nastydaddy.yppcdn.com','trailers.nastydaddy.yppcdn.com'}

class Page(HTMLParser):
    def __init__(self,raw):
        super().__init__(convert_charrefs=True);self.active=False;self.parts=[];self.feed(raw)
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='__NEXT_DATA__':self.active=True
    def handle_endtag(self,tag):
        if tag=='script':self.active=False
    def handle_data(self,data):
        if self.active:self.parts.append(data)
    def props(self):
        obj=json.loads(''.join(self.parts));p=obj.get('props',{}).get('pageProps')
        if not isinstance(p,dict):raise ValueError('Public page metadata is absent')
        return p

class Text(HTMLParser):
    def __init__(self,raw):
        super().__init__(convert_charrefs=True);self.parts=[];self.skip=0;self.feed(raw)
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:self.skip+=1
        if tag in {'p','div','br','li'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style'}:self.skip=max(0,self.skip-1)
        if tag in {'p','div','li'}:self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
    def text(self):
        return '\n\n'.join(re.sub(r'\s+',' ',p).strip() for p in re.split(r'\n+', ''.join(self.parts)) if p.strip())

def canonical(value,kind):
    p=urlsplit(value)
    if p.scheme not in {'http','https'} or p.hostname not in HOSTS or p.username or p.password:
        raise ValueError('Unsupported source URL')
    if not re.fullmatch('/'+kind+r'/[A-Za-z0-9][A-Za-z0-9_-]*/?',p.path):
        raise ValueError('An individual '+kind+' URL is required')
    return BASE+p.path.rstrip('/')

def fetch_page(url):
    with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; PersonalMetadata/1.0)','Accept':'text/html'}),timeout=40) as r:
        if urlsplit(r.url).hostname not in HOSTS:raise ValueError('Unexpected source redirect')
        return Page(r.read(6_000_001).decode('utf-8')).props()

def publication(value):
    if not isinstance(value,str):return None
    for fmt in ['%Y/%m/%d %H:%M:%S','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S']:
        try:return datetime.strptime(value[:19],fmt).strftime('%Y-%m-%d')
        except ValueError:pass
    return None

def image_urls(obj,performer=False):
    candidates=[obj.get('trailer_screencap'),obj.get('thumb')]
    if performer:
        extra=obj.get('extra_thumbnails') or []
        if isinstance(extra,dict):extra=list(extra.values())
        if isinstance(extra,list):candidates+=extra
    result=[]
    for value in candidates:
        if not isinstance(value,str):continue
        p=urlsplit(urljoin(BASE,value))
        if performer:
            # The current source sometimes puts another model's named portrait in
            # extra_thumbnails. Require a filename consistent with this profile.
            identity=re.sub(r'[^a-z0-9]','',str(obj.get('slug') or '').casefold())
            filename=re.sub(r'[^a-z0-9]','',p.path.rsplit('/',1)[-1].casefold())
            if not identity or identity not in filename:continue
        if p.scheme=='https' and p.hostname in IMAGE_HOSTS and re.search(r'\.(?:jpg|jpeg|png|webp)$',p.path,re.I):
            url=urlunsplit(p)
            if url not in result:result.append(url)
    return result

def embed(url):
    with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':BASE+'/'}),timeout=35) as r:
        if urlsplit(r.url).hostname not in IMAGE_HOSTS:raise ValueError('Unexpected image redirect')
        raw=r.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError('Image exceeds size limit')
    mime='image/jpeg' if raw.startswith(b'\xff\xd8') else 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/webp' if raw[:4]==b'RIFF' and raw[8:12]==b'WEBP' else None
    if not mime:raise ValueError('Source did not return an image')
    return 'data:'+mime+';base64,'+base64.b64encode(raw).decode()

def scene_data(obj,url):
    if obj.get('site')!='GentlemensCloset':raise ValueError('Source belongs to a different studio')
    if obj.get('slug')!=urlsplit(url).path.rsplit('/',1)[-1]:raise ValueError('Scene identity differs from requested URL')
    title=str(obj.get('title') or '').strip()
    if not title:raise ValueError('Scene title is absent')
    out={'title':title,'urls':[url],'studio':{'name':STUDIO,'url':BASE+'/'}}
    details=Text(obj.get('description') or '').text()
    if details:out['details']=details
    date=publication(obj.get('publish_date'))
    if date:out['date']=date
    people=[]
    for m in obj.get('models_slugs') or []:
        name=str(m.get('name') or '').strip();slug=m.get('slug') or ''
        if name and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',slug):
            p={'name':name,'urls':[BASE+'/models/'+slug],'disambiguation':STUDIO,'gender':'Male'}
            if p not in people:people.append(p)
    if people:out['performers']=people
    return out

def performer_data(obj,url):
    if obj.get('slug')!=urlsplit(url).path.rsplit('/',1)[-1]:raise ValueError('Performer identity differs from requested URL')
    name=str(obj.get('name') or '').strip()
    if not name:raise ValueError('Performer name is absent')
    out={'name':name,'urls':[url],'disambiguation':STUDIO}
    gender={'male':'Male','female':'Female','trans male':'Transgender Male','trans female':'Transgender Female'}.get(str(obj.get('gender') or '').casefold())
    if gender:out['gender']=gender
    details=obj.get('details')
    if isinstance(details,str) and (text:=Text(details).text()):out['details']=text
    return out

def scrape(value,kind='scene'):
    url=canonical(value,'videos' if kind=='scene' else 'models');props=fetch_page(url)
    obj=props.get('content' if kind=='scene' else 'model')
    if not isinstance(obj,dict):raise ValueError('Individual source record is absent')
    out=scene_data(obj,url) if kind=='scene' else performer_data(obj,url)
    images=[]
    for candidate in image_urls(obj,kind!='scene'):
        try:images.append(embed(candidate))
        except Exception:continue
        if kind=='scene' or len(images)>=4:break
    if images:
        if kind=='scene':out['image']=images[0]
        else:out['images']=images
    return out

if __name__=='__main__':
    try:
        args=json.load(sys.stdin);kind=sys.argv[1] if len(sys.argv)>1 else 'scene'
        if kind not in {'scene','performer'}:raise ValueError('Unsupported scrape action')
        print(json.dumps(scrape(args.get('url',''),kind)))
    except Exception as e:
        print(STUDIO+': '+str(e),file=sys.stderr);sys.exit(1)
