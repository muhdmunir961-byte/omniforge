import argparse,json,re
from pathlib import Path
RULES={'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'common_token':re.compile(r'(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[=:]\s*[\"\']?[^\s\"\']{8,}'),
 'github_token':re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{20,}')}
SKIP={'.git','.venv','node_modules','dist','build','__pycache__'}
def main():
 p=argparse.ArgumentParser(description='Heuristic credential leak scanner. No secret values emitted.')
 p.add_argument('path',nargs='?',default='.',type=Path);a=p.parse_args()
 root=a.path.resolve()
 if not root.is_dir():p.error('Directory not found')
 findings=[];count=0
 for f in root.rglob('*'):
  if any(part in SKIP for part in f.relative_to(root).parts) or f.is_symlink() or not f.is_file():continue
  if f.suffix not in {'.py','.js','.ts','.json','.txt','.env','.md','.yaml','.yml','.toml'} or f.stat().st_size>1_000_000:continue
  count+=1
  for number,line in enumerate(f.read_text(encoding='utf-8',errors='replace').splitlines(),1):
   for kind,pat in RULES.items():
    if pat.search(line):findings.append({'path':str(f.relative_to(root)),'line':number,'kind':kind})
 print(json.dumps({'files_scanned':count,'findings':findings,'disclaimer':'Heuristic only; false positives and missed secrets possible.'},indent=2))
if __name__=='__main__':main()
