# API for runtime
from cgi import escape as _escape
import json, re
from collections import namedtuple as _namedtuple

def range_incl(n, m):
    return range(n, m+1) if n < m else range(n, m-1, -1)
    
def range_excl(n, m):
    return range(n, m) if n < m else range(n-1, m-1, -1)
        
class _Vars(object):
    def __init__(self, locals):
        self.__dict__.update(locals.pop('_kw', {}))
        self.__dict__.update(locals)
                        


def _attr_other(o, q=_escape):
    if isinstance(o, (tuple, list)):
        return ' '.join([_escape(unicode(item)) for item in o])
    return q(unicode(o))

class safe(unicode): pass
_safe = lambda s: s

def _escape2(o, _e=_escape, _p=re.compile('''[<>&'"]''').search):
    if _p(o) is None:
        return o
    return _e(o)
    
def _escape(o):
    return o.replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')

def _escape2(o):
    return unicode(o).replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')

def _escape3(o):
    return o.replace(u'&', u'&amp;').replace(u'<', u'&lt;')
    
class _Context(object):
    q_def = {
        int: unicode, 
        float: unicode, 
        safe: _safe,
    }
    q = {
        'none': (json.dumps, {
            str: str,
            unicode: unicode,
        }),
        'attr': (_attr_other, {
            str: _escape,
            unicode: _escape,
        }),
        'attr2': (lambda o: _attr_other(o, _escape2), {
            str: _escape2,
            unicode: _escape2,
        }),
    }
    def __init__(self, ctxname):
        self.qstack = [0]  # track whether .quote has been called with an empty value
        self.estack = [[]] # stack of emit lists        
        self.emit = self.estack[-1].append   # adds to bottom list; called a lot
        self.get1 = _get1
        self.quote = unicode
        self.qcache = {}
        self.cstack = []   # stack f functions
        self.pushctx(ctxname)
        
    def pushctx(self, ctxname):
        self.cstack.append(self.quote)
        try:
            self.quote = self.qcache[ctxname]
        except KeyError:
            from collections import defaultdict
            default, typesdict = self.q[ctxname]
            d = defaultdict(lambda:default, self.q_def)
            d.update(typesdict)
            d[None.__class__] = self._none
            def quote(obj):
                return d[obj.__class__](obj)
            quote.d = d
            self.quote = self.qcache[ctxname] = quote
            
    def popctx(self):
        self.quote = self.cstack.pop()
        
    def _none(self, arg):
        self.qstack[-1] = 1
        return ''
    def push(self):
        cur = self.estack[-1]
        self.estack.append([])
        e = self.emit = self.estack[-1].append
        return e
        
    def star(self):
        return _Star(self.push(), self.quote)
        
    def plusplus(self):
        return _Plusplus(self.estack[-1])
        
    def pop(self):
        e = self.emit = self.estack[-2].append
        return ''.join(self.estack.pop()), e
        
    def result(self):
        try:
            return ''.join(map(''.join, self.estack))
        except:
            print 'Error in estack!'
            return ''.join([''.join(map(unicode, l)) for l in self.estack])
        
    def elidestart(self):
        self.qstack.append(0)
        return self.push()

    def elidecheck(self):
        c, e = self.pop()
        return not self.qstack.pop(), c, e

    def load(self, name, path):
        o = __import__(name)
        o = getattr(o, path.pop()) # error if first name not found
        return self.get(o, path)

    def get(self, o, path):
        for p in path:
            o = self.get1(o, p)
        return o    

    def applyauto(self, func, locals):
        # Determine which names to provide and call!
        # Result is emitted directly
        if isinstance(func, (_Star, _Plusplus)):
            argnames = ['dot']
        else:
            co = func.__code__
            argnames = co.co_varnames[:co.co_argcount]
        args = [locals.get(a) for a in argnames]
        result = func(*args)
        return result or ''

    def applyargs(self, func, args):
        # try/except?
        result = func(*args)
        return result or ''

    def items(self, obj):
        if obj is None: 
            return ()
        try:
            m = obj.iteritems
        except AttributeError:
            return ((x+1, y) for x, y in enumerate(obj))
        else:
            return m()

    def iter(self, obj):
        d = self.quote.d
        if obj is None or obj == '':
            return []
        elif isinstance(obj, basestring):
            return [obj]
        else:
            return obj

    def itemsq(self, obj):
        d = self.quote.d
        if obj is None: 
            return ()
        try:
            m = obj.iteritems
        except AttributeError:
            return ((x+1, d[obj.__class__](obj)) for x, y in enumerate(obj))
        else:
            return ((d[k.__class__](k), d[v.__class__](v)) for k, v in m())
                        
    def iterq(self, obj):
        d = self.quote.d
        if obj is None or obj == '':
            return []
        elif isinstance(obj, basestring):
            return [d[obj.__class__](obj)]
        else:
            return (d[obj.__class__](obj) for obj in obj)

    def buildtag(self, tag, attrs):
        contents, emit = self.pop()
        return Tag(tag, attrs, contents), emit

class Tag(_namedtuple('Tag', 'tag attrs contents')):
    pass

def _get1(o, p):
    try:
        return o[p]
    except (TypeError, KeyError, IndexError, AttributeError):
        try:
            return getattr(o, p, None)
        except Exception, e:
            pass
    except Exception, e:
        pass
    warn("Unexpected error getting %s: %s", (path, e))
    return None

_none = type(None)
_simple = (_none, basestring, int, long, float)
class _Forloop(object):
    length = 0
    counter0 = 0
    key = None
    value = None
    sum = None
    pre = False
    post = False
    prev = None
    next = None
    
    counter = property(lambda self: self.counter0 + 1)
    first = property(lambda self: self.counter0 == 0)
    last = property(lambda self: self.counter == self.length)
    
    def __init__(self, length, cycle=[], firstclass='first', lastclass='last', preclass='', postclass='', **opts):
        self.length = length
        self.cycle = cycle
        self.firstclass = firstclass
        self.lastclass = lastclass
        self.preclass = preclass
        self.postclass = postclass

    @property
    def class_(self):
        l = []
        if self.preclass and self.pre:
            l.append(self.preclass)
        if self.firstclass and self.first:
            l.append(self.firstclass)
        if self.cycle:
            l.append(self.cycle[self.counter0 % len(self.cycle)])
        if self.lastclass and self.last:
            l.append(self.lastclass)
        if self.postclass and self.post:
            l.append(self.postclass)
        return ' '.join(l)

    def make_next(self):
        next = self.__class__(
            self.length,
            self.cycle,
            self.firstclass,
            self.lastclass,
            self.preclass,
            self.postclass
        )
        self.next = next
        next.prev = self
        return next

    @property
    def current(self):
        if self.post:
            return self.sum
        return self._proxy(self.value, self._store, ())._value()

    class _proxy:
        def __init__(self, o, store, path=()):
            self._o = o
            self._store = store
            self._path = path

        def _value(self):
            if isinstance(self._o, _simple):
                self._store(self._path, self._o)
                return self._o
            else:
                return self

        def __getitem__(self, p):
            return self.__class__(_get1(self._o, p), self._store, self._path+(p,))._value()
                
        def __len__(self):
            return len(self.value)

    def _store(self, path, value):
        if not path:
            self.sum = self._add(value, self.sum)
            return
        if self.sum is None:
            self.sum = {}
        d = self.sum
        for p in path[:-1]:
            d = d.setdefault(p, {})
        d[path[-1]] = self._add(value, d.get(path[-1]))
        
    def _add(self, value, cur=0):
        if not isinstance(value, (int, long, float)):
            value = int(bool(value))
        return (cur or 0) + value

def forloop(obj, opts={}):
    "Support forloop.counter, etc"
    if obj is None: 
        return
    
    if isinstance(obj, basestring):
        obj = [obj]
        
    result = _Forloop(len(obj), **opts)
    if isinstance(obj, dict):
        iter = obj.iteritems()
    else:
        iter = ((None, value) for value in obj)
    
    result.pre = bool(result.preclass)
    lastresult = None
    for result.counter0, (result.key, result.value) in enumerate(iter):
        if result.pre:
            yield result
            result.pre = False
        if lastresult:
            yield lastresult
        lastresult = result
        result = result.make_next()
    if lastresult:
        lastresult.next = None
        yield lastresult
        if result.postclass:
            result.prev = None
            result.post = True
            result.value = result.sum
            yield result

class _Star:
    def __init__(self, l, quote):
        self._l = l
        self._len = len(l)
        self._sp = 0
        self._quote = quote

    def __call__(self, o):
        s = self._quote(o)
        if s:
            if self._sp:
                s = ' '+s
            self._sp = s[-1:] not in ' \n'
            self._l.append(s)

    def __unicode__(self):
        return ''.join(self._l[self._len:])
        
    def __getitem__(self, i):
        return self._l[i + self._len]
        
    def __len__(self):
        return len(self._l) - self._len

class _Plusplus:
    def __init__(self, l):
        self._l = l
        self._ix = len(l)
        l.append('0')
        self.cur = 0

    def __call__(self, value=""):
        if value or value == "":
            self.cur += 1
            self._l[self._ix] = str(self.cur)
        return ''

    def __unicode__(self):
        return unicode(self.cur)

    def __cmp__(self, other):
        return cmp(self.cur, other)

    def __int__(self):
        return self.cur
    
def _ctx(name):
    c = _Context(name)
    return c, c.quote, c.emit

class _NS: pass
callfilt = _NS()
exprfilt = _NS()

def _filter(fn):
    # define a filter
    wrapped = lambda inner:(lambda *args, **kw: fn(inner(*args, **kw)))
    setattr(callfilt, fn.__name__, wrapped)
    setattr(exprfilt, fn.__name__, fn)

@_filter
def trim(s):
    "A filter"
    return s.strip()
    
def unsafe(s):
    "A filter"

def main():
    import sys as _sys
    for arg in _sys.argv[1:]:
        if arg.endswith('.html'):
            arg = arg[:-5]
        load(arg)
    
if __name__ == '__main__':
    main()
