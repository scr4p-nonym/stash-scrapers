"""Small public-page parser and bounded first-party HTTP client. AGPL-3.0."""
import base64
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class Node:
    def __init__(self,tag='',attrs=(),parent=None):
        self.tag,self.attrs,self.parent,self.children=tag,dict(attrs),parent,[]
    def has_class(self,name):
        return name in self.attrs.get('class','').split()
    def all(self,predicate):
        for child in self.children:
            if isinstance(child,Node):
                if predicate(child):yield child
                yield from child.all(predicate)
    def first(self,predicate):
        return next(self.all(predicate),None)
    def text(self):
        return ''.join(c.text() if isinstance(c,Node) else c for c in self.children)

class Document(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True)
        self.root=Node();self.stack=[self.root];self.feed(html)
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs,self.stack[-1]);self.stack[-1].children.append(node)
        if tag not in VOID:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                del self.stack[i:];break
    def handle_data(self,data):
        self.stack[-1].children.append(data)

def clean(text):
    return re.sub(r'\s+',' ',text).strip()

def blocks(node,exclude=frozenset()):
    if node.tag in {'script','style','form','img','video','noscript'} or any(node.has_class(c) for c in exclude):return ''
    if node.tag=='br':return '\n'
    value=''.join(blocks(c,exclude) if isinstance(c,Node) else c for c in node.children)
    return '\n'+value+'\n' if node.tag in {'p','div','li'} else value

def text_blocks(node,exclude=frozenset()):
    return re.sub(r'\n{3,}','\n\n','\n'.join(clean(s) for s in blocks(node,exclude).splitlines())).strip()

def meta(root,name):
    node=root.first(lambda n:n.tag=='meta' and (n.attrs.get('property')==name or n.attrs.get('name')==name))
    return node.attrs.get('content','') if node else ''

class RedirectGuard(HTTPRedirectHandler):
    def __init__(self,hosts):self.hosts=hosts
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlsplit(newurl)
        if p.scheme!='https' or p.hostname not in self.hosts or p.username or p.password:
            raise ValueError('Unexpected redirect outside the public studio site')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class Client:
    def __init__(self,hosts):
        self.hosts=set(hosts)
        self.opener=build_opener(HTTPCookieProcessor(CookieJar()),RedirectGuard(self.hosts))
    def raw(self,url,data=None,limit=2_000_000,referer=None):
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname not in self.hosts or p.username or p.password:
            raise ValueError('Unsupported studio source URL')
        headers={'User-Agent':'Mozilla/5.0 (compatible; StashMetadataScraper)'}
        if referer:headers['Referer']=referer
        with self.opener.open(Request(url,data=data,headers=headers),timeout=35) as response:
            raw=response.read(limit+1)
            if len(raw)>limit:raise ValueError('Studio response exceeds size limit')
            return raw,response.url,response.headers.get_content_charset() or 'utf-8'
    def page(self,url):
        raw,final,encoding=self.raw(url)
        return Document(raw.decode(encoding,errors='replace')).root
    def image(self,url,referer=None):
        raw,_,_=self.raw(url,limit=8_000_000,referer=referer)
        if raw.startswith(b'\xff\xd8\xff'):mime='image/jpeg'
        elif raw.startswith(b'\x89PNG\r\n\x1a\n'):mime='image/png'
        elif raw[:6] in {b'GIF87a',b'GIF89a'}:mime='image/gif'
        elif raw[:4]==b'RIFF' and raw[8:12]==b'WEBP':mime='image/webp'
        else:raise ValueError('Studio did not return a supported still image')
        return 'data:'+mime+';base64,'+base64.b64encode(raw).decode('ascii')
