import argparse,json,importlib.util
p=argparse.ArgumentParser(description='Optional Playwright availability check')
p.add_argument('--check',action='store_true')
a=p.parse_args()
print(json.dumps({'tool':'playwright','available':importlib.util.find_spec('playwright') is not None,'invocation':'omniforge browser --url https://example.org --approve'}))
