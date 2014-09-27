# TATL runtime lib
import json, re
from warnings import warn

try: unicode
except:
    # Python 3
    unicode = basestring = str
    apply = lambda f, args=(), kw={}: f(*args, **kw)

# Define some of the TATL built-ins. Compiler uses __all__ to determine whether name refers to a
# built-in.
null = None
false = False
true = True
len = len
__all__ = ['len', 'true', 'false', 'null']
__js_submodules__ = ['forloop']

def public(obj):
    "Mark a class or function as public (aka a builtin, available from TATL templates)"
    __all__.append(obj.__name__)
    return obj

# A namespace of filters.
@apply
@public
class filters:
    def _add(self, fn, _alias=re.compile('Alias: (\w+)')):
        """Mark a function as a filter. Include Alias: name in the docstring
        to make a shortened alias.

        Also add logic such that if used in def="" context (ie, given a function),
        it will return a wrapper.

        eg filters.trim(" s") -> "s"
           filters.trim(func)(...) -> filters.trim(func(...))
        """
        def f(arg, *args, **kw):
            if callable(arg) and not (args or kw):
                return lambda *args, **kw: fn(arg(*args, **kw))
            else:
                return fn(arg, *args, **kw)
        name = f.__name__ = fn.__name__
        doc = f.__doc__ = fn.__doc__
        setattr(self, name, f)
        for alias in _alias.findall(doc or ''):
            setattr(self, alias, f)
        return fn

# Marker for safe strings
@filters._add
class safe(unicode): "Quoted strings are 'safe' and do not get quoted again."

# Buffer logic, use fastbuf if available or lists if not
# This can be turned off/on at runtime, to enable testing using both paths
def use_fast(flag):
    "Turn on fast mode, if possible. Return whether fast mode is in use."
    global Buf, join, safejoin, fast
    if flag:
        try:
            from fastbuf import Buf, set_safe_class
            set_safe_class(safe)
            join = unicode
            safejoin = safe
            fast = True
            return True
        except ImportError:
            pass
    def Buf():
        return [].append
    def join(b):
        return u''.join(b.__self__)
    def safejoin(b):
        return safe(join(b))
    fast = False
    return False

use_fast(True)

# Quoting / escaping logic.
# Quote occurs through a type-switch mechanism which is faster than if isinstance chains.
_quote_safe = lambda s: s

def _quote_str(o):
    """Escape a str/unicode object. Note that compiled code never uses ' for attributes and >
    doesn't needed to be escaped to form valid HTML. These replace calls are a big cost,
    so saving 40% of them is a win.
    """
    return o.replace(u'&', u'&amp;')\
            .replace(u'<', u'&lt;')\
            .replace(u"'", u'&#39;')

def _quote_other(o, q=_quote_str):
    """Escape a non-basestring, non-unicode, non-number, non-bool, non-null object.
    Lists are space separated, dictionaries are repr-ed
    """
    if isinstance(o, (tuple, list)):
        return q(' '.join(map(unicode, o)))
    return q(unicode(o))


class _Context(object):
    "Context object, created for each TATL macro"
    # Define type-switches for quoting
    q_def = {
        int: unicode,
        float: '%.16g'.__mod__,
        safe: _quote_safe,
    }
    q = {
        'none': (json.dumps, {
            str: str,
            unicode: unicode,
        }),
        'attr': (_quote_other, {
            str: _quote_str,
            unicode: _quote_str,
        }),
    }
    quote = None

    def __init__(self, ctxname):
        self.qstack = [0]  # track whether .quote has been called with an empty value
        self.mkquote(ctxname)

    def mkquote(self, ctxname):
        # Build a quoting function from type switches
        from collections import defaultdict
        default, typesdict = self.q[ctxname]
        d = defaultdict(lambda:default, self.q_def)
        d.update(typesdict)
        d[None.__class__] = self._none
        d[bool] = self._bool
        self.quote = lambda obj: d[obj.__class__](obj)

    def _none(self, arg):
        self.qstack[-1] = 1
        return ''

    def _bool(self, arg):
        if arg: return 'true'
        self.qstack[-1] = 1
        return ''

    def star(self):
        #NB broken
        return _Star(self.estack[-1], self.quote), + self.push()

    def plusplus(self):
        #NB broken
        return _Plusplus(self.estack[-1]), + self.push()

    def elidestart(self):
        self.qstack.append(0)
        return Buf()

    def elidecheck(self, emit):
        checkresult = not (getattr(emit, 'blank_flag', 0) or self.qstack.pop())
        return checkresult, safejoin(emit)

    def load(self, name, path):
        o = __import__(name)   # TODO we need a whitelist here
        o = getattr(o, path.pop(0)) # error if first name not found
        return self.get(o, path)

    def get(self, o, path):
        for p in path:
            o = self.get1(o, p)
        return o

    def applyauto(self, func, locals):
        if isinstance(func, (_Star, _Plusplus)):
            argnames = ['dot']
        else:
            co = func.__code__
            argnames = co.co_varnames[:co.co_argcount]
        args = [locals.get(a) for a in argnames]
        result = func(*args)
        return result or ''

    def applyargs(self, func, *args):
        result = func(*args)
        return result or ''

    def items(self, obj):
        if obj is None:
            return ()
        try:
            m = obj.items
        except AttributeError:
            return enumerate(obj)
        else:
            return sorted(m())

    def itemsUnsorted(self, obj):
        if obj is None:
            return ()
        try:
            m = obj.items
        except AttributeError:
            return enumerate(obj)
        else:
            return m()

    def iter(self, obj):
        if obj is None or obj == '':
            return []
        elif isinstance(obj, basestring):
            return [obj]
        else:
            return obj

    def search(self, pattern, object):
        if isinstance(object, basestring):
            return re.search(pattern, object) is not None
        return False

    def range_incl(self, n, m):
        # Implement n...m logic.
        return range(n, m+1) if n < m else range(n, m-1, -1)

    def range_excl(self, n, m):
        # Implement n..m logic.
        return range(n, m) if n < m else range(n-1, m-1, -1)

    def get1(self, o, p):
        "Implement path lookup, both {o.p} and {o[p]}"
        try:
            return o[p]
        except (TypeError, KeyError, IndexError, AttributeError):
            if not isinstance(p, basestring): return None
            try:
                return getattr(o, p, None)
            except Exception:
                pass
        except Exception:
            pass
        warn("Unexpected error getting %r[%r]: %s" % (o, p, e))
        return None

def ctx(name):
    c = _Context(name)
    return c, c.quote

# Used elsewhere in tatl for quoting
_attr = _Context('attr')

# Used to implement {*:x}
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
        return o

    def __unicode__(self):
        return ''.join(self._l[self._len:])

    def __getitem__(self, i):
        return self._l[i + self._len]

    def __len__(self):
        return len(self._l) - self._len

# Used to implement {++:x}
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

# forloop, swiss army knife of looping
class _Forloop(object):
    length = 0
    counter0 = None
    key = None
    value = None
    sum = None
    pre = False
    post = False
    prev = None
    next = None

    counter = property(lambda self: None if self.counter0 is None else self.counter0 + 1)
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

    def __repr__(self):
        result = '<forloop:'
        for k, v in self.__dict__.items():
            if k in ('prev', 'next', 'cycle') or k.endswith('class'): continue
            result += ' %s=%r' % (k, v)
        return result + ' classes=%r>' % self.classes()
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

    if bool(result.preclass):
        result.pre = True
        lastresult = result
        result = result.make_next()
    else:
        lastresult = None
    for result.counter0, (result.key, result.value) in enumerate(_attr.items(obj)):
        if agg: agg(result.value)
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
                self.values[key].append(_attr.get1(value, key))

    def value(self):
        if not self.has_aggs:
            return None
        if self.aggfn:
            return self.aggfn(self.values)
        d = self.consts.copy()
        for key, fn in self.aggfns.items():
            d[key] = fn(self.values[key])
        return d


# Additional filters
@filters._add
def url(s):
    "Alias: u"
    import urllib
    return urllib.quote(s)


def tostr(s):
    "Convert object to string with same semantics as default context"
    if s is None:
        return ''
    if isinstance(s, basestring):
        return s
    if isinstance(s, float):
        return '%.16g' % s
    return unicode(s)

@filters._add
def trim(s):
    "A filter"
    return tostr(s).strip()

TAG = re.compile('(\s*<)([a-zA-Z0-9_.:-]+)(.*?>)', re.DOTALL)
# Tag-oriented filters
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
def contents(inner):
    """
    >>> contents(u'   <title>HI</title>   ')
    u'HI'
    >>> contents(u'<p>1</p><p>2</p>')
    u'<p>1</p><p>2</p>'
    >>> contents(u'<p><p>1</p><p>2</p></p>')
    u'<p>1</p><p>2</p>'
    """
    return safe(_findtag(inner, lambda s, start, end: s[start.end():end.start()]))

notpassed = object()
@public
def tag(tagname, attrs_or_inner, inner=notpassed):
    """
    >>> tag('h1', {}, u'HI')
    u'<h1>HI</h1>'
    >>> tag('h1', {}, u'H&I')
    u'<h1>H&amp;I</h1>'
    >>> tag('h1', None, safe(u'<title>HI</title>'))
    u'<h1><title>HI</title></h1>'
    >>> tag('h1', {'class': 'large'}, safe(u'foo:<title>HI</title>'))
    u'<h1 class="large">foo:<title>HI</title></h1>'
    """
    if inner is notpassed:
        attstr = ''
        inner = attrs_or_inner
    else:
        attrs = attrs_or_inner or {}
        attstr = ''.join(
            ' %s="%s"' % (k, _attr.quote(v))
            for k, v in sorted(attrs.items())
        )
    return safe(u'<%s>%s</%s>' % (tagname+attstr, _attr.quote(inner), tagname))

@public
def attrs(attrs, inner):
    """
    >>> attrs({'id':'id123'}, u'<title>HI</title>')
    u'<title id="id123">HI</title>'
    """
    def _replace(s, start, end):
        attstr = ''.join(' %s="%s"' % (k, _attr.quote(v)) for k, v in attrs.items())
        e = start.end(2)
        return s[:e]+attstr+s[e:]
    return safe(_findtag(inner, _replace))

if __name__ == '__main__':
    import doctest
    doctest.testmod()
