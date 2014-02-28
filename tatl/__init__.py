_cache = {}

def load(template):
    "Load the given template, creating a new module for it"
    import os, imp
    from tatl import Compiler
    if template.endswith(('.html', '.tatl')):
        html = template
        if not os.path.exists(html):
            raise ImportError(html)
        template = template[:-5]
    else:
        for suf in '.t.html', '.html', '.tatl':
            if os.path.exists(template+suf):
                html = template+suf
                break
        else:
            raise ImportError(template)
    module = template.replace('.', '_').replace('/', '.')
    if module not in _cache:
        py = template+'.py'
        code = Compiler.compile(open(html).read(), html)
        with open(py, 'w') as f:
            f.write(code)
        _cache[module] = imp.load_source(module, py)
    return _cache[module]

def front_matter(template):
    import re, json
    
    s = open(template).read()
    m = re.search('(?s)<!--({.*?})\s*-->', s)
    if not m:
        return {}
    else:
        try:
            return json.loads(m.group(1))
        except:
            print m.group(1)
            raise
