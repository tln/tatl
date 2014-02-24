import os, json, tatlrt, tatl

def scandir(dir):
    f = os.path.join(dir, 'index.json')
    if os.path.exists(f):
        index = json.load(open(f))
    else:
        index = {}
    
    files = []
    for file in os.listdir(dir):
        if file.endswith('.html'):
            files.append(Template(dir, file))
        elif file.endswith('.md'):
            files.append(Markdown(dir, file))
            
    return tatlrt.forloop(reorder(files, index))

def reorder(files, index):
    order = index.get('order', [])
    sortkey = index.get('sortkey', 'name')
    def key(entry):
        try:
            ix = order.index(entry.name)
        except:
            ix = len(order)
        return (ix, getattr(entry, sortkey, ''))
    files.sort(key=key)
    return files
    
class Base(object):
    def __init__(self, dir, file):
        self.name = os.path.splitext(file)[0]
        self.path = os.path.join(dir, file)
        self.__dict__.update(self.front_matter())
        
    def render(self, pos):
        raise NotImplementedError
        
    def front_matter(self):
        #
        return {}

class Template(Base):
    def render(self, pos):
        # call from template
        mod = tatl.load(self.path)
        return mod.html(pos=pos)
        
    def front_matter(self):
        return tatl.front_matter(self.path)
        
class Markdown(Base):
    pass
