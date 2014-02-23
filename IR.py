from OpList import *
from cgi import escape  # for pre-quoting

RESERVED = ['var']

# --------- Compiler API
class Module:
    def __init__(self, source):
        self.block = Block(IR())
        self.functions = OrderedDict()
        self.add_import('t_tmpl')
        
    def startdef(self, funcdef):
        fn = self.functions[funcdef.name] = Function(funcdef)
        return fn
        
    def add_import(self, module):
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
    def __init__(self, funcdef):
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

        lvars = set(self.args.lvars)
        for op in code.ops:
            for rvar in op.rvars:
                if rvar not in lvars:
                    InitLocal(rvar).addto(self.init)
                    lvars.add(rvar)
            lvars.update(op.lvars)
        
        self.init.bot = code
        self.code = None
        return self.init.done()

# -------- Major constructs created by ExprSemantics
class FuncDef(ArgPart):
    fields = ['name', 'args']
    Code = Indent
    pyfmt = 'def %(name)s(%(args)s):'
    jsfmt = '%(name)s = t_tmpl._bind(function %(name)s(%(args)s) {'
    def __init__(self, name, args, result, filters):
        ArgPart.__init__(self, Lvar(name), args)
        self.result = result
        self.filters = filters
        
    def addto(self, block):
        block.top.add(self,
            FuncPreamble('attr')
            )
        block.bot.add(
            Expr([], 'dot = _.result()'),
            Part('return %(0)s', 'return %(0)s', self.result or Expr([], 'dot')),
            FuncEnd(),
            *[Filter(self.name, filt) for filt in self.filters]
        )
        block.bot.add(Part('', 'exports.%(0)s = %(0)s', self.name))
    
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
            end = UseEndArgs(self.path, self.arglist)
class For(namedtuple('For', 'set stmt'), Out):
    def addto(self, block):
        for stmt in self.set:
            stmt.addto(block)
        block.top.add(self.stmt)
        block.bot.add(ForEnd())
class Top(namedtuple('Top', 'set exprs emit rest'), Out):
    quoted = 1
    def addto(self, block):
        for stmt in self.set:
            stmt.addto(block)
        for expr in self.exprs:
            expr.addto(block)
        if self.emit:
            if self.emit.type == 'star':
                expr.addto(block)
            else:
                (EmitQExpr if self.quoted else EmitUExpr)(self.emit).addto(block)

# -------- Additional Semantics created constructs
class StarExp(Wrap):
    type = 'starexp'
 
class StarArg(BasePart):
    py = js = '*star*'
STAR_ARG = StarArg()

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
    pyfmt = 't_tmpl.range_incl(%(n)s, %(m)s)'
    jsfmt = 't_tmpl.range(%(n)s, %(m)s, true)'

class RangeExcl(ArgPart):
    fields = ['n', 'm']
    pyfmt = 't_tmpl.range_excl(%(n)s, %(m)s)'
    jsfmt = 't_tmpl.range(%(n)s, %(m)s, false)'

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

class EmitUText(_Val):
    pyfmt = '_emit(%(val)r)'
    jsfmt = '_.emit(%(val)r);'

class Filter(ArgPart):
    fields = ['name', 'filt']
    pyfmt = jsfmt = '%(name)s = %(filt)s(%(name)s)'
    
class FuncPreamble(ArgExpr):
    fields = ['context']
    pyfmt = '_, _q, _emit = t_tmpl._ctx(%(context)r)'
    jsfmt = 'var _ = t_tmpl._ctx(%(context)r);'

class FuncEnd(_End):
    js = '})'
class Import(ArgExpr):
    pyfmt = 'import %(arg)s'
    jsfmt = "var %(arg)s = require('./'+%(arg)r)"    # hack! ./t_tmpl
    lvarfields = fields = ['arg']

class InitLocal(_Var):  # SV Setup local vars
    lvarfields = ['var']
    pyfmt = '%(var)s = _kw.get(%(var)r)'
    jsfmt = 'var %(var)s = this.%(var)s'
            

class _Emit(ArgPart):
    fields = ['expr']
class EmitQExpr(_Emit):             # QE Quoted Expression
    pyfmt = '_emit(_q(%(expr)s))'
    jsfmt = '_.emit(_.q(%(expr)s));'
#class _QV(EmitQ, _Var):              # QV Quoted local Var
#    pyfmt = jsfmt = '_emit(_q(%(var)s))'
class EmitUExpr(_Emit):             # UE Unquoted Expression
    pyfmt = '_emit(unicode(%(expr)s))'
    jsfmt = '_.emit(%(expr)s);'
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
    py = js = '_emit = _.push()'
class SetEnd(ArgPart):
    fields = ['var', 'tagname']
    pyfmt = jsfmt = '%(var)s, _emit = _.buildtag(%(tagname)r, _attrs)'
    def addto(self, block):
        block.bot.add(self)
class StartAttrs(ArgExpr):
    fields = ['attrs']
    pyfmt = jsfmt = '_attrs = %(attrs)r'
class StartAttr(BasePart):
    py = js = '_emit = _.push()'
class EndAttr(ArgExpr):
    fields = ['attr']
    pyfmt = jsfmt = '_attrs[%(attr)r], _emit = _.pop()'
class EndAttrs(BasePart):
    py = js = '#end attrs'


    

class UseStart(BasePart):                 # CS Call (use) start
    py = js = '_emit = _.push()'
class UseEnd0(BasePart):
    py = 'dot, _emit = _.pop()'
    js = 'dot = _.pop()'
class UseEndAuto(ArgPart):
    fields = ['expr']
    pyfmt = '_emit(_.applyauto(%(expr)s, locals()))'
    jsfmt = '*not implemented*'
class UseEndArgs(ArgPart):
    fields = ['expr', 'callargs']
    pyfmt = jsfmt = '_emit(_.applyargs(%(expr)s, %(callargs)s))'


"""    
#class _EMITTRICK1(In.mk('vars')):
#    '_emit.__self__[999999:] = (%s)'
#    def code(self):
#        return self.__doc__ % ', '.join(self.vars)
class _EMITFMT(In.mk('fmt', 'vars')):
    '_emit(%r %% (%s))'
    def code(self):
        return self.__doc__ % (self.fmt, ', '.join(self.vars))

class _STARTATTRS(In.mk('attrs')):
    '_attrs = %r'
class _STARTATTR(Op0):
    '_emit = _.push()'
class _ENDATTR(In.mk('attr')):
    '_attrs[%r], _emit = _.pop()'
class _ENDATTRS(Op0):
    '#end attrs'

class _LD2(VExpr):              # LD2
    '%s = %s'

_LC = 'LVARC'
class _LVARC(VVal):                # LC local set constant
    '%s = %r'
_LE = 'LVARE'
class _LVARE(VExpr):               # LE Local set expression
    '%s = %s'
_F1 = 'FOR1'
class _FOR1(For, I, VExpr):            # F1 for loop 1 var start (pass pair as arg)
    'for %s in _.iter(%s):'
_F2 = 'FOR2'
class _FOR2(For, I, VVExpr):           # F2 for loop 2 var start (pass triple as arg)
    'for %s, %s in _.items(%s):'

_F1Q = 'FOR1Q'
class _FOR1Q(I, VExpr):                # F1Q Pre quoted for loop 1 var start
    'for %s in _.iterq(%s):'
_F2Q = 'FOR2Q'
class _FOR2Q(I, VVExpr):                # F2 Pre quoted for loop 2 var start (pass triple as arg)
    'for %s, %s in _.itemsq(%s):'

class _ENDFOR(D, Op0):                 # FD for loop done
    '#end for'

_IS = 'IFSTART'
class _IFSTART(I, Op1):                 # IS If start
    'if %s:'
class _IFEND(D, Op0):                 # IS If start
    '#end if'
class _ELSE(D, I, Op0):
    'else:'
class _ELIF(D, I, Expr):
    'elif %s:'
    
class _USESTART(Op0):                 # CS Call (use) start
    '_emit = _push()'
class _USEEND(In.mk('expr', 'arglist')):
    def init(self, ir):
        ir.USEEND0()
        if self.arglist:
            ir.USEENDARGS(self.expr, self.arglist)
        else:
            ir.USEENDAUTO(self.expr)
class _USEEND0(Op0):
    'dot, _emit = _.pop()'
class _USEENDAUTO(Op1):                # CD1,2 Call done
    '_emit(_.applyauto(%s, locals()))'
class _USEENDARGS(In.mk('expr', 'arglist')):        # USEENDARGS
    '_emit(_.applyargs(%s, %s))'

_PY = 'SET'
class _SET(Op1):                 # Assignment
    '%s'

    # LS C LF -> LC    
    # QV1 QV1 QV1 -> QQ UV UV UV
"""

class CombineC(Peepholer):
    cls = EmitQText
    def optimize_run(self, ops):
        v = ''.join([op.val for op in ops])
        if not v: return []
        ops[-1].val = v
        return ops[-1:]

class CombineU(CombineC):
    cls = EmitUText

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
    cls = (_Emit, EmitQText, EmitUText)
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

class StaticAttrs(StartEndPeepholer):
    start = () #STARTATTRS
    middle = Op
    end = () #ENDATTRS
    
    class Lit(unicode):
        def __repr__(self):
            return self               
    
    def optimize_run(self, ops):
        # Look for sub runs of STARTATTR, something, ENDATTR 
        # Move the U.val or UE.expr into STARTATTR
        result = []
        attrs = ops[0].attrs
        ix = 0
        end = len(ops)-3
        wraps = {'U': unicode, 'UE': self.Lit}
        while ix <= end:
            op = ops[ix]
            if op.name != 'STARTATTR': 
                result.append(op)
                ix += 1
                continue
            op1 = ops[ix+1]
            op2 = ops[ix+2]
            if op2.name == 'ENDATTR': 
                wrap = wraps.get(op1.name)
                if wrap:
                    attrs[op2.attr] = wrap(op1[0])
                    ix += 3
                    continue
                
            result += [op, op1, op2]
            ix += 3
        if attrs:
            # We only did something if attrs changed
            return result

class IR(OpList):
    optimizers = [
        CombineC,
        CombineU,
        #CombineEmitsFmt,
        #StaticAttrs,
        #HoistQuote,
    ]


if __name__ == '__main__':
    ir = IR()
    ir.DEF('foo', ['a'])
    ir.SETUP('wtf')
    print ir.join()
