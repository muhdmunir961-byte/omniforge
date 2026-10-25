import argparse,json,re,tomllib
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description='Inventory dependency declarations locally');p.add_argument('path',nargs='?',default='.');a=p.parse_args();root=Path(a.path).resolve();items=[]
 for target in ['package.json','pyproject.toml','requirements.txt']:
  f=root/target
  if not f.is_file():continue
  if target=='package.json':
   data=json.loads(f.read_text());items.extend({'name':k,'version':v,'group':g,'source':target} for g in ['dependencies','devDependencies','optionalDependencies'] for k,v in data.get(g,{}).items())
  elif target=='pyproject.toml':
   data=tomllib.loads(f.read_text());items.extend({'name':x,'group':'project','source':target} for x in data.get('project',{}).get('dependencies',[]))
  else:
   items.extend({'name':s,'group':'requirements','source':target} for line in f.read_text().splitlines() if (s:=line.strip()) and not s.startswith('#'))
 print(json.dumps({'path':str(root),'count':len(items),'dependencies':items},indent=2))
if __name__=='__main__':main()
