from collections import namedtuple, OrderedDict
import re

class Block:
    def __init__(self, top):
        self.top = top
        self.bot = OpList()
        
    def done(self):
        self.top.combine(self.bot)
        self.bot = None
        return self.top
        
    def __del__(self):
        if self.bot:
            print 'Warning: Block.done() not called'

class Compilable:
    def addto(self, block):
        # Add one or more Ops to block.top / block.bottom
        pass

class Op:
    def code(self, target):
        # Return a Code instance
        return ''
        
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
    py = js = '*not implemented*'
    def __init__(self):
        self.lvars = []
        self.rvars = []
        
    def add(self, part):
        self.lvars.extend(part.lvars)
        self.rvars.extend(part.rvars)
        
    def __str__(self):
        #TODO remove
        print 'str called -> %r' % self.py
        return self.py
        
    def __repr__(self):
        return '<%s>' % self.out().replace('\n', ' ')
        
    Code = Code
    def code(self, target):
        assert target in 'py', 'js'
        return self.Code(getattr(self, target))
        
    type = ''
    def out(self):
        l = []
        if self.py == self.js:
            l.append('py/js: '+self.py)
        else:
            l.append('py: '+self.py)
            l.append('js: '+self.js)
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

class ArgExpr(BasePart):
    fields = []
    lvarfields = []
    rvarfields = []
    def __init__(self, *args):
        BasePart.__init__(self)
        assert len(args) == len(self.fields)
        d = dict(zip(self.fields, args))
        self.__dict__.update(d)
        self.lvars = [d[k] for k in self.lvarfields]
        self.rvars = [d[k] for k in self.rvarfields]
        
    def __repr__(self):
        n = self.__class__.__name__
        args = tuple(getattr(self, attr) for attr in self.fields)
        return n + str(args)
        
    def code(self, target):
        fmt = getattr(self, target+'fmt')
        return self.Code(fmt % self.__dict__)

class Part(BasePart):
    def __init__(self, pyfmt, jsfmt, *parts, **partkw):
        BasePart.__init__(self)
        pyfrags = {}
        jsfrags = {}
        if 'Code' in partkw:
            self.Code = partkw.pop('Code')
        for k, v in list(enumerate(parts)) + partkw.items():
            self.add(v)
            pyfrags[str(k)] = v.py
            jsfrags[str(k)] = v.js
        self.py = pyfmt % pyfrags
        self.js = jsfmt % jsfrags
        self.__dict__.update(partkw)

class ArgPart(Part):
    fields = []
    pyfmt = jsfmt = '*not implemented*'
    def __init__(self, *args):
        assert len(args) == len(self.fields)
        partkw = dict(zip(self.fields, args))
        Part.__init__(self, self.pyfmt, self.jsfmt, **partkw)
    
class List(BasePart):
    def __init__(self, partlist, join=', '):
        BasePart.__init__(self)
        self.partlist = partlist
        map(self.add, partlist)
        self.py = join.join(p.py for p in partlist)
        self.js = join.join(p.js for p in partlist)

class Lvar(BasePart):
    def __init__(self, lvar):
        BasePart.__init__(self)
        self.lvars = [lvar]
        self.py = self.js = lvar
        
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
 
 
class Wrap(BasePart):
    def __init__(self, part):
        BasePart.__init__(self)
        self.add(part)
        self.py = part.py
        self.js = part.js
        self.part = part

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

def join(fn):
    return lambda *args, **kw: '\n'.join(fn(*args, **kw))
    
class OpList:
    def __init__(self):
        self.ops = []
                
    def __nonzero__(self):
        return bool(self.ops)

    def check(self):
        for op in self.ops:
            try:
                assert isinstance(op.code('py'), Code)
            except Exception, e:
                print 'error:', op, e
                import pdb
                pdb.post_mortem()

    @join
    def view(self):
        for op in self.ops:
            try:
                indent = op.Code.indent-op.Code.dedent
            except:
                indent = 0
            yield '%2d %s' % (indent, op)

    @join
    def code(self, target):
        i = 0
        for op in self.ops:
            code = op.code(target)
            if not isinstance(code, Code):
                print 'op.code didnt return Code instance:', repr(op)
                code = Code(code)
            i -= code.dedent
            yield '    '*i + code
            i += code.indent
    
    def add(self, *ops):
        self.ops.extend(ops)

    def combine(self, other):
        self.ops.extend(other.ops)    
    
    def optimize(self):
        for cls in self.optimizers:
            cls(self.ops).optimize()
        return self

    optimizers = []        

class Peepholer:
    def __init__(self, ops):
        self.ops = ops

    def filt(self, op, cur):
        return isinstance(op, self.cls)
        
    def valid_run(self, run):
        return True

    def optimize(self):
        # update ops in place
        runs = self.find_runs()
        ofs = 0
        for start, end in runs:
            new = self.optimize_run(self.ops[start-ofs:end-ofs])
            if new is not None:
                self.ops[start-ofs:end-ofs] = new
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
    start = Op
    end = Op   # valid if next op (or last op if also in cls) is this run
    def filt(self, op, cur):
        if cur:
            return isinstance(op, self.cls)
        else:
            return isinstance(op, self.start)
        
    def valid_run(self, run):
        start, end = run
        return isinstance(self.ops[end-1], self.end) or isinstance(self.ops[end], self.end)

class StartEndPeepholer(Peepholer):
    start = Op
    middle = Op
    end = Op
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
