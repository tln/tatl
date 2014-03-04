# API for runtime
from cgi import escape as _escape
import json, re
from collections import namedtuple as _namedtuple
from warnings import warn

#abs = abs
#all = all
#any = any
#apply = apply
#max = max
#min = min
#reversed = reversed
#round = round
#sorted = sorted
#str = str
#zip = zip

null = None
false = False
true = True
bool = bool
len = len
__all__ = ['len', 'bool', 'true', 'false', 'null']

def public(obj):
    "Functions called directly from templates should be marked public"
    __all__.append(obj.__name__)
    return obj

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

@public
class safe(unicode): pass
_safe = lambda s: s

def _escape2(o, _e=_escape, _p=re.compile('''[<>&'"]''').search):
    if _p(o) is None:
        return o
    return _e(o)
    
def _escape(o):
    return o.replace(u'&', u'&amp;')\
            .replace(u'<', u'&lt;')\
            .replace(u'>', u'&gt;')\
            .replace(u'"', u'&quot;')\
            .replace(u"'", u'&#39;')

def _escape2(o):
    return unicode(o).replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')

def _escape3(o):
    return o.replace(u'&', u'&amp;').replace(u'<', u'&lt;')
    
def _bool(b):
    return 'true' if b else ''
    
class _Context(object):
    q_def = {
        bool: _bool,
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
            d[bool] = self._bool
            def quote(obj):
                return d[obj.__class__](obj)
            quote.d = d
            self.quote = self.qcache[ctxname] = quote
            
    def popctx(self):
        self.quote = self.cstack.pop()
        
    def _none(self, arg):
        self.qstack[-1] = 1
        return ''
    def _bool(self, arg):
        if arg: return 'true'
        self.qstack[-1] = 1
        return ''
    def push(self):
        cur = self.estack[-1]
        self.estack.append([])
        e = self.emit = self.estack[-1].append
        return e
        
    def star(self):
        return _Star(self.estack[-1], self.quote), self.push()
        
    def plusplus(self):
        return _Plusplus(self.estack[-1]), self.push()
        
    def pop(self):
        e = self.emit = self.estack[-2].append
        return safe(''.join(self.estack.pop())), e
        
    def result(self):
        try:
            return safe(''.join(map(''.join, self.estack)))
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
        o = getattr(o, path.pop(0)) # error if first name not found
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

    def applyargs(self, func, *args):
        # try/except?
        result = func(*args)
        return result or ''

    def items(self, obj):
        if obj is None: 
            return ()
        try:
            m = obj.items
        except AttributeError:
            return ((x+1, y) for x, y in enumerate(obj))
        else:
            return sorted(m())

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

    def search(self, pattern, object):
        if isinstance(object, basestring):
            return re.search(pattern, object) is not None
        return False

def _get1(o, p):
    try:
        return o[p]
    except (TypeError, KeyError, IndexError, AttributeError):
        if not isinstance(p, basestring): return None
        try:
            return getattr(o, p, None)
        except Exception, e:
            pass
    except Exception, e:
        pass
    warn("Unexpected error getting %r[%r]: %s" % (o, p, e))
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

    def classes(self):
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

@public
def forloop(obj, opts={}):
    "Support forloop.counter, etc"
    
    #forloop [pre] should have counter = counter0 = key = value = null
    if obj is None: 
        return
    
    if isinstance(obj, basestring):
        obj = [obj]
        
    agg = opts.pop('total', None)
    agg = agg and Aggregator(agg)
        
    result = _Forloop(len(obj), **opts)
    
    result.pre = bool(result.preclass)
    lastresult = None
    for result.counter0, (result.key, result.value) in enumerate(_attr.items(obj)):
        if agg: agg(result.value)
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
        if result.postclass or agg:
            result.prev = None
            result.post = True
            result.key = opts.get('totalkey')
            result.value = agg and agg.value()
            yield result

@public
def sum(values, _builtin=sum):
    try:
        values = map(float, values)
    except:
        return None
    return _builtin(values)

class Aggregator:
    def __init__(self, aggregators):
        if callable(aggregators):
            self.aggfn = aggregators
            self.consts = self.aggfns = {}
            self.has_aggs = True
            self.values = []
        else:
            l = [{}, {}]
            self.aggfn = None
            self.aggfns = l[True]
            self.consts = l[False]
            for k, v in aggregators.items():
                l[callable(v)][k] = v
            self.has_aggs = bool(self.aggfns or self.consts)            
            self.values = dict((k, []) for k in self.aggfns)
    def __call__(self, value):
        if not self.has_aggs: return
        if self.aggfn:
            self.values.append(value)
        else:
            for key in self.aggfns:
                self.values[key].append(_get1(value, key))

    def value(self):
        if not self.has_aggs: 
            return None
        if self.aggfn:
            return self.aggfn(self.values)
        d = self.consts.copy()
        for key, fn in self.aggfns.items():
            d[key] = fn(self.values[key])
        return d

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
        return s

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

_attr = _Context('attr')

class _NS: pass

@public
def wrap(fn):
    # define a filter
    return lambda inner:(lambda *args, **kw: fn(inner(*args, **kw)))

@public
def trim(s):
    "A filter"
    return s.strip()

TAG = re.compile('(\s*<)([a-zA-Z0-9_.:-]+)(.*?>)', re.DOTALL)
def _findtag(s, fn):
    if not isinstance(s, basestring): return s
    start = m = TAG.match(s)
    if not m: return s
    count = 1
    p = re.compile('<(/?)%s\s*' % start.group(2))
    while count:
        m = p.search(s, m.end())
        if not m: return s
        count += -1 if m.group(1) else 1
    if s[m.end()+1:].strip(): return s
    return fn(s, start, m)

@public
def contents(s):
    """
    >>> contents(u'   <title>HI</title>   ')
    u'HI'
    >>> contents(u'<p>1</p><p>2</p>')
    u'<p>1</p><p>2</p>'
    >>> contents(u'<p><p>1</p><p>2</p></p>')
    u'<p>1</p><p>2</p>'
    """
    return safe(_findtag(s, lambda s, start, end: s[start.end():end.start()]))

@public
def tag(new, s):
    """
    >>> tag('h1', u'<title>HI</title>')
    u'<h1>HI</h1>'
    >>> tag('h1', u'foo:<title>HI</title>')
    u'foo:<title>HI</title>'
    """
    def _replace(s, start, end):
        pre, post = start.group(1, 3)
        between = s[start.end():end.end(1)]  # and </
        after = s[end.end():]   # > and whitespace
        return '%s%s%s%s%s%s' % (pre, new, post, between, new, after)
    return safe(_findtag(s, _replace))

@public
def attrs(attdict, s):
    """
    >>> attrs({'id':'id123'}, u'<title>HI</title>')
    u'<title id="id123">HI</title>'
    """
    def _replace(s, start, end):
        attstr = ''.join(' %s="%s"' % (k, _escape(v)) for k, v in attdict.items())
        e = start.end(2)
        return s[:e]+attstr+s[e:]
    return safe(_findtag(s, _replace))

if __name__ == '__main__':
    import doctest
    doctest.testmod()
