from html.parser import HTMLParser
from pathlib import Path
import json,re,argparse,hashlib
from collections import Counter
from secstab.extraction import find_section,artifact_reason,BLOCK
class Reader(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.stack=[];self.out=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);local=tag.lower().split(':')[-1];style=re.sub(r'\s+','',a.get('style','').lower())
  hidden=(any(x[1] for x in self.stack) or local in {'script','style','head','hidden'} or 'display:none' in style or 'visibility:hidden' in style or 'hidden' in a)
  if not hidden and local in BLOCK:self.out.append('\n')
  if local not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,hidden))
 def handle_endtag(self,tag):
  hidden=any(x[1] for x in self.stack)
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:
    del self.stack[i:];break
  local=tag.lower().split(':')[-1]
  if not hidden:
   if local in BLOCK:self.out.append('\n')
   elif local in {'td','th'}:self.out.append(' ')
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if self.stack and self.stack[-1][0]==tag:self.handle_endtag(tag)
 def handle_data(self,data):
  if not any(x[1] for x in self.stack):self.out.append(re.sub(r'\s+',' ',data))
arg=argparse.ArgumentParser(description='Second-parser extraction check; shared boundary/cleanup policy, separate parser implementation.')
arg.add_argument('--project',default='.')
arg.add_argument('--package',required=True)
arg.add_argument('--output',required=True)
args=arg.parse_args()
p=Path(args.project)
package=Path(args.package)
checks=[]
for r in json.loads((p/'data/filings.json').read_text()):
 parser=Reader();parser.feed((p/r['raw_path']).read_text(encoding='utf-8'))
 lines=[{'text':re.sub(r'\s+',' ',l).strip()} for l in ''.join(parser.out).splitlines() if l.strip()]
 bounds,_=find_section(lines);a,b=bounds['start_line'],bounds['end_line'];c=Counter(l['text'] for l in lines[a:b])
 text='\n\n'.join(l['text'] for i,l in enumerate(lines[a:b],a) if i<=bounds['heading_end_line'] or artifact_reason(l['text'],c) is None)+'\n'
 expected=(package/'data/text/extracted_v1'/f"{r['ticker']}_item1a.txt").read_text()
 x,y=re.sub(r'\s+','',expected),re.sub(r'\s+','',text)
 result={'ticker':r['ticker'],'nonwhitespace_characters_lxml':len(x),'nonwhitespace_characters_stdlib':len(y),'exact_nonwhitespace_match':x==y}
 print(result)
 result.update(raw_sha256=hashlib.sha256((p/r['raw_path']).read_bytes()).hexdigest(),
               text_sha256=hashlib.sha256(expected.encode('utf-8')).hexdigest())
 checks.append(result)
Path(args.output).write_text(json.dumps(checks,indent=2)+'\n')
if not all(x['exact_nonwhitespace_match'] for x in checks):
 raise SystemExit('Parser disagreement: inspect differences before approval')
