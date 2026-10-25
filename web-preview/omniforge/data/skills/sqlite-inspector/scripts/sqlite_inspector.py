import argparse,json,sqlite3
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description='Read-only SQLite schema inspector'); p.add_argument('database',type=Path);p.add_argument('--count',action='store_true',help='count rows; may be slow for large tables');a=p.parse_args()
 db=a.database.resolve()
 if not db.is_file():p.error('database does not exist')
 con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=3)
 try:
  con.execute('PRAGMA query_only=ON')
  rows=con.execute("SELECT name,type,sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
  tables=[]
  for name,typ,sql in rows:
   info={'name':name,'type':typ,'definition':sql}
   if a.count and typ=='table':
    quoted='"'+name.replace('"','""')+'"'
    info['rows']=con.execute(f'SELECT COUNT(*) FROM {quoted}').fetchone()[0]
   tables.append(info)
  print(json.dumps({'database':str(db),'objects':tables},indent=2))
 finally:con.close()
if __name__=='__main__':main()
