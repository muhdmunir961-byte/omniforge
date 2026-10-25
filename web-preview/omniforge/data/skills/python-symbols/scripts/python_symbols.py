import argparse,ast,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description='Offline Python AST symbol map (no execution)')
 p.add_argument('file',type=Path);a=p.parse_args()
 f=a.file.resolve()
 if not f.is_file() or f.suffix!='.py':p.error('Expected an existing .py file')
 if f.stat().st_size>2_000_000:p.error('File exceeds 2 MB limit')
 tree=ast.parse(f.read_text(encoding='utf-8'),filename=str(f))
 symbols=[]
 for node in ast.walk(tree):
  if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
   symbols.append({'type':type(node).__name__,'name':node.name,'line':node.lineno})
 print(json.dumps({'file':str(f),'symbols':sorted(symbols,key=lambda x:x['line'])},indent=2))
if __name__=='__main__':main()
