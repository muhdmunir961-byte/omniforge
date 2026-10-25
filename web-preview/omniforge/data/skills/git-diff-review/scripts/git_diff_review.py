import argparse,subprocess,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description='Read-only Git diff summary')
 p.add_argument('repo',nargs='?',default='.',type=Path)
 p.add_argument('--staged',action='store_true');a=p.parse_args()
 root=a.repo.resolve()
 command=['git','-C',str(root),'diff']
 if a.staged:command.append('--cached')
 proc=subprocess.run(command+['--numstat'],capture_output=True,text=True,timeout=12,check=False)
 if proc.returncode:p.error(proc.stderr.strip() or 'Git diff failed')
 files=[]
 for line in proc.stdout.splitlines():
  parts=line.split('\t',2)
  if len(parts)==3:
   additions,deletions,path=parts
   files.append({'path':path,'added':additions,'deleted':deletions})
 print(json.dumps({'repo':str(root),'staged':a.staged,'files':files},indent=2))
if __name__=='__main__':main()
