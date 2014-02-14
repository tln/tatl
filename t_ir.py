from OpList import *


class Pre(OpType):pass
class Post(OpType):pass
class In(OpType):pass

PreExpr = Pre.mk('expr')
PreVar = Pre.mk('var')
Pre1 = Pre.mk('arg')

Val = In.mk('val')
Expr = In.mk('expr')
Var = In.mk('var')
Op0 = In.mk()
Op1 = In.mk('arg')

VExpr = In.mk('var', 'expr')
VVExpr = In.mk('var1', 'var2', 'expr')
VVal = In.mk('var', 'val')
VVar = In.mk('var', 'var')

class Emit: "mixin to ops that call emit"
class EmitQ(Emit): quote = 1
class EmitU(Emit): quote = 0

class For: "mixin to mark for loop start"

class IR(OpList):
    op_types = [Pre, In, Post]
    def peephole(self):
        self.check()
        
        ir = self.lists[1]
        CombineC(ir).optimize()
        HoistQuote(ir).optimize()
        CombineEmits2(ir).optimize()
        
        self.check()
        return
        
        # old code
      
        lop = lopn = lix = None
        ir = self.lists[1]
        for ix, op in enumerate(ir):
            if op == None:
                continue
            opn = op.name

            # C C -> C
            if opn == 'C' and lopn == 'C':
                op.val = lop.val + op.val
                ir[lix] = None


            lix, lop, lopn = ix, op, opn
            
            
            
        self.lists[1] = filter(None, ir)
        self.check()
        
    def finish(self):
        self.peephole()
        print 'finished!'

    def join(self):
        return '\n'.join(self.out())

    
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

    class _C(Val):                  # C Constant
        '_emit(%r)'
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
    class _EMITTRICK2(In.mk('fmt', 'vars')):
        '_emit(%r %% (%s))'
        def code(self):
            return self.__doc__ % (self.fmt, ', '.join(self.vars))

    _LS = 'SETSTART'
    class _SETSTART(Op0):                 # LS Local (set) start
        '_emit = _.push()'
    class _SETEND(In.mk('var', 'filts')):
        def init(self, ir):
            if self.filts:
                expr = '_content'
                for f in filts: expr = '%s( %s )' % (f, expr)
                ir.SETENDEXPR(self.var, expr)
            else:
                ir.SETENDVAR(self.name)
    class _SETENDVAR(Var):                # LD Local (set) Done
        '%s, _emit = _.pop()'
    class _SETENDEXPR(VExpr):                # LD Local (set) Done
        '_content, _emit = _.pop(); %s = %s'
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
    class _ELSE0(D, Op0):
        '#else'
    class _ELSE(I, Op0):
        'else:'
        def init(self, ir):
            ir.ELSE0()
            yield self
    class _ELIF(I, Expr):
        'elif %s:'
        def init(self, ir):
            ir.ELSE0()
            yield self
        
    class _SS(Op1):                 # SS Skip (elide) start
        '_emit = _.elidestart()'
    class _IE1(Op1):                # IE Else (otherwise)
        'else:'    
    class _IE2(D, Op1):             #dedent'
        'else:'
    class _II1(Op1):                # II Else if
        '    '
    class _II2(D, Op1):             #dedent'
        'elif %s:'
    class _SE(Op1):                 # SE Skip (elide) end
        '_noelide, _content, _emit = _.elidestart()'
    # then IS, QV
    class _ID(Op1):                 # ID If end
        '#dedent'
    class _CS(Op1):                 # CS Call (use) start
        '_emit = _push()'
    class _CD1(Op1):                # CD1,2 Call done
        'dot, _emit = _.pop()'
    class _CD2(Op1): 
        '_emit(_.apply(%s, locals()))'
    class _P1(Op1):                 # P1 Param (set dot)
        'dot = %s'
    class _P2(Op1):                 # P2 Params (do not set dot)
        ''
    class _PY(Op1):                 # PY arbitrary python
        '%s'
    
    # *
    # ++
    
    # LS C LF -> LC    
    # QV1 QV1 QV1 -> QQ UV UV UV

class CombineC(Peepholer):
    cls = IR._C
    def optimize_run(self, ops):
        ops[-1].val = ''.join([op.val for op in ops])
        return ops[-1:]

class CombineEmits(Peepholer):
    cls = (Emit, IR._C)
    def optimize_run(self, ops):
        if len(ops) < 2: return
            
        exprs = [repr(op.val) if op.name == 'C' else op.code()[6:-1] # strip off _emit( )
                 for op in ops]
                 
        # gross...
        op = IR._EMITTRICK1(exprs)
        return [op]

class CombineEmits2(Peepholer):
    cls = (Emit, IR._C)
    def optimize_run(self, ops):
        if len(ops) < 2: return
        fmt = ''
        exprs = []
        for op in ops:
            if op.name == 'C':
                fmt += op.val.replace('%', '%%')
            else:
                fmt += '%s'
                exprs.append(op.code()[6:-1]) # strip off _emit( )

        # gross...
        op = IR._EMITTRICK2(fmt, exprs)
        return [op]


class HoistQuote(StartEndPeepholer):
    start = IR._FOR2   # s/bFor
    cls = (EmitQ, IR._C, EmitU)
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


if __name__ == '__main__':
    ir = IR()
    ir.DEF('foo', ['a'])
    ir.SETUP('wtf')
    print ir.join()
