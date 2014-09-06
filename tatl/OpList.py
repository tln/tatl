from collections import namedtuple, OrderedDict
import re

class Block:
    def __init__(self, top, parent=None):
        self.top = top
        self.bot = OpList()
        self.parent = parent

    def __repr__(self):
        return '<block @%x parent=%r>' % (id(self), self.parent)

    def done(self):
        #print 'Done:', repr(self)
        self.top.combine(self.bot)
        self.bot = None
        return self.top

    def __del__(self):
        if self.bot:
            print 'Warning: Block.done() not called on', repr(self)

class Compilable:
    def addto(self, block):
        # Add one or more Ops to block.top / block.bottom
        pass

class Op:
    def code(self, target):
        # Return a Code instance
        return ''
    def check(self, warn, lvars, functions):
        # check the expression/op
        # lvars is the lvars up to this op in function.
        # May add rvars on self; any rvars on the op will
        # be added as parameters after this call
        pass

class Code(unicode):
    dedent = 0
    indent = 0

class Indent(Code):
    indent = 1

class Dedent(Code):
    dedent = 1

class DedentThenIndent(Code):
    dedent = 1
    indent = 1

class BasePart(Op):
    """Represents part of our AST. Renders early to py or js, keeps
    tracks of lvars and rvars of itself and children.
    """
    py = js = '*not implemented*'
    def __init__(self):
        self.lvars = []
        self.rvars = []

    def add(self, part):
        self.lvars.extend(part.lvars)
        self.rvars.extend(part.rvars)

    def __str__(self):
        #TODO remove
        print 'str called -> %r' % self.py
        return self.py

    def __repr__(self):
        return '<%s>' % self.out().replace('\n', ' ')

    Code = Code
    def code(self, target):
        assert target in ('py', 'js')
        return self.Code(getattr(self, target))

    type = ''
    def out(self):
        l = []
        py = self.code('py')
        js = self.code('js')
        if py == js:
            l.append('py/js: '+py)
        else:
            l.append('py: '+py)
            l.append('js: '+js)
        line = ''
        if self.type:
            line += 'type: %s ' % self.type
        if self.lvars:
            line += 'lvars: %s ' % ','.join(self.lvars)
        if self.rvars:
            line += 'rvars: %s ' % ','.join(self.rvars)
        line = line.rstrip()
        if line:
            l.append(line)
        return '\n'.join(l)

    def addto(self, block):
        block.top.add(self)

class ArgExpr(BasePart):
    fields = []
    lvarfields = []
    rvarfields = []
    noaddfields = []
    def __init__(self, *args):
        BasePart.__init__(self)
        assert len(args) == len(self.fields)
        d = dict(zip(self.fields, args))
        self.__dict__.update(d)
        self.lvars = [d[k] for k in self.lvarfields]
        self.rvars = [d[k] for k in self.rvarfields]

    def __repr__(self):
        n = self.__class__.__name__
        args = tuple(getattr(self, attr) for attr in self.fields)
        return n + str(args)

    def code(self, target):
        fmt = getattr(self, target+'fmt')
        return self.Code(fmt % self.__dict__)

class Part(BasePart):

    def __init__(self, pyfmt, jsfmt, *parts, **partkw):
        BasePart.__init__(self)
        pyfrags = {}
        jsfrags = {}
        if 'Code' in partkw:
            self.Code = partkw.pop('Code')
        for k, v in list(enumerate(parts)) + partkw.items():
            self.add(v)
            pyfrags[str(k)] = v.code('py')
            jsfrags[str(k)] = v.code('js')
        self.py = pyfmt % pyfrags
        self.js = jsfmt % jsfrags
        self.__dict__.update(partkw)

class ArgPart(BasePart):
    fields = []
    pyfmt = jsfmt = '*not implemented*'
    def __init__(self, *args):
        BasePart.__init__(self)
        assert len(args) == len(self.fields)
        self.__dict__.update(dict(zip(self.fields, args)))
        map(self.add, args)

    def code(self, target):
        fmt = getattr(self, target+'fmt')
        d = dict([
            (f, getattr(self, f).code(target))
            for f in self.fields
        ])
        return self.Code(fmt % d)

class List(BasePart):
    def __init__(self, partlist, join=', ', paren='%s'):
        BasePart.__init__(self)
        self.partlist = partlist
        self.join = join
        self.paren = paren
        map(self.add, partlist)

    def code(self, target):
        value = lambda s: s[target] if isinstance(s, dict) else s
        return value(self.paren) % value(self.join).join(
            p.code(target)
            for p in self.partlist
        )

class Lvar(BasePart):
    def __init__(self, lvar):
        BasePart.__init__(self)
        self.lvar = lvar
        self.lvars = [lvar]
        self.py = self.js = lvar
class Asgn(Part):
    def __init__(self, lvar, expr):
        if isinstance(lvar, basestring):
            lvar = Lvar(lvar)
        if isinstance(expr, basestring):
            expr = Expr([expr], expr, expr)
        fmt = '%(lvar)s = %(expr)s'
        Part.__init__(self, fmt, fmt, lvar=lvar, expr=expr)

class Expr(BasePart):
    def __init__(self, rvars, py, js=None):
        BasePart.__init__(self)
        self.py = py
        self.js = js or py
        self.rvars = rvars

class Value(BasePart):
    def __init__(self, py, js=None):
        BasePart.__init__(self)
        self.py = py
        self.js = js or py

class Impl(BasePart):
    "Reference to implementation variable"
    def __init__(self, py, js=None):
        BasePart.__init__(self)
        self.py = py
        self.js = js or py


class Wrap(BasePart):
    def __init__(self, part):
        BasePart.__init__(self)
        self.add(part)
        self.part = part
    def code(self, target):
        return self.part.code(target)

class Out:
    # mixin to namedtuples
    def out(self):
        l = []
        for k in self._fields:
            v = getattr(self, k)
            if v and isinstance(v, list):
                l += [('%s[%s]' % (k, ix), v.out() if hasattr(v, 'out') else str(v))
                      for ix, v in enumerate(v)]
            else:
                v = v.out() if hasattr(v, 'out') else str(v)
                l.append((k, v))
        n = max(len(lbl) for lbl, val in l)
        s = '\n' + ' '*n + '   '
        return '\n'.join(
            lbl.ljust(n)+' = '+val.replace('\n', s)
            for lbl, val in l
        )

#----------
class Pass(BasePart):
    js = '//pass'
    py = 'pass'
def join(fn):
    return lambda *args, **kw: '\n'.join(fn(*args, **kw))

class OpList:
    def __init__(self):
        self.ops = []

    def __nonzero__(self):
        return bool(self.ops)

    def check(self):
        for op in self.ops:
            try:
                assert isinstance(op.code('py'), Code)
            except Exception, e:
                print 'error:', op, e
                import pdb
                pdb.post_mortem()

    @join
    def view(self):
        for op in self.ops:
            try:
                indent = op.Code.indent-op.Code.dedent
            except:
                indent = 0
            yield '%2d %r' % (indent, op)

    @join
    def code(self, target):
        i = 0
        for op in self.ops:
            code = op.code(target)
            if not isinstance(code, Code):
                print 'op.code didnt return Code instance:', repr(op)
                code = Code(code)
            i -= code.dedent
            yield '    '*i + code
            i += code.indent

    def add(self, *ops):
        if not ops: return
        cur = self.ops
        if cur and cur[-1].Code.indent and ops[0].Code.dedent:
            cur.append(Pass())
        cur.extend(ops)

    def combine(self, other):
        self.ops.extend(other.ops)

    def optimize(self):
        for cls in self.optimizers():
            cls(self.ops).optimize()
        return self

    def optimizers(self):
        return []

