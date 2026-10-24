import argparse,json,time,urllib.request,urllib.error,urllib.parse

def main():
 p=argparse.ArgumentParser(description='Minimal authorized HTTP header probe');p.add_argument('url');p.add_argument('--timeout',type=float,default=5);p.add_argument('--method',choices=['HEAD','GET'],default='HEAD');a=p.parse_args()
 u=urllib.parse.urlparse(a.url)
 if u.scheme not in ('http','https') or not u.hostname:p.error('Only HTTP(S) URLs allowed')
 if u.username or u.password:p.error('Credentials in URLs are not allowed')
 start=time.monotonic(); req=urllib.request.Request(a.url,method=a.method,headers={'User-Agent':'OmniForge/1.0'})
 opener=urllib.request.build_opener(urllib.request.ProxyHandler(),urllib.request.HTTPRedirectHandler())
 try:
  with opener.open(req,timeout=a.timeout) as resp:
   result={'status':resp.status,'final_url':resp.url,'elapsed_ms':round((time.monotonic()-start)*1000,1),'content_type':resp.headers.get('Content-Type'),'server':resp.headers.get('Server')}
 except urllib.error.HTTPError as e:
  result={'status':e.code,'elapsed_ms':round((time.monotonic()-start)*1000,1),'error':'HTTP error'}
 except urllib.error.URLError as e:
  result={'status':None,'elapsed_ms':round((time.monotonic()-start)*1000,1),'error':type(e.reason).__name__}
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
