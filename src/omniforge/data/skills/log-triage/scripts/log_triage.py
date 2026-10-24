import argparse,json,re
from collections import Counter
from pathlib import Path
PATTERNS={'timeout':r'timeout|timed out|ETIMEDOUT','connection':r'ECONNRESET|ECONNREFUSED|connection refused|disconnect','memory':r'out of memory|OOM|heap out of memory','database':r'prisma|postgres|sqlite|database error','uncaught':r'unhandled|uncaught|traceback|exception'}
SECRET_RE=re.compile(r'(Bearer\s+)[^\s]+|((?:password|secret|token|api_key)\s*[:=]\s*)[^\s,;]+',re.I)
def main():
    p=argparse.ArgumentParser(description='Offline log analysis; outputs counts and redacted examples')
    p.add_argument('file',type=Path); p.add_argument('--max-lines',type=int,default=200000)
    a=p.parse_args(); counts=Counter(); severity=Counter(); examples={}; seen=0
    with a.file.open('r',encoding='utf-8',errors='replace') as f:
      for line in f:
        seen+=1
        if seen>a.max_lines:break
        for level in ('ERROR','WARN','FATAL','INFO','DEBUG'):
          if re.search(r'\b'+level+r'\b',line,re.I):severity[level]+=1;break
        for typ,pattern in PATTERNS.items():
          if re.search(pattern,line,re.I):
            counts[typ]+=1
            if typ not in examples:
              examples[typ]=SECRET_RE.sub(lambda m: (m.group(1) or m.group(2) or '')+'[REDACTED]',line.strip())[:250]
    print(json.dumps({'lines_scanned':min(seen,a.max_lines),'patterns':counts,'severity':severity,'samples':examples},indent=2))
if __name__=='__main__':main()
