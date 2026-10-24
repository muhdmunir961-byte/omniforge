import argparse,json,subprocess
from collections import Counter
from pathlib import Path

def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,timeout=10,check=False)
    return p.stdout.strip() if p.returncode==0 else None

def main():
    parser=argparse.ArgumentParser(description='Local Git repository reconnaissance (read-only)')
    parser.add_argument('path',nargs='?',default='.')
    a=parser.parse_args(); root=Path(a.path).resolve()
    if git(root,'rev-parse','--is-inside-work-tree')!='true': parser.error('not a git repository')
    files=(git(root,'ls-files','-z') or '').split('\0')
    extensions=Counter(Path(n).suffix.lower() or '[no extension]' for n in files if n)
    status=git(root,'status','--porcelain=v1') or ''
    result={'path':str(root),'branch':git(root,'branch','--show-current'),
     'dirty':bool(status),'changed_paths':len(status.splitlines()),
     'tracked_files':len([x for x in files if x]),
     'extensions':dict(extensions.most_common(12)),
     'recent_commits':(git(root,'log','-5','--pretty=format:%h %s') or '').splitlines()}
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
