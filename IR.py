from OpList import *
from cgi import escape  # for pre-quoting


class Module:
    def __init__(self):
        self.code = Block(OpList())
        self.functions = OrderedDict()
        
    def startdef(self, funcdef):
        fn = self.functions[funcdef.name] = Function(funcdef)
        return fn
        
    def done(self):
        for fn in self.functions.values():
            self.code.top.add(fn.done())
        return self.code.done()

class Function:
    def __init__(self, funcdef):
        self.name = name
        self.code = Block(target, OpList())
        self.init = Block(target, OpList())
        self.args = funcdef.args
        funcdef.addto(self.init)
        
    def block(self):
        return Block(self.code.top)
        
    def done(self):
        self.init.top.add(self.code.done())
        self.code = None
        return self.init.done()

# ---------
class StarExp(Wrap):
    type = 'starexp'
 
class StarArg(BasePart):
    py = js = '*star*'
STAR_ARG = StarArg()

class Args(List):
    def args(self):
        return ['*' if p is STAR_ARG else p.lvar
                for p in self.partlist]

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
        Part.__init__(self, '\n'.join(pyfmt), ''.join(jsfmt), *filters, name=name, args=args)
        self.result = result
        self.filters = filters
        
    def addto(self, block):
        block.top.add(self)
        p = Expr([], 'dot = _.result()')
        block.bot.add(p)
        p = Part('return %(0)s', 'return %(0)s', self.result or Expr([], 'dot'))
        block.bot.add(p)
        p = Part('#done', '}'+')'*len(self.filters), Code=Dedent)
        block.bot.add(p)
    
class If(namedtuple('If', 'set test'), Out): pass
class Use(namedtuple('Use', 'set path arglist'), Out): pass
class For(namedtuple('For', 'set stmt'), Out): pass
class Top(namedtuple('Top', 'set exprs emit rest'), Out): pass

class Emit: "mixin to ops that call emit"
class EmitQ(Emit): quote = 1
class EmitU(Emit): quote = 0

class For: "mixin to mark for loop start"

class IR(OpList):
    optimizers = [
        CombineC,
        CombineU(,
        CombineEmitsFmt,
        StaticAttrs,
        #HoistQuote,
    ]


    _FL = 'FILT'
    class _FILT(PreExpr):  # FL FiLter (decorator)
        '@%s'

    _DS = 'DEF'
    class _DEF(I, Pre.mk('name', 'args')):  # DS Function def start
        def init(self, ir):
            ir.name = self.name
            ir.args = args = self.args
            ir.star = '*' in args
            if ir.star:
                ir.starix = args.index('*')
                del args[ir.starix]
            yield self
            
        def code(self):
            return 'def %s(%s):' % (self.name, ', '.join(self.args+['**_kw']))
    
    _S = 'SETUP'
    class _SETUP(Pre1):  # S Setup
        '_, _q, _emit = t_tmpl._ctx(%r)'
        
    _LV = 'SV'
    _SV = 'VAR'
    class _VAR(PreVar):  # SV Setup local vars
        '%(var)s = _kw.get(%(var)r)'
        def init(self, ir):
            if self.var not in ir.args:
                yield self
        
    _SP = 'PARAM'   
    class _PARAM(PreVar):
        '#param:%s'
        def init(self, ir):
            if self.var in ir.args:
                warn("Duplicate param: %s", self.var)
            elif ir.star:
                ir.args.insert(ir.starix, self.var)
            else:
                ir.args.append(self.var)

    Post0 = Post.mk()

    _DD = 'RET'
    class _RET(Post0):  # D Def return done
        'return _.result()'

    class _T(In.mk('val', 'quoted')):    # T -> C Constant or U Unquoted
        def init(self, ir):
            if self.quoted:
                ir.C(escape(self.val))
            else:
                ir.U(self.val)  
    class _C(Val):                  # C Pre-quoted Constant
        '_emit(%r)'
    class _U(Val):                  # C Unquoted Constant (eg for building attr)
        '_emit(%r)'
    class _V(In.mk('expr', 'quoted')):    # V -> QE or UE
        def init(self, ir):
            if self.quoted:
                ir.QE(self.expr)
            else:
                ir.UE(self.expr)
    class _QE(EmitQ, Expr):             # QE Quoted Expression
        '_emit(_q(%s))'
    class _QV(EmitQ, Var):              # QV Quoted local Var
        '_emit(_q(%s))'
    class _QQ(VExpr):                # QQ Make local be quoted 
        '%s = %s'
    class _UE(EmitU, Expr):             # UE Unquoted Expression
        '_emit(%s)'
    class _UV(EmitU, Var):              # UV Unquoted local Var
        '_emit(%s)'
        
    class _EMITTRICK1(In.mk('vars')):
        '_emit.__self__[999999:] = (%s)'
        def code(self):
            return self.__doc__ % ', '.join(self.vars)
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

class CombineC(Peepholer):
    cls = IR._C
    def optimize_run(self, ops):
        v = ''.join([op.val for op in ops])
        if not v: return []
        ops[-1].val = v
        return ops[-1:]

class CombineU(CombineC):
    cls = IR._U

class CombineEmits(Peepholer):
    cls = (Emit, IR._C)
    def optimize_run(self, ops):
        if len(ops) < 2: return
            
        exprs = [repr(op.val) if op.name == 'C' else op.code()[6:-1] # strip off _emit( )
                 for op in ops]
                 
        # gross...
        op = IR._EMITTRICK1(exprs)
        return [op]

class CombineEmitsFmt(Peepholer):
    cls = (Emit, IR._C, IR._U)
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
        op = IR._UE(expr)
        return [op]


class HoistQuote(StartEndPeepholer):
    start = IR._FOR2   # s/bFor
    middle = (EmitQ, IR._C, EmitU)
    end = IR._ENDFOR
    
    def optimize_run(self, ops):
        # check that the EmitQ expressions match loop names
        # make mods as we go; throw them away if we find out its not a match
        for i, op in enumerate(ops):
            if i == 0:
                n1, n2, rexpr = ops[0]
                ok_code = {IR._QE(n1).code(): n1, IR._QE(n2).code(): n2}
                ops[i] = IR._FOR2Q(n1, n2, rexpr)
            elif isinstance(op, EmitQ):
                if op.code() in ok_code:
                    ops[i] = IR._UE(ok_code[op.code()])
                else:
                    return None
        return ops  # not implemented
        
    def find_runs(self):
        #import pdb
        #pdb.set_trace()
        return StartEndPeepholer.find_runs(self)

class StaticAttrs(StartEndPeepholer):
    start = IR._STARTATTRS
    middle = OpType
    end = IR._ENDATTRS
    
    def optimize_run(self, ops):
        # Look for sub runs of STARTATTR, something, ENDATTR 
        # Move the U.val or UE.expr into STARTATTR
        result = []
        attrs = ops[0].attrs
        ix = 0
        end = len(ops)-3
        wraps = {'U': unicode, 'UE': Lit}
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

class Lit(unicode):
    def __repr__(self):
        return self               

if __name__ == '__main__':
    ir = IR()
    ir.DEF('foo', ['a'])
    ir.SETUP('wtf')
    print ir.join()
