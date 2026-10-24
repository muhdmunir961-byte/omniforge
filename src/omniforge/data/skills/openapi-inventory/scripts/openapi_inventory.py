import argparse,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description='OpenAPI JSON endpoint inventory (offline)')
 p.add_argument('file',type=Path);a=p.parse_args();path=a.file.resolve()
 if not path.is_file() or path.stat().st_size>2_000_000:p.error('File missing or too large (2MB max)')
 spec=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(spec,dict) or not any(k in spec for k in ('openapi','swagger')):p.error('Not an OpenAPI or Swagger document')
 result=[]
 for route,operations in spec.get('paths',{}).items():
  if not isinstance(operations,dict):continue
  for method,operation in operations.items():
   if method.lower() in {'get','post','put','delete','patch','head','options','trace'} and isinstance(operation,dict):
    result.append({'method':method.upper(),'route':route,'operationId':operation.get('operationId',''),'responses':sorted(str(k) for k in operation.get('responses',{}))})
 print(json.dumps({'file':str(path),'count':len(result),'endpoints':result},indent=2))
if __name__=='__main__':main()
