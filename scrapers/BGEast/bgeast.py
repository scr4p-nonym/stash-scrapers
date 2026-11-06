"""BG East public individual-match and wrestler metadata. AGPL-3.0."""
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs,urlencode,urljoin,urlsplit
from public_html import Client,Document,clean,text_blocks

BASE='https://www.bgeast.com'
HOSTS={'www.bgeast.com','bgeast.com'}
STUDIO='BG East'

def canonical(value,kind='scene'):
    p=urlsplit(value);q=parse_qs(p.query)
    if p.scheme not in {'http','https'} or p.hostname not in HOSTS or p.username or p.password:
        raise ValueError('Expected a BG East public URL')
    if kind=='performer':
        values=q.get('wrestler',[])
        if p.path!='/profiles/index.php' or len(values)!=1 or not clean(values[0]) or len(values[0])>100:
            raise ValueError('Expected an individual wrestler profile URL')
        return BASE+'/profiles/index.php?'+urlencode({'wrestler':clean(values[0])})
    if p.path!='/catalog.php' or any(len(q.get(k,[]))!=1 or not re.fullmatch(r'[1-9]\d*',q[k][0]) for k in ['pid','match']):
        raise ValueError('Use an individual match URL containing both pid and match')
    return BASE+'/catalog.php?'+urlencode({k:q[k][0] for k in ['pid','match']})

def approved_entry():
    path=Path(os.environ.get('BGEAST_OPTIONS_FILE',str(Path.home()/'.stash'/'bgeast-options.json')))
    try:return json.loads(path.read_text(encoding='utf-8')).get('accept_entry') is True
    except (OSError,ValueError):return False

class BGEastClient(Client):
    def __init__(self):super().__init__(HOSTS)
    def page(self,url):
        raw,final,encoding=self.raw(url)
        root=Document(raw.decode(encoding,errors='replace')).root
        form=root.first(lambda n:n.tag=='form' and n.attrs.get('name')=='ageagree')
        if form:
            if not approved_entry():
                raise ValueError('BG East requires your 21+ and cookie/privacy confirmation; see README for private entry configuration')
            checkbox=form.first(lambda n:n.tag=='input' and n.attrs.get('name')=='agree' and n.attrs.get('value')=='on')
            target=urljoin(final,form.attrs.get('action',''))
            p=urlsplit(target)
            if not checkbox or p.scheme!='https' or p.hostname not in HOSTS or p.path!='/':
                raise ValueError('BG East entry form changed; review it before continuing')
            location=parse_qs(p.query).get('location',[])
            if len(location)!=1 or canonical(urljoin(BASE+'/',location[0]),'performer' if '/profiles/' in url else 'scene')!=url:
                raise ValueError('BG East entry form targets a different page')
            raw,final,encoding=self.raw(target,data=urlencode({'agree':'on','submit':'ENTER WEBSITE'}).encode(),referer=final)
            root=Document(raw.decode(encoding,errors='replace')).root
            if root.first(lambda n:n.tag=='form' and n.attrs.get('name')=='ageagree'):
                raise ValueError('BG East entry confirmation did not succeed')
        expected=canonical(url,'performer' if '/profiles/' in url else 'scene')
        if canonical(final,'performer' if '/profiles/' in url else 'scene')!=expected:
            raise ValueError('BG East returned a different public page')
        return root

def parse_scene(root,url):
    query=parse_qs(urlsplit(url).query);pid=query['pid'][0];match=query['match'][0]
    selected=[]
    for a in root.all(lambda n:n.tag=='a' and n.has_class('menuon') and n.attrs.get('href')):
        try:selected.append(canonical(urljoin(url,a.attrs['href'])))
        except ValueError:pass
    if selected!=[url]:raise ValueError('The selected BG East match does not agree with the requested URL')
    heading=root.first(lambda n:n.has_class('headline3'))
    if not heading or not clean(heading.text()):raise ValueError('Individual match title unavailable')
    name=clean(heading.text()).rstrip('*').strip()
    purchase=root.first(lambda n:n.has_class('headline2') and clean(n.text()).startswith('Purchase '))
    product=re.sub(r'^Purchase\s+','',clean(purchase.text())).rstrip('*').strip() if purchase else ''
    result={'title':(product+' — ' if product else '')+name,'urls':[url],
            'studio':{'name':STUDIO,'url':BASE+'/'},'tags':[{'name':'Missing Date'}]}
    # No release date is declared on the inspected public match pages.
    # Footer years, runtime, product numbers and image timestamps are not dates.
    body=root.first(lambda n:n.has_class('body'))
    if body:
        subhead=body.parent.first(lambda n:n.has_class('subhead'))
        details=text_blocks(body)
        if details:result['details']=((clean(subhead.text())+'\n\n') if subhead else '')+details
    people={}
    for a in root.all(lambda n:n.tag=='a' and n.attrs.get('href')):
        try:target=canonical(urljoin(url,a.attrs['href']),'performer')
        except ValueError:continue
        q=parse_qs(urlsplit(a.attrs['href']).query)
        if q.get('donotdisplay')!=[pid]:continue
        person=parse_qs(urlsplit(target).query)['wrestler'][0]
        people[target]={'name':person,'urls':[target],'gender':'Male','disambiguation':STUDIO}
    # Older matches can explicitly name an opponent without giving him a profile.
    # Use only the match's "A vs. B" credit line, never story prose or keywords.
    cast={p['name'].casefold():p for p in people.values()}
    ordered=[]
    if re.search(r'\s+(?:vs\.?|versus)\s+',name,re.I):
        for person in re.split(r'\s+(?:vs\.?|versus)\s+|\s*&\s*|\s+and\s+',name,flags=re.I):
            person=clean(person).strip('* ')
            if re.fullmatch(r"[\w][\w .’'()-]{0,79}",person) and len(person.split())<=5:
                key=person.casefold()
                if key not in cast:cast[key]={'name':person,'gender':'Male','disambiguation':STUDIO}
                if key not in ordered:ordered.append(key)
    ordered.extend(k for k in cast if k not in ordered)
    if cast:result['performers']=[cast[k] for k in ordered]
    codes={}
    for a in root.all(lambda n:n.tag=='a' and n.attrs.get('href')):
        p=urlsplit(urljoin(url,a.attrs['href']));q=parse_qs(p.query)
        if p.hostname in HOSTS and p.path=='/vidondemand.php' and len(q.get('vid',[]))==1:
            code=q['vid'][0]
            if re.fullmatch(r'[A-Za-z0-9_-]{1,40}',code) and code.endswith('-'+match):
                codes[code]=BASE+'/vidondemand.php?'+urlencode({'vid':code})
    if len(codes)==1:
        result['code']=next(iter(codes));result['urls'].append(next(iter(codes.values())))
    images=[]
    for caption in root.all(lambda n:n.has_class('caption')):
        declared=[]
        for image in caption.all(lambda n:n.tag=='img'):
            value=urljoin(url,image.attrs.get('src',''));p=urlsplit(value)
            if p.hostname in HOSTS and re.fullmatch(r'/catalog/images/[^/]+/'+match+r'\d{2}\.(?:jpg|jpeg|png)',p.path,re.I):
                declared.append(value)
        # First picture in each caption column is a named portrait; prefer action.
        images.extend(declared[1:]+declared[:1])
    return result,list(dict.fromkeys(images))

def parse_performer(root,url):
    heading=root.first(lambda n:n.has_class('headline'))
    expected=parse_qs(urlsplit(url).query)['wrestler'][0]
    if not heading or clean(heading.text()).casefold()!=expected.casefold():
        raise ValueError('The wrestler profile does not match the requested name')
    result={'name':clean(heading.text()),'urls':[url],'gender':'Male','disambiguation':STUDIO}
    scope=heading.parent
    body=scope.first(lambda n:n.has_class('body'))
    if body:
        text=clean(body.text())
        height=re.search(r'Height:\s*(\d+)\'\s*(\d+)',text)
        weight=re.search(r'Weight:\s*(\d+)\s*lbs',text,re.I)
        if height:result['height']=str(round((int(height[1])*12+int(height[2]))*2.54))
        if weight:result['weight']=str(round(int(weight[1])*0.45359237))
    image=scope.first(lambda n:n.tag=='img' and '/profiles/images/' in n.attrs.get('src','') and 'logo' not in n.attrs.get('src','').lower())
    return result,urljoin(url,image.attrs['src']) if image else None

def scrape(value,kind='scene',client=None):
    url=canonical(value,kind);client=client or BGEastClient();root=client.page(url)
    if kind=='performer':
        result,image=parse_performer(root,url)
        if image:
            try:result['images']=[client.image(image,url)]
            except Exception:pass
        return result
    result,images=parse_scene(root,url)
    for image in images[:3]:
        try:result['image']=client.image(image,url);break
        except Exception:pass
    return result

if __name__=='__main__':
    try:
        action=sys.argv[1] if len(sys.argv)>1 else 'scene'
        if action not in {'scene','performer'}:raise ValueError('Unsupported scraper action')
        print(json.dumps(scrape(json.load(sys.stdin)['url'],action)))
    except Exception as error:
        print('BG East: '+str(error),file=sys.stderr);sys.exit(1)
