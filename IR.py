from OpList import *
from cgi import escape  # for pre-quoting


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

class Function:
    def __init__(self, funcdef):
        self.name = funcdef.name
        self.code = Block(IR())
        self.init = Block(IR())
        self.args = funcdef.args
        funcdef.addto(self.init)
        
    def block(self):
        return Block(self.code.top)
        
    def done(self):
        code = self.code.done()
        code.optimize()

        print '----- add_locals -----'
        lvars = set()
        for op in code.ops:
            for rvar in op.rvars:
                if rvar not in lvars:
                    InitLocal(rvar).addto(self.init)
                    lvars.add(rvar)
            lvars.update(op.lvars)
            print '%-30.30r l:%s r:%s lvars:%s' % (op, op.lvars, op.rvars, lvars)
        print '-----'
        
        self.init.top.combine(code)
        self.code = None
        return self.init.done()

# ---------
class StarExp(Wrap):
    type = 'starexp'
 
class StarArg(BasePart):
    py = js = '*star*'
STAR_ARG = StarArg()

class Args(List):
    def __init__(self, args):
        try:
            self.addix = args.index(STAR_ARG)
            del args[self.addix]
        except:
            self.addix = len(args)-1
        List.__init__(self, args)
        self.py += ', **_kw'.lstrip(', ')
    

class Placeholder(BasePart):
    type = 'placeholder'
    def __init__(self, ast):
        BasePart.__init__(self)
        op, self.name = ast
        self.type = {'*':'star','++':'plusplus'}[op]
        self.py = self.js = '%s = _.%s()' % (self.name, self.type)
        self.lvars = [self.name]

class FuncDef(Part):
    Code = Indent
    def __init__(self, name, args, result, filters):
        pyfmt = map('@%({})s\n'.format, range(len(filters)))
        pyfmt.append('def %(name)s(%(args)s):')
        jsfmt = ['%(name)s = '] + map('%({})s('.format, range(len(filters))) + [
            'function %(name)s(%(args)s) {'
        ]
        Part.__init__(self, '\n'.join(pyfmt), ''.join(jsfmt), *filters, 
            name=Lvar(name), args=args)
        self.result = result
        self.filters = filters
        
    def addto(self, block):
        block.top.add(self,
            FuncPreamble('attr')
            )
        block.bot.add(
            Expr([], 'dot = _.result()'),
            Part('return %(0)s', 'return %(0)s', self.result or Expr([], 'dot')),
            Part('#done', '}'+')'*len(self.filters), Code=Dedent),
        )
    
class If(namedtuple('If', 'set test'), Out): pass
class Use(namedtuple('Use', 'set path arglist'), Out): pass
class For(namedtuple('For', 'set stmt'), Out): pass
class Top:
    def __init__(self, set, exprs, emit, rest):
        self.set = set
        self.exprs = exprs
        self.quoted = 1
        self.emit = emit
        self.rest = rest

    def addto(self, block):
        for stmt in self.set:
            stmt.addto(block)
        for expr in self.exprs:
            expr.addto(block)
        if self.emit:
            if self.emit.type == 'star':
                expr.addto(block)
            else:
                (QE if self.quoted else UE)(self.emit).addto(block)

class _Val(ArgExpr): fields = ['val']
class _Var(ArgExpr): fields = ['var']
class _Expr(ArgPart): fields = ['expr']

class C(_Val):
    jsfmt = pyfmt = '_emit(%(val)r)'

class U(_Val):
    jsfmt = pyfmt = '_emit(%(val)r)'

class Emit: "mixin to ops that call emit"
class EmitQ(Emit): quote = 1
class EmitU(Emit): quote = 0

class For: "mixin to mark for loop start"

class FuncPreamble(ArgExpr):
    fields = ['context']
    pyfmt = jsfmt = '_, _q, _emit = t_tmpl._ctx(%(context)r)'

class Import(ArgExpr):
    pyfmt = 'import %(arg)s'
    jsfmt = "var %(arg)s = require(%(arg)r)"
    lvarfields = fields = ['arg']

class InitLocal(_Var):  # SV Setup local vars
    lvarfields = ['var']
    pyfmt = '%(var)s = _kw.get(%(var)r)'
    jsfmt = 'var %(var)s'
    
class T(ArgExpr):    # T -> C Constant or U Unquoted
    fields = 'val', 'quoted'
    def addto(self, block):
        p = C(escape(self.val)) if self.quoted else U(self.val)
        p.addto(block)
        
class QE(EmitQ, ArgPart):             # QE Quoted Expression
    fields = ['expr']
    pyfmt = jsfmt = '_emit(_q(%(expr)s))'
#class _QV(EmitQ, _Var):              # QV Quoted local Var
#    pyfmt = jsfmt = '_emit(_q(%(var)s))'
class _UE(EmitU, ArgPart):             # UE Unquoted Expression
    fields = ['expr']
    pyfmt = jsfmt = '_emit(%(expr)s)'
#class _UV(EmitU, _Var):              # UV Unquoted local Var
#    pyfmt = jsfmt = '_emit(%(var)s)'

"""    
#class _EMITTRICK1(In.mk('vars')):
#    '_emit.__self__[999999:] = (%s)'
#    def code(self):
#        return self.__doc__ % ', '.join(self.vars)
class _EMITFMT(In.mk('fmt', 'vars')):
    '_emit(%r %% (%s))'
    def code(self):
        return self.__doc__ % (self.fmt, ', '.join(self.vars))

_LS = 'SETSTART'
class _SETSTART(Op0):                 # LS Local (set) start
    '_emit = _.push()'
class _SETEND(In.mk('var', 'tag')):
    '%s, _emit = _.buildtag(%r, _attrs)'
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
    
class _ELIDESTART(Op0):                 # SS Skip (elide) start
    '_emit = _.elidestart()'
class _ELIDEEND(Op0):                 # SE Skip (elide) end
    '_noelide, _content, _emit = _.elidecheck()'
    def init(self, ir):
        yield self
        ir.IFSTART('_noelide')
        ir.UV('_content')

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
    cls = C
    def optimize_run(self, ops):
        v = ''.join([op.val for op in ops])
        if not v: return []
        ops[-1].val = v
        return ops[-1:]

class CombineU(CombineC):
    cls = U

class CombineEmits(Peepholer):
    cls = (Emit, C)
    def optimize_run(self, ops):
        if len(ops) < 2: return
            
        exprs = [repr(op.val) if op.name == 'C' else op.code()[6:-1] # strip off _emit( )
                 for op in ops]
                 
        # gross...
        op = EMITTRICK1(exprs)
        return [op]

class CombineEmitsFmt(Peepholer):
    cls = (Emit, C, U)
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
    start = ()  #FOR2   # s/bFor
    middle = (EmitQ, C, EmitU)
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
