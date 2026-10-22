"""Render public catalog copy before indexing, without touching scripts or form data."""
import html
import re
from html.parser import HTMLParser

VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
SKIP = {'script','style','noscript','textarea','code','pre'}
BRANDS = {'brand','corp-brand','tb-brand','newsletter-brand','notranslate'}
ATTRIBUTES = {'title','placeholder','aria-label','alt'}

class PublicCopyTranslator(HTMLParser):
    def __init__(self,catalog):
        super().__init__(convert_charrefs=True)
        self.catalog=catalog;self.stack=[];self.parts=[]
        self.patterns=[(re.compile('^'+'(.+?)'.join(re.escape(part) for part in re.split(r'\$\{[^}]+\}',key))+'$'),value) for key,value in catalog.items() if '${' in key]
    def translate(self,value):
        key=re.sub(r'\s+',' ',value).strip()
        copy=self.catalog.get(key)
        if not copy:
            for pattern,pattern_copy in self.patterns:
                match=pattern.match(key)
                if match:
                    copy=re.sub(r'GRCPLACEHOLDER(\d+)',lambda item:match.group(int(item.group(1))+1),pattern_copy)
                    break
        return value.replace(value.strip(),copy,1) if copy else value
    def start(self,tag,attrs,closed=False):
        values=dict(attrs)
        excluded=bool(self.stack and self.stack[-1][1]) or tag in SKIP or values.get('translate')=='no' or bool(BRANDS.intersection((values.get('class') or '').split())) or 'contenteditable' in values
        raw=self.get_starttag_text()
        if not excluded:
            for key,value in attrs:
                if value is not None and (key in ATTRIBUTES or (tag=='meta' and key=='content' and (values.get('name')=='description' or values.get('property') in ('og:title','og:description')))):
                    translated=self.translate(value)
                    if translated!=value:
                        raw=re.sub(r'(?<![\w-])'+re.escape(key)+r'\s*=\s*([\"\']).*?\1',lambda m:key+'="'+html.escape(translated,quote=True)+'"',raw,count=1,flags=re.S)
        self.parts.append(raw)
        if not closed and tag not in VOID:self.stack.append((tag,excluded))
    def handle_starttag(self,tag,attrs):self.start(tag,attrs)
    def handle_startendtag(self,tag,attrs):self.start(tag,attrs,True)
    def handle_endtag(self,tag):
        self.parts.append('</'+tag+'>')
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0]==tag:
                del self.stack[index:];break
    def handle_data(self,data):
        excluded=self.stack and self.stack[-1][1]
        # Raw script/style contents must retain JS/CSS operators and JSON escapes.
        raw=self.stack and self.stack[-1][0] in ('script','style')
        self.parts.append(data if raw else html.escape(data if excluded else self.translate(data),quote=False))
    def handle_comment(self,data):self.parts.append('<!--'+data+'-->')
    def handle_decl(self,decl):self.parts.append('<!'+decl+'>')

def translate_public_html(content,catalog):
    parser=PublicCopyTranslator(catalog);parser.feed(content);parser.close()
    return ''.join(parser.parts)
