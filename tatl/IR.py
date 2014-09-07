from tatl.OpList import *
from cgi import escape  # for pre-quoting

RESERVED = ['var']

def warn(*args):
    print 'WARN:', args

# --------- Compiler API
class Module:
    def __init__(self, source):
        self.block = Block(IR(), repr(self))
        self.functions = OrderedDict()
        self.imports = set()
        self.add_import('tatlrt')

    def startdef(self, funcdef):
        fn = self.functions[funcdef.name.lvar] = Function(self, funcdef)
        return fn

    def add_import(self, module):
        if module not in self.imports:
            self.imports.add(module)
            Import(module).addto(self.block)

    def done(self):
        for fn in self.functions.values():
            self.block.top.combine(fn.done())
        return self.block.done()

    def code(self, target):
        return self.block.top.code(target)

    def view(self):
        return self.block.top.view()

class Function:
    def __init__(self, module, funcdef):
        self.module = module
        self.name = funcdef.name
        self.init = Block(IR(), self.name.lvar+'@init')
        self.code = Block(IR(), self.name.lvar+'@code')
        self.args = funcdef.args
        funcdef.addto(self.init)

    def argnames(self):
        self.done()
        return [a.lvar for a in self.args.args]

    def add_params(self, params):
        #TODO check for duplicates
        map(self.args.add_arg, params)

    def block(self):
        return Block(self.code.top, self.name.lvar+'@block')

    def done(self):
        if self.code is None:
            # already called
            return self.init.top

        # Done is called after all Module functions have been created.
        # Optimize, create implicit parameters, let ops check.
        code = self.code.done()
        code.combine(self.init.bot)
        code.optimize()

        lvars = set(self.args.lvars) | self.module.imports | set(self.module.functions)
        hasvar = lvars.copy()
        for op in code.ops:
            if isinstance(op, FuncEnd):
                break
            op.check(warn, lvars, self.module.functions)
            for rvar in op.rvars:
                if rvar not in lvars:
                    #InitLocal(rvar).addto(self.init)
                    self.add_params([Lvar(rvar)])
                    hasvar.add(rvar)
                    lvars.add(rvar)
            lvars.update(op.lvars)
        InitLvars(lvars - hasvar).addto(self.init)

        self.init.bot = code
        self.code = None
        return self.init.done()

# ---------
class IR(OpList):
    def optimizers(self):
        # peephole imports IR, delay import to avoid circular import issues
        from tatl.peephole import optimizers
        return optimizers


# -------- Major constructs created by ExprSemantics
class Def(namedtuple('Def', 'name args result filters'), Out):
    def addto(self, block):
        block.top.add(
            FuncDef(self.name, self.args),
            FuncPreamble('attr')
            )
        if self.result:
            block.bot.add(
                Asgn('dot', Impl('_.result()')),
                Return(self.result),
            )
        else:
            block.bot.add(
                Return(Expr([], '_.result()')),
            )
        block.bot.add(
            FuncEnd(),
            *[Filter(self.name, filt) for filt in self.filters]
        )
        block.bot.add(Part('', 'exports.%(0)s = tatlrt._bind(%(0)s)', self.name))

class If(namedtuple('If', 'set test'), Out):
    def addto(self, block):
        for stmt in self.set:
            stmt.addto(block)
        block.top.add(IfStart(self.test))
        block.bot.add(IfEnd())
class Use(namedtuple('Use', 'set path arglist'), Out):
    def addto(self, block):
        for stmt in self.set:
            stmt.addto(block)

        block.top.add(UseStart())

        if self.arglist is None:
            end = UseEndAuto(self.path)
        else:
            end = UseEndArgs(self.path, List(self.arglist))

        block.bot.add(UseEnd0(), end)
class For(namedtuple('For', 'set stmt'), Out):
    def addto(self, block):
        for stmt in self.set:
            stmt.addto(block)
        block.top.add(self.stmt)
        block.bot.add(ForEnd())

class Set(namedtuple('Set', 'var filters'), Out):
    def addto(self, block):
        block.top.add(SetStart())
        block.bot.add(
            SetEnd(self.var),
            *[Filter(self.var, filt) for filt in self.filters]
        )


class Top(namedtuple('Top', 'set exprs emit rest'), Out):
    def addto(self, block):
        #import pdb
        #pdb.set_trace()

        self.add_setup(block)
        e = self.emit
        if not e: return
        if e.type != 'placeholder':
            e = EmitQExpr(e)
        e.addto(block)

    def add_setup(self, block):
        for stmt in self.set:
            stmt.addto(block)
        for expr in self.exprs:
            expr.addto(block)

    def boolable(self):
        return self.emit.type != 'placeholder' and not self.rest

class BoolAttr(namedtuple('BoolAttr', 'attr top'), Out):
    def addto(self, block):
        self.top.add_setup(block)
        block.top.add(
            IfStart(self.top.emit),
            EmitQText(' '+self.attr),
            IfEnd()
        )
# -------- Additional constructs
class StarExp(Wrap):
    type = 'starexp'

class StarArg(BasePart):
    py = js = '*star*'
STAR_ARG = StarArg()
class Filt(BasePart):
    # |filter calls are looked up in a special namespace,
    # tatlrt.filter.
    filtname = None   # built in filt name
    def __init__(self, expr):
        BasePart.__init__(self)
        if isinstance(expr, (BuiltinPath, VarPath)):
            self.expr = self.make_lookup_expr(expr)
        elif isinstance(expr, Call) and isinstance(expr.fn, (BuiltinPath, VarPath)):
            self.expr = Call(self.make_lookup_expr(expr.fn), expr.args)
        else:
            # ExtPath or Call with ExtPath
            self.expr = expr
        self.add(self.expr)

    def make_lookup_expr(self, path):
        import tatlrt
        fn = tatlrt.filters.__dict__.get(path.paths[0])
        if fn:
            expr = '.'.join(['tatlrt', 'filters', fn.__name__] + path.paths[1:])
            path = Expr([], expr, expr)
            self.filtname = fn.__name__
        return path

    def code(self, target):
        return self.expr.code(target)


class FiltExp(ArgPart):
    fields = ['expr', 'filt']
    pyfmt = '%(filt)s( %(expr)s )'
    jsfmt = '%(filt)s( %(expr)s )'
def Path(paths):
    import tatlrt
    if paths[0] in tatlrt.__all__:
        return BuiltinPath(paths)
    else:
        return VarPath(paths)
class BasePath(BasePart):
    def args(self, functions):
        import inspect
        try:
            d = {}
            exec 'import tatlrt' in d, d
            func = eval(self.code('py'), d, d)
            args, _, _, _ = inspect.getargspec(func)
            if list in map(type, args):
                # cant handle auto in this case
                warn("%s args are not compatible with use=")
                args = None
        except:
            warn("Can't find args for %r", self)
            args = None
        return args

class BuiltinPath(BasePath):
    def __init__(self, paths):
        BasePart.__init__(self)
        self.paths = paths

    def code(self, target):
        return 'tatlrt.' + '.'.join(self.paths)

class VarPath(BasePath):
    def __init__(self, paths):
        BasePart.__init__(self)
        self.paths = paths
        self.rvars = [paths[0]]

    def code(self, target):
        # Same for py and js
        paths = self.paths[:]
        var = paths.pop(0)
        if not paths:
            return var
        elif len(paths) == 1:
            path = paths[0]
            return '_.get1(%s, %r)' % (var, path)
        else:
            return '_.get(%s, %r)' % (var, paths)



    def args(self, functions):
        fn = functions.get(self.paths[0])
        if fn is None: return None
        #import pdb
        #pdb.set_trace()
        return fn.argnames()

class ExtPath(Expr, BasePath):
    def __init__(self, module, path):
        self.module = module
        self.path = path
        Expr.__init__(self, [], '_.load(%r, %r)' % (module, path))

class Lookup(ArgPart):
    fields = ['expr', 'key']
    pyfmt = jsfmt = '_.get1(%(expr)s, %(key)s)'

class Call(ArgPart):
    fields = ['fn', 'args']
    pyfmt = jsfmt = '%(fn)s(%(args)s)'
    def __init__(self, fn, args):
        if not isinstance(args, List): args = List(args)
        ArgPart.__init__(self, fn, args)

class Args(BasePart):
    def __init__(self, args):
        BasePart.__init__(self)
        self.args = args
        try:
            self.addix = self.args.index(STAR_ARG)
            del self.args[self.addix]
        except:
            self.addix = len(self.args)-1
        map(self.add, self.args)
        self.calc()

    def calc(self):
        self.py = ', '.join(p.code('py')+'=None' for p in self.args) + ', **_kw'
        self.py = self.py.lstrip(', ')
        self.js = ', '.join(p.code('js') for p in self.args)

    def add_arg(self, lvar):
        assert lvar.lvars
        self.args.insert(self.addix, lvar)
        self.add(lvar)
        self.calc()

class Placeholder(BasePart):
    type = 'placeholder'
    def __init__(self, ast):
        BasePart.__init__(self)
        op, self.name = ast
        self.method = {'*':'star','++':'plusplus'}[op]
        self.py = '%s, _emit = _.%s()' % (self.name, self.method)
        self.js = '%s = _.%s()' % (self.name, self.method)
        self.lvars = [self.name]


class RangeIncl(ArgPart):
    fields = ['n', 'm']
    pyfmt = 'tatlrt.range_incl(%(n)s, %(m)s)'
    jsfmt = 'tatlrt.range(%(n)s, %(m)s, true)'

class RangeExcl(ArgPart):
    fields = ['n', 'm']
    pyfmt = 'tatlrt.range_excl(%(n)s, %(m)s)'
    jsfmt = 'tatlrt.range(%(n)s, %(m)s, false)'

# -------- Bases/helpers for Ops
class _Val(ArgExpr): fields = ['val']
class _Var(ArgExpr): fields = ['var']
class _Expr(ArgPart): fields = ['expr']
class _End(BasePart):
    py = '# end'
    js = '}'
    Code = Dedent


# -------- Emitting Ops
class EmitQText(_Val):
    pyfmt = '_emit(%(val)r)'
    jsfmt = '_.emit(%(val)r);'

class _Emit(ArgPart):
    fields = ['expr']
    def fmtexpr(self):
        return self.expr
class EmitQExpr(_Emit):             # QE Quoted Expression
    pyfmt = '_emit(_q(%(expr)s))'
    jsfmt = '_.emit(_.q(%(expr)s));'
    def fmtexpr(self):
        return Part('_q(%(0)s)', '_.q(%(0)s)', self.expr)
class EmitUExpr(_Emit):             # UE Unquoted Expression
    pyfmt = '_emit(unicode(%(expr)s))'
    jsfmt = '_.emit(%(expr)s);'
# -------- Module/function Ops
class ModPreamble(BasePart):
    py = '# -*- coding:UTF-8 -*-'
    js = ''
class FuncDef(ArgPart):
    fields = ['name', 'args']
    Code = Indent
    pyfmt = 'def %(name)s(%(args)s):'
    jsfmt = 'function %(name)s(%(args)s) {'
    def code(self, target):
        code = ArgPart.code(self, target)
        if target == 'js':
            for arg in self.args.args:
                code += '\n    %(arg)s = %(arg)s || this.%(arg)s' % {'arg': arg.lvar}
        return self.Code(code)

class FuncPreamble(ArgExpr):
    fields = ['context']
    pyfmt = '_, _q, _emit = tatlrt._ctx(%(context)r)'
    jsfmt = 'var _ = tatlrt._ctx(%(context)r);'

class FuncEnd(_End):
    js = '}'
class Return(ArgPart):
    fields = ['expr']
    jsfmt = pyfmt = 'return %(expr)s'

class Import(ArgExpr):
    pyfmt = 'import %(arg)s'
    jsfmt = "var %(arg)s = require(%(arg)r)"    # hack! ./t_tmpl
    lvarfields = fields = ['arg']

class InitLocal(_Var):  # SV Setup local vars
    lvarfields = ['var']
    pyfmt = '%(var)s = _kw.get(%(var)r)'
    jsfmt = 'var %(var)s = this.%(var)s'


class InitLvars(BasePart):  # SV Setup local vars
    def __init__(self, vars):
        BasePart.__init__(self)
        v = ', '.join(vars)
        self.py = v and ('# locals: ' + v)
        self.js = v and ('var ' + v)
    def addto(self, block):
        if self.js:
            block.top.add(self)

class Filter(ArgPart):
    fields = ['name', 'filt']
    pyfmt = jsfmt = '%(name)s = %(filt)s(%(name)s)'
# -------- If
class IfStart(ArgPart):                 # IS If start
    fields = ['test']
    Code = Indent
    pyfmt = 'if %(test)s:'
    jsfmt = 'if (%(test)s) {'
class IfEnd(_End): pass
class Else(BasePart):
    Code = DedentThenIndent
    py = 'else:'
    js = '} else {'
class Elif(IfStart):
    Code = DedentThenIndent
    pyfmt = 'elif %(test)s:'
    jsfmt = '} else if (%(test)s) {'

class ElideStart(BasePart):                 # SS Skip (elide) start
    py = '_emit = _.elidestart()'
    js = '_.elidestart()'
class ElideEnd(BasePart):                 # SE Skip (elide) end
    py = '_noelide, _content, _emit = _.elidecheck()'
    js = '_content = _.pop();'
    def addto(self, block):
        block.top.add(
            self,
            IfStart(Expr([], '_noelide', '_.elidecheck()')),
            EmitUExpr(Impl('_content')),
        )
        block.bot.add(IfEnd())

# -------- For
class _Tmp(ArgPart):
    tmp = 0
    def __init__(self, *args):
        tmp = Lvar('_tmp%d' % _Tmp.tmp)
        _Tmp.tmp += 1
        ArgPart.__init__(self, *args+(tmp,))

class For1(_Tmp):            # F1 for loop 1 var start (pass pair as arg)
    fields = ['n1', 'expr', 'tmp']
    pyfmt = 'for %(n1)s in _.iter(%(expr)s):'
    jsfmt = 'for (_i in (%(tmp)s = %(expr)s)) { %(n1)s = %(tmp)s[_i];'
    Code = Indent

class For2(_Tmp):         # F2 for loop 2 var start (pass triple as arg)
    fields = ['n1', 'n2', 'expr', 'tmp']
    pyfmt = 'for %(n1)s, %(n2)s in _.items(%(expr)s):'
    jsfmt = '''for (var Ti = 0, Tk = _.keys(T = %(expr)s), Tn = Tk.length; Ti < Tn; Ti++) {
    %(n2)s = T[%(n1)s = Tk[Ti]];'''.replace('T', '%(tmp)s')
    Code = Indent
class ForEnd(_End): pass               # FD for loop done
# -------- Set
class SetStart(BasePart):                 # LS Local (set) start
    py = '_emit = _.push()'
    js = '_.push()'
class SetEnd(ArgPart):
    fields = ['var']
    pyfmt = '%(var)s, _emit = _.pop()'
    jsfmt = '%(var)s = _.pop()'

# -------- Use
class UseStart(BasePart):                 # CS Call (use) start
    py = js = '_emit = _.push()'
class UseEnd0(BasePart):
    py = 'inner, _emit = _.pop()'
    js = 'inner = _.pop()'
    def __init__(self):
        BasePart.__init__(self)
        self.lvars = ['inner']
class UseEndAuto(BasePart):
    def __init__(self, expr):
        BasePart.__init__(self)
        self.expr = expr
        self.add(expr)

    def check(self, warn, lvars, functions):
        self.args = self.expr.args(functions)
        if not self.args:
            # maybe this should just be an error.
            warn("Could not find args for %s", self.expr)
        else:
            for arg in self.args:
                if arg not in lvars:
                    warn("Use arg %s not defined -- adding as parameter" % arg)
                    self.rvars.append(arg)

    def code(self, target):
        if self.args:
            expr = Call(self.expr, [Expr([], a, a) for a in self.args])
        else:
            expr = Part(
                '_emit(_.applyauto(%(0)s, locals()))',
                'var func = %(0)s; _.emit(eval(_.applyautoexpr("func", func)))',
                self.expr)
        return expr.code(target)


class UseEndArgs(ArgPart):
    fields = ['expr', 'callargs']
    pyfmt = '_emit(_.applyargs(%(expr)s, %(callargs)s))'
    jsfmt = '_.emit(_.applyargs(this, %(expr)s, %(callargs)s))'

