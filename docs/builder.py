import os, json, tatlrt, tatl, re

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
            ix = order.index(entry.file)
        except:
            ix = len(order)
        return (ix, getattr(entry, sortkey, ''))
    files.sort(key=key)
    return files

class Base(object):
    def __init__(self, dir, file):
        self.dir = dir
        self.file = file
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


def highlight(html, title=''):
    html = html.replace('&', '&amp;')
    specialtags = {'do': 'special', 'else': 'special'}
    def attr((attr, val)):
        cls = 'attr'
        if attr in 'def for use param if set'.split():
            cls += ' special'
        if val:
            return '<span class="%s"><span class="attrname">%s</span>=<span class="attrval">%s</span></span>' % (cls, attr, val)
        else:
            return '<span class="%s"><span class="attrname">%s</span></span>' % (cls, attr)

    def tag(m):
        e, tag, guts = m.groups()
        l = ['%s<span class="tag %s">%s</span>' % (e, specialtags.get(tag, ''), tag)]
        l += map(attr, re.findall('''(\w+)(?:=(".*?"|'.*?'))?''', guts))
        return '<code>&lt;%s&gt;</code>' % ' '.join(l)

    html = re.sub('<(/?)(\w+)(.*?)>', tag, html)
    html = re.sub('{{(.*?)}}', '<span class="quoted">{{<code>\\1</code>}}</span>', html)
    html = re.sub('(?s)({[^<{}]+(?:{.*?}.*?)?})', '<var>\\1</var>', html)
    html = re.sub('<(!--.*?--)>', '<span class="comment">&lt;\\1&gt;</span>', html)
    html = '<pre class="html tatl">%s</pre>' % html
    if title:
        html = '<div class="filename">%s</div>\n' % title + html
    return tatlrt.safe(html)

def as_code(path, filename=''):
    html = open(path).read()
    return highlight(html, filename)
