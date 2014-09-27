from collections import namedtuple, OrderedDict
import re

str_targets = {
    'py': repr,
    'js': lambda s: repr(s).lstrip('u')
}


class ModfinderBase:
    def module_spec(self, module, target):
        return module

class CodeState:
    depth = 0

    modfinder = ModfinderBase()

    def emitvar(self, op):
        """Return var for depth. As side effect, adjust depth:
        before when increasing, after when decreasing. Usually code expressions
        that need to decrease depth need to use the previous value.
        """
        assert op.adjust in (-1, 0, 1)
        self.depth += op.adjust
        result = '_emit%d' % (self.depth + (op.adjust < 0))
        return result

class Block:
    def __init__(self, top, parent=None):
        self.top = top
        self.bot = OpList()
        self.parent = parent

    def __repr__(self):
        return '<block @%x parent=%r>' % (id(self), self.parent)

    def done(self):
        self.top.combine(self.bot)
        self.bot = None
        return self.top

    def __del__(self):
        if self.bot:
            import sys
            print>>sys.stderr, 'Warning: Block.done() not called on', repr(self)

class Compilable:
    def addto(self, block):
        # Add one or more Ops to block.top / block.bottom
        pass

class Op:
    adjust = 0
    def code(self, target, state):
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
    py = js = None   # '*not implemented*'
    def __init__(self):
        self.lvars = []
        self.rvars = []

    def add(self, part):
        self.lvars.extend(part.lvars)
        self.rvars.extend(part.rvars)

    def __repr__(self):
        return '<%s>' % self.out().replace('\n', ' ')

    Code = Code
    def code(self, target, state):
        assert target in ('py', 'js')
        return self.Code(getattr(self, target))

    type = ''
    def out(self):
        l = []
        cs = CodeState()
        py = self.code('py', cs)
        js = self.code('js', cs)   # passing cs in a second time! double indent!
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

    def imports(self):
        return []

class ArgPart(BasePart):
    fields = []
    pyfmt = jsfmt = None #'*not implemented*'
    coerce = {}
    def __init__(self, *args):
        BasePart.__init__(self)
        assert len(args) == len(self.fields)
        self.d = []
        for field, arg in zip(self.fields, args):
            setattr(self, field, arg) # expose arg as passed, used by eg peepholers
            if not isinstance(arg, BasePart):
                arg = self.coerce[field](arg)
            self.add(arg)
            self.d.append((field, arg))

    def code(self, target, state):
        fmt = getattr(self, target+'fmt')
        d = {
            k: v.code(target, state)
            for k, v in self.d
        }
        d['emit'] = state.emitvar(self)
        out = self.Code(fmt % d)
        if target == 'js':
            assert not re.search("""u(['"]).*?\\1""", out)
        return out

class List(BasePart):
    def __init__(self, partlist, join=', ', paren='%s'):
        BasePart.__init__(self)
        self.partlist = partlist
        self.join = join
        self.paren = paren
        map(self.add, partlist)

    def code(self, target, state):
        value = lambda s: s[target] if isinstance(s, dict) else s
        return value(self.paren) % value(self.join).join(
            p.code(target, state)
            for p in self.partlist
        )

class Lvar(BasePart):
    def __init__(self, lvar):
        BasePart.__init__(self)
        self.lvar = lvar
        self.lvars = [lvar]
        self.py = self.js = lvar

class Rvar(BasePart):
    def __init__(self, rvar):
        BasePart.__init__(self)
        self.rvar = rvar
        self.rvars = [rvar]
        self.py = self.js = rvar

class Asgn(ArgPart):
    pyfmt = jsfmt = '%(lvar)s = %(expr)s'
    fields = ['lvar', 'expr']
    def __init__(self, lvar, expr):
        if isinstance(lvar, basestring):
            lvar = Lvar(lvar)
        if isinstance(expr, basestring):
            expr = Expr([expr], expr, expr)
        ArgPart.__init__(self, lvar, expr)

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

class Str(BasePart):
    def __init__(self, value):
        BasePart.__init__(self)
        self.value = value
        self.py = repr(value)
        self.js = self.py.lstrip('u')

class StrList(BasePart):
    def __init__(self, value):
        assert isinstance(value, list)
        BasePart.__init__(self)
        self.py = repr(value)
        self.js = '[%s]' % ', '.join(map(str_targets['js'], value))

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
    def code(self, target, state):
        return self.part.code(target, state)

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
        self.pyops = []
        self.jsops = []

    def __nonzero__(self):
        return bool(self.pyops)

    def check(self):
        for op in self.pyops:
            try:
                assert isinstance(op.code('py'), Code)
            except Exception, e:
                print 'error:', op, e
                import pdb
                pdb.post_mortem()

    @join
    def view(self):
        for op in self.pyops:
            try:
                indent = op.Code.indent-op.Code.dedent
            except:
                indent = 0
            yield '%2d %r' % (indent, op)

    @join
    def code(self, target, state):
        i = 0
        ops = self.pyops if target == 'py' else self.jsops
        for op in ops:
            code = op.code(target, state)
            if not isinstance(code, Code):
                print 'op.code didnt return Code instance:', repr(op)
                code = Code(code)
            i -= code.dedent
            yield '    '*i + code
            i += code.indent

    def add(self, *ops):
        if not ops: return
        for cur in self.pyops, self.jsops:
            if cur and cur[-1].Code.indent and ops[0].Code.dedent:
                cur.append(Pass())
            cur.extend(ops)

    def combine(self, other):
        self.pyops.extend(other.pyops)
        self.jsops.extend(other.jsops)

    def optimize(self):
        for cls in self.optimizers('py'):
            cls(self.pyops).optimize('py')
        for cls in self.optimizers('js'):
            cls(self.jsops).optimize('js')

    def optimizers(self, target):
        return []

    def imports(self):
        l = []
        for op in self.pyops:
            l += op.imports()
        return l
