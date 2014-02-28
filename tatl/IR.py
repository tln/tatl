from tatl.OpList import *
from cgi import escape  # for pre-quoting

RESERVED = ['var']

# --------- Compiler API
class Module:
    def __init__(self, source):
        self.block = Block(IR())
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
        self.code = Block(IR())
        self.init = Block(IR())
        self.args = funcdef.args
        funcdef.addto(self.init)
            
    def add_params(self, params):
        #TODO check for duplicates
        map(self.args.add_arg, params)
    
    def block(self):
        return Block(self.code.top)
        
    def done(self):
        code = self.code.done()
        code.combine(self.init.bot)
        code.optimize()

        lvars = set(self.args.lvars) | self.module.imports | set(self.module.functions)
        hasvar = lvars.copy()
        for op in code.ops:
            if isinstance(op, FuncEnd):
                break
            for rvar in op.rvars:
                if rvar not in lvars:
                    InitLocal(rvar).addto(self.init)
                    hasvar.add(rvar)
                    lvars.add(rvar)
            lvars.update(op.lvars)
        InitLvars(lvars - hasvar).addto(self.init)
        
        self.init.bot = code
        self.code = None
        return self.init.done()

# -------- Major constructs created by ExprSemantics
class FuncDef(ArgPart):
    fields = ['name', 'args']
    Code = Indent
    pyfmt = 'def %(name)s(%(args)s):'
    jsfmt = 'function %(name)s(%(args)s) {'
    def __init__(self, name, args, result, filters):
        if args is None:
            args = Args([STAR_ARG])
        ArgPart.__init__(self, Lvar(name), args)
        self.result = result
        self.filters = filters
        
    def addto(self, block):
        block.top.add(self,
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
        block.bot.add(UseEnd0())
        
        if self.arglist is None:
            end = UseEndAuto(self.path)
        else:
            end = UseEndArgs(self.path, List(self.arglist))
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
        if self.emit:
            if self.emit.type == 'star':
                expr.addto(block)
            else:
                EmitQExpr(self.emit).addto(block)
        
    def add_setup(self, block):
        for stmt in self.set:
            stmt.addto(block)
        for expr in self.exprs:
            expr.addto(block)

    def boolable(self):
        return self.emit.type != 'star' and not self.rest

class BoolAttr(namedtuple('BoolAttr', 'attr top'), Out):
    def addto(self, block):
        self.top.add_setup(block)
        block.top.add(
            IfStart(self.top.emit),
            EmitQText(' '+self.attr),
            IfEnd()
        )
# -------- Additional Semantics created constructs
class StarExp(Wrap):
    type = 'starexp'
 
class StarArg(BasePart):
    py = js = '*star*'
STAR_ARG = StarArg()

def Path(paths):
    import tatlrt
    if paths[0] in tatlrt.__all__:
        return BuiltinPath(paths)
    else:
        return VarPath(paths)

class BuiltinPath(BasePart):
    def __init__(self, paths):
        BasePart.__init__(self)
        self.paths = paths
        
    def code(self, target):
        return 'tatlrt.' + '.'.join(self.paths)

class VarPath(BasePart):
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

class Lookup(ArgPart):
    fields = ['expr', 'key']
    pyfmt = jsfmt = '_.get1(%(expr)s, %(key)s)'

class Call(ArgPart):
    fields = ['fn', 'args']
    pyfmt = jsfmt = '%(fn)s(%(args)s)'
    def __init__(self, fn, args):
        ArgPart.__init__(self, fn, List(args))

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
        self.type = {'*':'star','++':'plusplus'}[op]
        self.py = self.js = '%s = _.%s()' % (self.name, self.type)
        self.lvars = [self.name]


class RangeIncl(ArgPart):
    fields = ['n', 'm']
    pyfmt = 'tatlrt.range_incl(%(n)s, %(m)s)'
    jsfmt = 'tatlrt.range(%(n)s, %(m)s, true)'

class RangeExcl(ArgPart):
    fields = ['n', 'm']
    pyfmt = 'tatlrt.range_excl(%(n)s, %(m)s)'
    jsfmt = 'tatlrt.range(%(n)s, %(m)s, false)'
        
# --------
class _Val(ArgExpr): fields = ['val']
class _Var(ArgExpr): fields = ['var']
class _Expr(ArgPart): fields = ['expr']

class _End(BasePart):
    py = '# end'
    js = '}'
    Code = Dedent

class EmitQText(_Val):
    pyfmt = '_emit(%(val)r)'
    jsfmt = '_.emit(%(val)r);'

class Filter(ArgPart):
    fields = ['name', 'filt']
    pyfmt = jsfmt = '%(name)s = %(filt)s(%(name)s)'
    
class ModPreamble(BasePart):
    py = '# -*- coding:UTF-8 -*-'
    js = ''
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

class _Emit(ArgPart):
    fields = ['expr']
class EmitQExpr(_Emit):             # QE Quoted Expression
    pyfmt = '_emit(_q(%(expr)s))'
    jsfmt = '_.emit(_.q(%(expr)s));'
class EmitUExpr(_Emit):             # UE Unquoted Expression
    pyfmt = '_emit(unicode(%(expr)s))'
    jsfmt = '_.emit(%(expr)s);'
#class _QV(EmitQ, _Var):              # QV Quoted local Var
#    pyfmt = jsfmt = '_emit(_q(%(var)s))'
#class _UV(EmitU, _Var):              # UV Unquoted local Var
#    pyfmt = jsfmt = '_emit(%(var)s)'

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
    jsfmt = 'for (%(n1)s in (_tmp = %(expr)s)) { %(n2)s = _tmp[%(n1)s];'
    Code = Indent  
class ForEnd(_End): pass               # FD for loop done
    

class SetStart(BasePart):                 # LS Local (set) start
    py = '_emit = _.push()'
    js = '_.push()'
class SetEnd(ArgPart):
    fields = ['var']
    pyfmt = '%(var)s, _emit = _.pop()'
    jsfmt = '%(var)s = _.pop()'

class UseStart(BasePart):                 # CS Call (use) start
    py = js = '_emit = _.push()'
class UseEnd0(BasePart):
    py = 'dot, _emit = _.pop()'
    js = 'dot = _.pop()'
    lvars = ['dot']
class UseEndAuto(ArgPart):
    fields = ['expr']
    pyfmt = '_emit(_.applyauto(%(expr)s, locals()))'
    jsfmt = '*not implemented*'
class UseEndArgs(ArgPart):
    fields = ['expr', 'callargs']
    pyfmt = jsfmt = '_emit(_.applyargs(%(expr)s, %(callargs)s))'

class CombineC(Peepholer):
    cls = EmitQText
    def optimize_run(self, ops):
        v = ''.join([op.val for op in ops])
        if not v: return []
        ops[-1].val = v
        return ops[-1:]

class CombineEmits(Peepholer):
    cls = (_Emit, EmitQText)
    def optimize_run(self, ops):
        if len(ops) < 2: return
            
        exprs = [repr(op.val) if op.name == 'C' else op.code()[6:-1] # strip off _emit( )
                 for op in ops]
                 
        # gross...
        op = EMITTRICK1(exprs)
        return [op]

class CombineEmitsFmt(Peepholer):
    cls = (_Emit, EmitQText)
    def optimize_run(self, ops):
        if len(ops) < 2: return
        fmt = ''
        exprs = []
        for op in ops:
            if op.name in ('U', 'C'):
                fmt += op.val.replace('%', '%%')
            else:
                fmt += '%s'
                exprs.append(op.code()[6:-1]) # strip off _emit( )

        expr = '%r %% (%s)' % (fmt, ', '.join(exprs))
        op = UE(expr)
        return [op]


class HoistQuote(StartEndPeepholer):
    "Non-functional -- hoist quoting into _.iter. Doesn't help bigtable.py that much..."
    start = ()  #FOR2   # s/bFor
    middle = (_Emit, EmitQText)
    end = () #ENDFOR
    
    def optimize_run(self, ops):
        # check that the EmitQ expressions match loop names
        # make mods as we go; throw them away if we find out its not a match
        for i, op in enumerate(ops):
            if i == 0:
                n1, n2, rexpr = ops[0]
                ok_code = {QE(n1).code('py'): n1, QE(n2).code('py'): n2}
                ops[i] = FOR2Q(n1, n2, rexpr)
            elif isinstance(op, EmitQ):
                if op.code() in ok_code:
                    ops[i] = UE(ok_code[op.code('py')])
                else:
                    return None
        return ops  # not implemented
        
    def find_runs(self):
        #import pdb
        #pdb.set_trace()
        return StartEndPeepholer.find_runs(self)

class IR(OpList):
    optimizers = [
        CombineC,
        #CombineEmitsFmt,
        #HoistQuote,
    ]


if __name__ == '__main__':
    ir = IR()
    ir.DEF('foo', ['a'])
    ir.SETUP('wtf')
    print ir.join()
