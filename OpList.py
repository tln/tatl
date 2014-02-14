from collections import namedtuple
import re

    
class I: indent = 1
class D: indent = -1

class OpBase:
    _fields = []
    indent = 0
    
    @property
    def name(self):
        return self.__class__.__name__[1:]
    
    def __init__(self, *args):
        if len(self._fields) != len(args):
            raise TypeError("%s: arg count wrong: %s <- %s" % (self.__class__.__name__, self._fields, args))
        for field, arg in zip(self._fields, args):
            setattr(self, field, arg)

    def init(self, ir):
        "Do initialization. Can set attrs on ir. yield one or more ops. Don't forget yield self!"
        yield self

    def __repr__(self):
        fields = [getattr(self, fld) for fld in self._fields]
        return self.__class__.__name__ + repr(tuple(fields))

    def code(self):
        fmt = self.__doc__
        if '%(' in fmt: fmt %= self
        elif self._fields: fmt %= tuple(self)
        return fmt
        
    def __getitem__(self, name):
        if isinstance(name, int): name = self._fields[name]
        return getattr(self, name, None)
        
    def __len__(self):
        # so that tuple(self) works
        return len(self._fields)
        
    def __nonzero__(self):
        return True
        
class Op0(OpBase):
    _fields = ()
    def __init__(self, *args):
        raise TypeError("%s: arg count wrong" % self.__class__.__name__)
    def code(self):
        return self.__doc__

class OpType:
    @classmethod
    def mk(cls, *args, **kw):
        class NewOpClass(cls, OpBase):
            _fields = args
        return NewOpClass
  
assert OpType.mk()()
   
class OpList:
    def __init__(self):
        self.lists = [[] for t in self.op_types]
        for (i, t) in enumerate(self.op_types):
            t.listix = i

    def __getattr__(self, op, _p=re.compile('[A-Z][A-Z0-9]*$').match):
        if _p(op) is None: raise AttributeError(op)
        cls = getattr(self, '_'+op)
        while isinstance(cls, str):
            # alias
            print op, 'alias ->', cls
            op = cls
            cls = getattr(self, '_'+op)
            
        dest = self.lists[cls.listix]
        def fn(*args):
            o = cls(*args)
            r = o.init(self)
            if r is None: 
                print op, "-> nothing"
                return
            for o in r: 
                #NB o.init may cause insertions between iterations
                if o is None: continue
                if not isinstance(o, OpBase):
                    print "Bad add!", o
                    continue
                dest.append(o) 
        setattr(self, op, fn)
        return fn

    def check(self):
        for l in self.lists:
            for op in l:
                try:
                    op.code()
                except Exception, e:
                    print 'error:', op, e
                    import pdb
                    pdb.post_mortem()

    def out(self):
        i = 0
        for l in self.lists:
            for op in l:
                yield '    '*i + op.code()
                i += op.indent
    
    def add(self, ir):
        assert self.op_types == ir.op_types
        for l1, l2 in zip(self.lists, ir.lists):
            l1.extend(l2)

class SampleIR(OpList):
    class Pre(OpType):pass
    class Post(OpType):pass
    class In(OpType):pass
    op_types = [Pre, In, Post]

    # shared attrs
    name = None
    args = None
    
    class _DEF(I, Pre.mk('name', 'args')):
        def init(self, ir):
            ir.name = self.name
            ir.args = args = self.args
            ir.star = '*' in args
            if ir.star:
                ir.starix = args.index('*')
                del args[ir.starix]
            yield self
            ir.PREAM('attr')

        def code(self):
            return 'def %s(%s)' % (self.name, ', '.join(self.args))
        
    class _LV(Pre.mk('var')):
        "%(var)s = _kw.get(%(var)r)"
        def init(self, ir):
            if self.var not in ir.args:
                yield self
        
    class _PREAM(Pre.mk('mode')): "_ = _ctx(%r)"
 
    Op0 = In.mk()
    Op1 = In.mk('arg')
    Op2 = In.mk('arg', 'arg2')

    _DF = 'FOO'
    class _FOO(Op1):  "Foo!"
    class _BAR(Op2): 
        def init(self, ir): ir.BAR1(), ir.BAR2(self.arg2, self.arg)
    class _BAR1(Op0): "bar1"
    class _BAR2(Op2): "bar2 %s %s"
  

class Peepholer:
    def __init__(self, ops):
        self.ops = ops

    cls = OpType.mk()
    def filt(self, op, cur):
        return isinstance(op, self.cls)
        
    def valid_run(self, run):
        return True

    def optimize(self):
        # update ops in place
        runs = self.find_runs()
        ofs = 0
        for start, end in runs:
            print 'run:', (start, end), ofs, self.ops[start-ofs:end-ofs]
            new = self.optimize_run(self.ops[start-ofs:end-ofs])
            if new is None:
                print 'No optimization'
            else:
                self.ops[start-ofs:end-ofs] = new
                print '->', new
                ofs += (end - start) - len(new)
                print 'ofs ->', ofs
                
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
 
 
class StartEndPeepholer(Peepholer):
    start = OpBase
    end = OpBase   # valid if next op (or last op if also in cls) is this run
    def filt(self, op, cur):
        if cur:
            return isinstance(op, self.cls)
        else:
            return isinstance(op, self.start)
        
    def valid_run(self, run):
        start, end = run
        return isinstance(self.ops[end-1], self.end) or isinstance(self.ops[end], self.end)
    
    
if __name__ == '__main__':
    ir = SampleIR()
    ir.DEF('fn', ['a', '*', 'b'])
    ir.DF(2)
    ir.FOO(1)
    ir.LV('c')
    ir.LV('a')
    ir.BAR(2, 3)
    print ir.lists
    ir.check()
    print '\n'.join(ir.out())
