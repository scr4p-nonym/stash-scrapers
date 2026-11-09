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
STUDIO = 'BG East Wrestling'
PERFORMER_DISAMBIGUATION = 'BG East'
PROFILE_PATH = '/profiles/index.php'
DIRECTORY_URL = BASE + PROFILE_PATH + '?offset=1'

# Product IDs from BG East's catalog listings. The README records the
# contemporary release coverage or archived homepages used to date each batch.
RELEASE_YEARS = {
    # Catalog 73
    **dict.fromkeys(('1128', '1129', '1130', '1131'), '2008'),
    # Catalog 87
    **dict.fromkeys(('1271', '1272', '1274', '1275', '1277', '1278'), '2011'),
    # Catalog 97
    **dict.fromkeys(('1425', '1426', '1427', '1428', '1429', '1430', '1431'), '2013'),
    # Catalogs 104.1 and 105
    **dict.fromkeys(('1495', '1497', '1498', '1499', '1500', '1501', '1502'), '2014'),
    **dict.fromkeys(('1508', '1509', '1510', '1511', '1512', '1513'), '2014'),
    # Catalogs 107 and 109.2
    **dict.fromkeys(('1524', '1525', '1526', '1527', '1528', '1529'), '2015'),
    **dict.fromkeys(('1539', '1540', '1541', '1542'), '2015'),
    # Catalog 172
    **dict.fromkeys(('2040', '2041', '2042', '2043', '2044', '2045'), '2023'),
}

def canonical(value,kind='scene'):
    p=urlsplit(value);q=parse_qs(p.query)
    if p.scheme not in {'http','https'} or p.hostname not in HOSTS or p.username or p.password:
        raise ValueError('Expected a BG East public URL')
    if kind == 'directory':
        if p.path == PROFILE_PATH and q == {'offset': ['1']}:
            return DIRECTORY_URL
        raise ValueError('Expected the BG East wrestler directory')
    if kind == 'performer':
        if p.path != PROFILE_PATH:
            raise ValueError('Expected an individual wrestler profile URL')
        profile_query = parse_qs(p.query, keep_blank_values=True)
        ids = profile_query.get('wr_id', [])
        names = profile_query.get('wrestler', [])
        if len(ids) == 1 and re.fullmatch(r'[1-9][0-9]*', ids[0]) and not names:
            return BASE + PROFILE_PATH + '?' + urlencode({'wr_id': ids[0]})
        if len(names) == 1 and 0 < len(clean(names[0])) <= 100 and not ids:
            return BASE + PROFILE_PATH + '?' + urlencode({'wrestler': clean(names[0])})
        raise ValueError('Expected one wrestler name or numeric profile ID')
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
        kind = 'scene'
        if url == DIRECTORY_URL:
            kind = 'directory'
        elif urlsplit(url).path == PROFILE_PATH:
            kind = 'performer'
        expected = canonical(url, kind)
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
            if len(location)!=1 or canonical(urljoin(BASE+'/',location[0]),kind)!=expected:
                raise ValueError('BG East entry form targets a different page')
            raw,final,encoding=self.raw(target,data=urlencode({'agree':'on','submit':'ENTER WEBSITE'}).encode(),referer=final)
            root=Document(raw.decode(encoding,errors='replace')).root
            if root.first(lambda n:n.tag=='form' and n.attrs.get('name')=='ageagree'):
                raise ValueError('BG East entry confirmation did not succeed')
        if canonical(final,kind)!=expected:
            raise ValueError('BG East returned a different public page')
        return root

def parse_scene(root,url):
    query=parse_qs(urlsplit(url).query);pid=query['pid'][0];match=query['match'][0]
    selected=[]
    for a in root.all(lambda n:n.tag=='a' and n.has_class('menuon') and n.attrs.get('href')):
        try:selected.append(canonical(urljoin(url,a.attrs['href'])))
        except ValueError:pass
    if selected and selected != [url]:
        raise ValueError('The selected BG East match does not agree with the requested URL')
    heading=root.first(lambda n:n.has_class('headline3'))
    if not heading or not clean(heading.text()):raise ValueError('Individual match title unavailable')
    name=clean(heading.text()).rstrip('*').strip()
    purchase=root.first(lambda n:n.has_class('headline2') and clean(n.text()).startswith('Purchase '))
    product=re.sub(r'^Purchase\s+','',clean(purchase.text())).rstrip('*').strip() if purchase else ''
    result={'title':(product+' — ' if product else '')+name,'urls':[url],
            'studio':{'name':STUDIO,'url':BASE+'/'},'tags':[{'name':'Missing Date'}]}
    if pid in RELEASE_YEARS:
        result['date'] = RELEASE_YEARS[pid]
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
        names = parse_qs(urlsplit(target).query).get('wrestler', [])
        if names:
            person = names[0]
        else:
            label = re.fullmatch(r'Other (.+) Matches', clean(a.text()), re.I)
            if not label:
                continue
            person = label[1]
        people[target]={'name':person,'urls':[target],'gender':'Male','disambiguation':PERFORMER_DISAMBIGUATION}
    # Older matches can explicitly name an opponent without giving him a profile.
    # Use only the match's "A vs. B" credit line, never story prose or keywords.
    cast={p['name'].casefold():p for p in people.values()}
    ordered=[]
    if re.search(r'\s+(?:vs\.?|versus)\s+',name,re.I):
        for person in re.split(r'\s+(?:vs\.?|versus)\s+|\s*&\s*|\s+and\s+',name,flags=re.I):
            person=clean(person).strip('* ')
            if re.fullmatch(r"[\w][\w .’'()-]{0,79}",person) and len(person.split())<=5:
                key=person.casefold()
                if key not in cast:cast[key]={'name':person,'gender':'Male','disambiguation':PERFORMER_DISAMBIGUATION}
                if key not in ordered:ordered.append(key)
    ordered.extend(k for k in cast if k not in ordered)
    if cast:result['performers']=[cast[k] for k in ordered]
    codes={}
    for a in root.all(lambda n:n.tag=='a' and n.attrs.get('href')):
        p=urlsplit(urljoin(url,a.attrs['href']));q=parse_qs(p.query)
        if p.hostname in HOSTS and p.path=='/vidondemand.php' and len(q.get('vid',[]))==1:
            code=q['vid'][0]
            if re.fullmatch(r'[A-Za-z0-9_-]{1,40}',code):
                codes[code]=BASE+'/vidondemand.php?'+urlencode({'vid':code})
    matching_codes = [code for code in codes if code.endswith('-' + match)]
    if not selected:
        # Some match pages omit the active navigation link. Check both IDs
        # using the product selector and the page's unique VOD link.
        product_selector = root.first(
            lambda node: node.tag == 'select' and node.attrs.get('name') == 'qty_' + pid
        )
        if not product_selector or len(codes) != 1 or not matching_codes:
            raise ValueError('BG East did not confirm the requested product and match')
    if len(matching_codes) == 1:
        code = matching_codes[0]
        result['code'] = code
        result['urls'].append(codes[code])
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
    name = clean(heading.text()) if heading else ''
    expected = parse_qs(urlsplit(url).query).get('wrestler', [])
    if not name or (expected and name.casefold() != expected[0].casefold()):
        raise ValueError('The wrestler profile does not match the requested name')
    scope=heading.parent
    if not expected and not scope.first(
        lambda node: node.tag == 'a' and
        urljoin(url, node.attrs.get('href', '')) == DIRECTORY_URL
    ):
        raise ValueError('The requested wrestler ID did not return a profile')
    result={'name':name,'urls':[url],'gender':'Male','disambiguation':PERFORMER_DISAMBIGUATION}
    body=scope.first(lambda n:n.has_class('body'))
    if body:
        text=clean(body.text())
        height=re.search(r'Height:\s*(\d+)\'\s*(\d+)',text)
        weight=re.search(r'Weight:\s*(\d+)\s*lbs',text,re.I)
        if height:result['height']=str(round((int(height[1])*12+int(height[2]))*2.54))
        if weight:result['weight']=str(round(int(weight[1])*0.45359237))
    image=scope.first(lambda n:n.tag=='img' and '/profiles/images/' in n.attrs.get('src','') and 'logo' not in n.attrs.get('src','').lower())
    return result,urljoin(url,image.attrs['src']) if image else None

def fill_profile_urls(performers, client):
    unlinked = [person for person in performers if not person.get('urls')]
    if not unlinked:
        return
    try:
        directory = client.page(DIRECTORY_URL)
    except (OSError, ValueError):
        return

    profiles = {}
    for menu in directory.all(
        lambda node: node.tag == 'select' and
        re.fullmatch(r'wrestlerjump[0-9]+', node.attrs.get('name', ''))
    ):
        for option in menu.all(lambda node: node.tag == 'option'):
            name = clean(option.text()).casefold()
            try:
                url = canonical(urljoin(DIRECTORY_URL, option.attrs.get('value', '')), 'performer')
            except ValueError:
                continue
            if name and 'wr_id' in parse_qs(urlsplit(url).query):
                profiles.setdefault(name, set()).add(url)
    for person in unlinked:
        matches = profiles.get(person['name'].casefold(), set())
        if len(matches) == 1:
            person['urls'] = list(matches)

def scrape(value,kind='scene',client=None):
    url=canonical(value,kind);client=client or BGEastClient();root=client.page(url)
    if kind=='performer':
        result,image=parse_performer(root,url)
        if image:
            try:result['images']=[client.image(image,url)]
            except Exception:pass
        return result
    result,images=parse_scene(root,url)
    fill_profile_urls(result.get('performers', []), client)
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
