
import OpList, IR

class Pass(OpList.BasePart):
    py = 'pass'
    js = '/* no op */'

class Peepholer:
    def __init__(self, ops):
        self.ops = ops

    def filt(self, op, cur):
        return isinstance(op, self.cls)

    def valid_run(self, run):
        return True

    def optimize(self, target):
        # update ops in place
        runs = self.find_runs()
        ofs = 0
        for start, end in runs:
            new = self.optimize_run(self.ops[start-ofs:end-ofs])
            if new is None: continue
            start -= ofs
            end -= ofs
            if not new:
                if start > 0 and self.ops[start-1].Code.indent and self.ops[end].Code.dedent:
                    # insert a Pass, to avoid "if x:", "elif x:" which is syntax error in python
                    new = [Pass()]
            self.ops[start:end] = new
            ofs += (end - start) - len(new)

    def optimize_run(self, ops):
        pass

    def find_runs(self):
        runs = []
        flag = False
        for ix, op in enumerate(self.ops):
            newflag = self.filt(op, flag)
            if flag == newflag: continue
            if newflag:
                runs.append([ix, None])
            else:
                runs[-1][-1] = ix
                if not self.valid_run(runs[-1]):
                    del runs[-1]
            flag = newflag
        if flag:
            runs[-1][-1] = ix+1

        return runs

class OldStartEndPeepholer(Peepholer):
    start = OpList.Op
    end = OpList.Op   # valid if next op (or last op if also in cls) is this run
    def filt(self, op, cur):
        if cur:
            return isinstance(op, self.cls)
        else:
            return isinstance(op, self.start)

    def valid_run(self, run):
        start, end = run
        return isinstance(self.ops[end-1], self.end) or isinstance(self.ops[end], self.end)

class StartEndPeepholer(Peepholer):
    start = OpList.Op
    middle = OpList.Op
    end = OpList.Op
    def find_runs(self):
        runs = []
        start = None
        for ix, op in enumerate(self.ops):
            if start is None:
                if isinstance(op, self.start):
                    start = ix
            elif isinstance(op, self.end):
                runs.append((start, ix+1))
                start = None
            elif not isinstance(op, self.middle):
                start = None
                # migt miss here
        return runs

# -------- Peepholers
class CombineC(Peepholer):
    cls = IR.EmitQText
    def optimize_run(self, ops):
        v = ''.join([op.val for op in ops])
        if not v:
            # insert Pass??
            return []
        return [IR.EmitQText(v)]

class SafeEmit(Peepholer):
    cls = IR.EmitQExpr
    def optimize_run(self, ops):
        result = None  # indicate no change unless we modify an op
        for ix, op in enumerate(ops):
            e = op.expr
            if isinstance(e, IR.FiltExp) and e.filt.filtname == 'safe':
                ops[ix] = IR.EmitUExpr(e.expr)
                result = ops
        return result

class CombineEmits(Peepholer):
    cls = (IR._Emit, IR.EmitQText)
    def optimize_run(self, ops):
        if len(ops) < 2: return

        exprs = [repr(op.val) if op.name == 'C' else op.code()[6:-1] # strip off _emit( )
                 for op in ops]

        # gross...
        op = EMITTRICK1(exprs)
        return [op]

class EmitFmt(OpList.BasePart):
    def __init__(self, fmt, exprs):
        OpList.BasePart.__init__(self)
        map(self.add, exprs)
        self.fmt = fmt
        self.exprs = exprs

    def code(self, target, state):
        if target == 'py':
            if len(self.exprs) == 1:
                py = self.exprs[0].code('py', state)
            else:
                py = '(%s)' % OpList.List(self.exprs).code('py', state)
            return self.Code('%s(%r %% %s)' % (state.emitvar(self), self.fmt, py))
        elif target == 'js':
            code = repr(unicode(self.fmt))[1:]  # without u prefix
            fmt = code[0]+'+%s+'+code[0]
            code %= tuple([fmt % e.code('js', state) for e in self.exprs])
            return self.Code('_.emit(%s);' % code)

class UseBuf(Peepholer):
    cls = (IR._Emit, IR.EmitQText)
    def optimize_run(self, ops):
        pyfmt = '%(emit)s'
        exprs = {}
        for n, op in enumerate(ops):
            var = 'e'+str(n)
            binop = '+'
            if isinstance(op, IR.EmitQText):
                expr = IR.Value(repr(op.val))
            elif isinstance(op, IR.EmitUExpr):
                expr = op.expr
            elif isinstance(op, IR.EmitQExpr):
                expr = op.expr
                binop = '&'
            else:
                raise ValueError("Unexpected op", op)
            exprs[var] = expr
            pyfmt = '(%s %s (%%(%s)s))' % (pyfmt, binop, var)
        op = PyOptimized(ops, pyfmt[1:-1], **exprs)
        return [op]

class PyOptimized(OpList.ArgPart):
    def __init__(self, subparts, pyfmt, **exprs):
        self.subparts = subparts
        self.pyfmt = pyfmt
        self.fields = exprs.keys()
        OpList.ArgPart.__init__(self, *exprs.values())
    def code(self, target, state):
        if target == 'py':
            return OpList.ArgPart.code(self, target, state)
        else:
            assert target == 'js'
            code = '\n'.join(p.code(out) for p in self.subparts)
        return self.Code(code)

class BufOrNotPeepholer(Peepholer):
    def optimize(self, target):
        if target != 'py': return

        # find the return
        for i, o in enumerate(self.ops):
            if isinstance(o, IR.Return):
                break
        else:
            raise AssertionError("Expected a return")

        ops1 = self.ops[:i]
        ops2 = self.ops[:i]
        rest = self.ops[i:]
        UseBuf(ops1).optimize(target)
        CombineEmitsFmt(ops2).optimize(target)
        self.ops[:i] = [IR.IfStart(IR.Impl('tatlrt.fast'))] + ops1 + [IR.Else()] + ops2 + [IR.IfEnd()]

class CombineEmitsFmt(Peepholer):
    cls = (IR._Emit, IR.EmitQText)
    def optimize_run(self, ops):
        if len(ops) < 2: return
        fmt = u''
        expr = None
        out = []
        for op in ops:
            if isinstance(op, IR.EmitQText):
                fmt += op.val.replace('%', '%%')
            elif expr is None:
                fmt += '%s'
                expr = op.fmtexpr()
            else:
                out.append(EmitFmt(fmt, [expr]))
                fmt = u'%s'
                expr = op.fmtexpr()

        if expr is None:
            if fmt:
                out.append(IR.EmitQText(fmt.replace('%%', '%')))
        else:
            out.append(EmitFmt(fmt, [expr]))
        return out

optimizers = {
    'py': [CombineC, SafeEmit, BufOrNotPeepholer],
    'js': [CombineC, SafeEmit],
}