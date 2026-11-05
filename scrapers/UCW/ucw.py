"""UCW factual public-catalog snapshot. Standard library only. AGPL-3.0."""
import base64,json,re,sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
BASE='https://undergroundwrestler.com'
INDEX=Path(__file__).with_name('public_index.json')

def canonical(value):
 p=urlsplit(value)
 if p.scheme not in {'http','https'} or p.hostname not in {'undergroundwrestler.com','www.undergroundwrestler.com'} or p.username or p.password:
  raise ValueError('Unsupported source URL')
 if not re.fullmatch(r'/products/[A-Za-z0-9][A-Za-z0-9_-]*/?',p.path):raise ValueError('An individual public product URL is required')
 return BASE+p.path.rstrip('/')

def image(value):
 p=urlsplit(value)
 if p.scheme!='https' or p.hostname!='cdn.shopify.com':raise ValueError('Unsupported image source')
 with urlopen(Request(value,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as r:
  if urlsplit(r.url).hostname!='cdn.shopify.com':raise ValueError('Unexpected image redirect')
  raw=r.read(8_000_001)
 if len(raw)>8_000_000:raise ValueError('Image exceeds size limit')
 mime='image/jpeg' if raw.startswith(b'\xff\xd8') else 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/webp' if raw[:4]==b'RIFF' and raw[8:12]==b'WEBP' else None
 if not mime:raise ValueError('Source did not return an image')
 return 'data:'+mime+';base64,'+base64.b64encode(raw).decode()

def scrape(value):
 url=canonical(value);handle=url.rsplit('/',1)[-1];index=json.loads(INDEX.read_text(encoding='utf-8'))
 record=index.get('products',{}).get(handle)
 if not record or record.get('url')!=url:raise ValueError('This product is not in the initial public UCW snapshot; no scene is guessed. Catalog expansion is pending site rate-limit recovery.')
 result={'title':record['title'],'urls':[url],'studio':{'name':'UCW','url':BASE+'/collections/ucw-matches'}}
 if record.get('code'):result['code']=record['code']
 people=[]
 for p in record.get('models',[]):
  u=urlsplit(p.get('url',''))
  if p.get('name') and u.hostname=='undergroundwrestler.com' and u.path.startswith('/collections/'):
   people.append({'name':p['name'],'urls':[p['url']],'gender':'Male','disambiguation':'UCW'})
 if people:result['performers']=people
 for candidate in record.get('images',[]):
  try:result['image']=image(candidate);break
  except Exception:continue
 return result

if __name__=='__main__':
 try:print(json.dumps(scrape(json.load(sys.stdin).get('url',''))))
 except Exception as e:print('UCW: '+str(e),file=sys.stderr);sys.exit(1)
