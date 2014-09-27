from tatl.OpList import *
from cgi import escape  # for pre-quoting
import os

RESERVED = ['var']

def warn(*args):
    print 'WARN:', args

# --------- Compiler API
class Modfinder(ModfinderBase):
    def __init__(self, source):
        self.base = os.path.split(source)[0]
        self.extensions = ['tatl', 'html']    # plus 'py' or 'js'

    def module_spec(self, module, target):
        for extn in self.extensions + [target]:
            modsource = os.path.join(self.base, module+'.'+extn)
            if os.path.exists(modsource):
                return './'+module if target == 'js' else module     # python.... import .name?
        return module

class Modformat:
    def addto(self, modname, imports, block):
        block.top.add(CommonJSModuleStart())
        block.bot.add(CommonJSModuleEnd(modname))

class Module:
    def __init__(self, source, modname, modfinder, modformat):
        self.block = Block(IR(), repr(self))
        self.functions = OrderedDict()
        self.modformat = modformat
        self.source = source
        self.modname = modname
        self.modfinder = modfinder
        self.imports = []
        self.add_import('tatlrt')

    def add_import(self, module):
        if module not in self.imports:
            self.imports.append(module)

    def startdef(self, funcdef):
        fn = self.functions[funcdef.name.lvar] = Function(self, funcdef)
        return fn

    def done(self):
        self.modformat.addto(self.modname, self.imports, self.block)
        for fn in self.functions.values():
            self.block.top.combine(fn.done())
        return self.block.done()

    def code(self, target):
        state = CodeState()
        state.modfinder = self.modfinder
        return self.block.top.code(target, state)

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

        lvars = set(self.args.lvars) | set(self.module.imports) | set(self.module.functions)
        hasvar = lvars.copy()
        for op in code.pyops:
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
    def optimizers(self, target):
        # peephole imports IR, delay import to avoid circular import issues
        from tatl.peephole import optimizers
        return optimizers[target]

# -------- Modue constructs
class CommonJSModuleStart(BasePart):
    py = 'import tatlrt'
    js = "var tatlrt = require('tatlrt');"

class CommonJSModuleEnd(BasePart):
    py = ''
    def __init__(self, modname):
        self.js = "tatlrt.add_template('%s', exports);" % modname

class AMDModuleStart(BasePart):
    # Note: this is not a usable option, yet. Also the Python logic is different
    # and should be separated.
    def __init__(self, modname, imports):
        BasePart.__init__(self)
        self.py = 'import ' + ', '.join(imports)
        self.js = '''\
if (typeof define !== 'function') { var define = require('amdefine')(module) }
define([%s], function (%s) {
var exports = {};
tatlrt.add_template('%s', exports);
''' % (', '.join(map(str_targets['js'], imports)), ', '.join(imports), modname)

class AMDModuleEnd(BasePart):
    py = ''
    js = 'return exports;});\n'

# -------- Major constructs created by ExprSemantics
class Def(namedtuple('Def', 'name args result filters'), Out):
    def addto(self, block):
        block.top.add(
            FuncDef(self.name, self.args),
            FuncPreamble('attr')
            )
        if self.result:
            block.bot.add(
                Asgn('dot', Result()),
                Return(self.result),
            )
        else:
            block.bot.add(
                Return(Result()),
            )
        block.bot.add(
            FuncEnd(),
            *[Filter(self.name, filt) for filt in self.filters]
        )
        block.bot.add(
            BindAndExport(self.name)
        )

class Result(ArgPart):
    fields = []
    pyfmt = 'tatlrt.safejoin(%(emit)s)'
    jsfmt = 'tatlrt.safe(%(emit)s)'

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

    def code(self, target, state):
        return self.expr.code(target, state)


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
            func = eval(self.code('py', None), d, d)
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
        self.mod = module_for_builtin(self.paths[0])
        self.add(self.mod)

    def code(self, target, state):
        m = self.mod.code(target, state)
        return '.'.join([m]+self.paths)

def module_for_builtin(builtin):
    # Parse js files??
    import tatlrt
    if builtin in tatlrt.__js_submodules__:
        return BuiltinImport('_'+builtin, 'tatlrt/js/tatlrt/'+builtin)
    return Impl('tatlrt')

class BuiltinImport(BasePart):
    def __init__(self, lvar, module):
        BasePart.__init__(self)
        self.lvars = [lvar]
        assert '"' not in module
        self.js = "(%s = %s || require('%s'))" % (lvar, lvar, module)
        self.py = 'tatlrt'

class VarPath(BasePath):
    def __init__(self, paths):
        BasePart.__init__(self)
        self.paths = paths
        self.rvars = [paths[0]]

    def code(self, target, state):
        # Same for py and js
        paths = self.paths[:]
        var = paths.pop(0)
        if not paths:
            return var
        elif len(paths) == 1:
            path = paths[0]
            return '_.get1(%s, %s)' % (var, str_targets[target](path))
        else:
            return '_.get(%s, [%s])' % (var, ', '.join(map(str_targets[target], paths)))

    def args(self, functions):
        fn = functions.get(self.paths[0])
        if fn is None: return None
        return fn.argnames()

class ExtPath(BasePath):
    def __init__(self, module, path):
        self.module = module
        if isinstance(path, list):
            self.path = StrList(path)
        BasePath.__init__(self)

    def code(self, target, state):
        module = state.modfinder.module_spec(self.module, target)
        module = str_targets[target](module)
        path = self.path.code(target, state)
        fmt = {'py': '_.load(%s, %s)', 'js': '_.get(require(%s), %s)'}[target]
        return fmt % (module, path)

    def imports(self):
        return [self.module]

class AsgnIf(ArgPart):
    fields = ['var', 'expr']
    pyfmt = '%(var)s = %(var)s or %(expr)s'
    jsfmt = '%(var)s = %(var)s || %(expr)s'

class Member(ArgPart):
    fields = ['key', 'val']
    pyfmt = jsfmt = '%(key)s: %(val)s'

class Bool(ArgPart):
    fields = ['expr']
    pyfmt = 'bool(%(expr)s)'
    jsfmt = 'tatlrt.bool(%(expr)s)'

class Ternary(ArgPart):
    pyfmt = '%(true)s if %(test)s else %(false)s'
    jsfmt = '%(test)s ? %(true)s : %(false)s'
    fields = ['test', 'true', 'false']

Null = Expr([], 'None', 'null')

class Or(ArgPart):
    fields = ['test', 'false']
    pyfmt = '(%(test)s or %(false)s)'
    jsfmt = '((%(test)s) || (%(false)s))'

class OpChain(BasePart):
    def __init__(self, args, ops):
        BasePart.__init__(self)
        map(self.add, args)
        self.args = args
        self.ops = ops

    def code(self, target, state):
        # Make list of combined size
        parts = self.args + self.ops
        # Replace every 2nd element offset 1 with an op
        parts[1::2] = self.ops
        if target == 'py' or len(self.args) == 2:
            # Replace every 2nd element with code
            parts[::2] = [a.code(target, state) for a in self.args]
        else:
            # a == b == c  -->  a == (_tmp = b) && _tmp == c
            # First and last args become unwrapped code
            parts[0] = self.args[0].code(target, state)
            parts[-1] = self.args[-1].code(target, state)
            # Wrap middle args with temp assignment so that expression is
            # not executed twice
            parts[2:-2:2] = [
                '(_tmp%d = %s) && _tmp%d' % (i, a.code(target, state), i)
                for i, a in enumerate(self.args[1:-1])
            ]
        return ' '.join(parts)

class Lookup(ArgPart):
    fields = ['expr', 'key']
    pyfmt = jsfmt = '_.get1(%(expr)s, %(key)s)'

class Call(ArgPart):
    fields = ['fn', 'args']
    pyfmt = jsfmt = '%(fn)s(%(args)s)'
    coerce = {'args': List}

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
        self.py = ', '.join(p.code('py', None)+'=None' for p in self.args) + ', **_kw'
        self.py = self.py.lstrip(', ')
        self.js = ', '.join(p.code('js', None) for p in self.args)

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
        self.py = '%s, _emit, _b = _.%s()' % (self.name, self.method)
        self.js = '%s = _.%s()' % (self.name, self.method)
        self.lvars = [self.name]

class RangeIncl(ArgPart):
    fields = ['n', 'm']
    pyfmt = '_.range_incl(%(n)s, %(m)s)'
    jsfmt = 'tatlrt.range(%(n)s, %(m)s, true)'

class RangeExcl(ArgPart):
    fields = ['n', 'm']
    pyfmt = '_.range_excl(%(n)s, %(m)s)'
    jsfmt = 'tatlrt.range(%(n)s, %(m)s, false)'

class Regex(ArgPart):
    fields = ['expr']
    def __init__(self, pat, negate, expr):
        re.compile(pat)  # crash on invalid pattern
        pat = pat.replace('%', '%%')
        self.pyfmt = ('not ' if negate else '') + '_.search(%r, %%(expr)s)' % pat
        self.jsfmt = ('!' if negate else '') + '_.search(/%s/, %%(expr)s)' % pat
        ArgPart.__init__(self, expr)

class _End(BasePart):
    py = '# end'
    js = '}'
    Code = Dedent

# -------- Emitting Ops
class EmitQText(ArgPart):
    fields = ['val']
    coerce = {'val': Str}
    pyfmt = '%(emit)s(%(val)s)'
    jsfmt = '%(emit)s += %(val)s;'

class _Emit(ArgPart):
    fields = ['expr']
    def fmtexpr(self):
        return self.expr
class EmitQExpr(_Emit):
    pyfmt = '%(emit)s(_q(%(expr)s))'
    jsfmt = '%(emit)s += _.q(%(expr)s);'
    def fmtexpr(self):
        return QExpr(self.expr)
class EmitUExpr(_Emit):
    pyfmt = '%(emit)s(u"%%s" %% %(expr)s)'
    jsfmt = '%(emit)s += %(expr)s;'

class QExpr(ArgPart):
    fields = ['expr']
    pyfmt = '_q(%(expr)s)'
    jsfmt = '_.q(%(expr)s)'

# -------- Module/function Ops
class ModPreamble(BasePart):
    py = '# -*- coding:UTF-8 -*-'
    js = ''
class FuncDef(ArgPart):
    fields = ['name', 'args']
    Code = Indent
    pyfmt = 'def %(name)s(%(args)s):'
    jsfmt = 'function %(name)s(%(args)s) {'
    def code(self, target, state):
        code = ArgPart.code(self, target, state)
        if target == 'js':
            for arg in self.args.args:
                code += '\n    %(arg)s = %(arg)s || this.%(arg)s' % {'arg': arg.lvar}
        return self.Code(code)

class FuncPreamble(ArgPart):
    fields = ['context']
    coerce = {'context': Str}
    pyfmt = '_, _q = tatlrt.ctx(%(context)s); %(emit)s = tatlrt.Buf()'
    jsfmt = 'var _ = tatlrt.ctx(%(context)s), %(emit)s = "";'

class FuncEnd(_End):
    pass

class BindAndExport(ArgPart):
    fields = ['name']
    coerce = {'name': Rvar}
    pyfmt = ""
    jsfmt = "exports.%(name)s = tatlrt._bind(%(name)s)"


class Return(ArgPart):
    fields = ['expr']
    jsfmt = pyfmt = 'return %(expr)s'

class Import(ArgPart):
    pyfmt = 'import %(arg)s'
    jsfmt = "var %(arg)s = require('%(arg)s')"    # hack! ./t_tmpl
    fields = ['arg']
    coerce = {'arg': Lvar}

class InitLocal(ArgPart):
    fields = ['var']
    coerce = {'var': Lvar}
    pyfmt = '%(var)s = _kw.get(%(var)s)'
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
    coerce = {'name': Lvar}
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

class ElideStart(ArgPart):
    adjust = 1
    fields = []
    pyfmt = '%(emit)s = _.elidestart()'
    jsfmt = '_.elidestart(); %(emit)s = "";'

class ElideEnd(ArgPart):
    adjust = -1
    pyfmt = '_noelide, _content = _.elidecheck(%(emit)s)'
    jsfmt = '_content = %(emit)s;'
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

class For1(_Tmp):
    fields = ['n1', 'expr', 'tmp']
    pyfmt = 'for %(n1)s in _.iter(%(expr)s):'
    jsfmt = '''for (var Ti = 0, T = _.iter(%(expr)s), Tn = T.length; Ti < Tn; Ti++) { %(n1)s = T[Ti];'''.replace('T', '%(tmp)s')
    Code = Indent
    def pragma(self, pragma):
        pass

class For2(_Tmp):
    fields = ['n1', 'n2', 'expr', 'tmp']
    pyfmt = 'for %(n1)s, %(n2)s in _.items(%(expr)s):'
    pyuns = pyfmt.replace('items(', 'itemsUnsorted(')
    jsfmt = '''for (var Ti = 0, Tk = _.keys(T = %(expr)s), Tn = Tk.length; Ti < Tn; Ti++) {
    %(n2)s = T[%(n1)s = Tk[Ti]];'''.replace('T', '%(tmp)s')
    jsuns = jsfmt.replace('keys(', 'keysUnsorted(')
    Code = Indent

    def pragma(self, pragma):
        if pragma == 'unsorted':
            self.pyfmt = self.pyuns
            self.jsfmt = self.jsuns

class ForEnd(_End): pass

# -------- Set
class SetStart(ArgPart):
    fields = []
    adjust = 1
    pyfmt = '%(emit)s = tatlrt.Buf()'
    jsfmt = '%(emit)s = "";'

class SetEnd(ArgPart):
    fields = ['var']
    adjust = -1
    pyfmt = '%(var)s = tatlrt.safejoin(%(emit)s)'
    jsfmt = '%(var)s = tatlrt.safe(%(emit)s);'

# -------- Use
class UseStart(ArgPart):
    adjust = 1
    fields = []
    pyfmt = '%(emit)s = tatlrt.Buf()'
    jsfmt = '%(emit)s = "";'

class UseEnd0(ArgPart):
    adjust = -1
    fields = []
    pyfmt = 'inner = tatlrt.safejoin(%(emit)s)'
    jsfmt = 'inner = tatlrt.safe(%(emit)s);'
    def __init__(self):
        ArgPart.__init__(self)
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

    def code(self, target, state):
        if self.args:
            expr = EmitQExpr(Call(self.expr, [Expr([], a, a) for a in self.args]))
        else:
            expr = ApplyAuto(self.expr)
        return expr.code(target, state)

class ApplyAuto(ArgPart):
    fields = ['expr']
    pyfmt = '%(emit)s(_.applyauto(%(expr)s, locals()))'
    jsfmt = 'var _func = %(expr)s; %(emit)s += eval(_.applyautoexpr("_func", _func));'

class UseEndArgs(ArgPart):
    fields = ['expr', 'callargs']
    pyfmt = '%(emit)s(_.applyargs(%(expr)s, %(callargs)s))'
    jsfmt = '%(emit)s += _.applyargs(this, %(expr)s, %(callargs)s)'
