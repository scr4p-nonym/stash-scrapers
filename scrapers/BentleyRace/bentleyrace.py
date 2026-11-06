"""Bentley Race public scene and model metadata. Standard library only. AGPL-3.0."""
from datetime import datetime
import json
import re
import sys
from urllib.parse import urljoin,urlsplit
from public_html import Client,Document,clean,meta,text_blocks

BASE='https://bentleyrace.com'
HOSTS={'bentleyrace.com','www.bentleyrace.com'}
STUDIO='Bentley Race'

def canonical(value,kind='scene'):
    p=urlsplit(value)
    if p.scheme not in {'http','https'} or p.hostname not in HOSTS or p.username or p.password:
        raise ValueError('Expected a Bentley Race public URL')
    pattern=r'/model/[a-z0-9-]+/?' if kind=='performer' else r'/[a-z0-9-]+/?'
    if not re.fullmatch(pattern,p.path) or p.path.strip('/') in {
        'join-now','login','blog','models','contact','model-with-us','mates','members-lounge'}:
        raise ValueError('Expected an individual scene or model page')
    return BASE+p.path.rstrip('/')

def declared_image(value,page):
    if not value:return None
    url=urljoin(page,value);p=urlsplit(url)
    if p.scheme=='https' and p.hostname in HOSTS and re.search(r'\.(?:jpe?g|png|gif|webp)$',p.path,re.I):
        return url
    return None

def portrait(root,url):
    for a in root.all(lambda n:n.tag=='a' and n.attrs.get('href')):
        try:target=canonical(urljoin(url,a.attrs['href']),'performer')
        except ValueError:continue
        if target!=url:continue
        image=a.first(lambda n:n.tag=='img' and n.attrs.get('src'))
        if not image:continue
        candidates=[]
        for item in image.attrs.get('srcset','').split(','):
            match=re.fullmatch(r'\s*(\S+)\s+(\d+)w\s*',item)
            if match:candidates.append((int(match[2]),match[1]))
        candidates.sort(reverse=True)
        for _,candidate in candidates+[(0,image.attrs['src'])]:
            if result:=declared_image(candidate,url):return result
    return None

def parse_scene(root,url):
    article=root.first(lambda n:n.tag=='article' and n.has_class('single-post'))
    if not article:raise ValueError('An individual Bentley Race scene was not returned')
    classes=article.attrs.get('class','').split()
    if not any(c in classes for c in ['category-videos','category-behind-the-scenes']):
        raise ValueError('This is not a video or behind-the-scenes video post')
    heading=article.first(lambda n:n.tag=='h1' and n.has_class('entry-title'))
    if not heading or not clean(heading.text()):raise ValueError('Scene title unavailable')
    declared=meta(root,'og:url')
    if declared and canonical(urljoin(url,declared))!=url:raise ValueError('A different scene was returned')
    result={'title':clean(heading.text()),'urls':[url],'studio':{'name':STUDIO,'url':BASE+'/'}}
    code=next((c[5:] for c in classes if re.fullmatch(r'post-\d+',c)),None)
    if code:result['code']=code
    posted=article.first(lambda n:n.has_class('posted'))
    date=clean(posted.text()) if posted else ''
    for fmt in ['%d %b, %Y','%d %B, %Y']:
        try:result['date']=datetime.strptime(date,fmt).date().isoformat();break
        except ValueError:pass
    if not result.get('date'):
        value=meta(root,'article:published_time')
        if re.match(r'^\d{4}-\d{2}-\d{2}T',value):
            try:result['date']=datetime.fromisoformat(value.replace('Z','+00:00')).date().isoformat()
            except ValueError:pass
    if not result.get('date'):result['tags']=[{'name':'Missing Date'}]
    content=article.first(lambda n:n.has_class('entry-content'))
    if content:
        details=text_blocks(content,{'public-preview','counts-and-join','signup','join','join-now-button','login'})
        if details:result['details']=details
    people={}
    for a in article.all(lambda n:n.tag=='a' and n.attrs.get('href')):
        try:target=canonical(urljoin(url,a.attrs['href']),'performer')
        except ValueError:continue
        name=clean(a.text())
        if name and target not in people:
            people[target]={'name':name,'urls':[target],'gender':'Male','disambiguation':STUDIO}
    if people:result['performers']=list(people.values())
    candidates=[]
    if content:
        for node in content.all(lambda n:n.has_class('preview-img-desktop')):
            match=re.search(r'background-image\s*:\s*url\([\'"]?([^\'")]+)',node.attrs.get('style',''),re.I)
            if match:candidates.append(match[1])
    candidates.append(meta(root,'og:image'))
    images=list(dict.fromkeys(v for c in candidates if (v:=declared_image(c,url))))
    return result,images

def parse_performer(root,url):
    heading=root.first(lambda n:n.tag=='h1')
    if not heading:raise ValueError('Model heading unavailable')
    name=re.sub(r'^Models?\s*:\s*','',clean(heading.text()),flags=re.I)
    declared=meta(root,'og:url')
    if not declared or canonical(urljoin(url,declared),'performer')!=url or not name:
        raise ValueError('A different model page was returned')
    return {'name':name,'urls':[url],'gender':'Male','disambiguation':STUDIO},portrait(root,url)

def scrape(value,kind='scene',client=None):
    url=canonical(value,kind);client=client or Client(HOSTS);root=client.page(url)
    if kind=='performer':
        result,image=parse_performer(root,url)
        if image:
            try:result['images']=[client.image(image,url)]
            except Exception:pass
        return result
    result,candidates=parse_scene(root,url)
    for image in candidates:
        try:result['image']=client.image(image,url);break
        except Exception:pass
    return result

if __name__=='__main__':
    try:
        action=sys.argv[1] if len(sys.argv)>1 else 'scene'
        if action not in {'scene','performer'}:raise ValueError('Unsupported scraper action')
        print(json.dumps(scrape(json.load(sys.stdin)['url'],action)))
    except Exception as error:
        print('Bentley Race: '+str(error),file=sys.stderr);sys.exit(1)
