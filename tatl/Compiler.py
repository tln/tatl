import bs4
import sys
import json
import ExprParser, ExprSemantics
from cgi import escape

from tatl import IR

def run_file(f):
    return run_string(open(f).read())

def compile(s, source, out='py'):
    """Return Python that implements the template"""
    dom = bs4.BeautifulSoup(s)
    c = Compiler(source)
    c.root(dom)
    c.module.done()
    if out == 'ir':
        return c.module.view()
    assert out in ('py', 'js')
    code = c.module.code(out)
    if out == 'js':
        #HACK!!! this has to be done throughout IR....
        code = code.replace("u'", "'").replace('u"', '"')
    return code
    
def main():
    for inp in sys.argv[1:]:
        if not inp.endswith('.html'):
            print "Expected .html file:", inp
            continue
        html = open(inp).read()
        py = inp[:-5] + '.py'
        open(py, 'w').write(compile(html, inp, 'py'))
        js = inp[:-5] + '.js'
        open(js, 'w').write(compile(html, inp, 'js'))
    
class Compiler:
    def __init__(self, source):
        self.module = IR.Module(source)
        self.parser = ExprParser.ExprParser(
            parseinfo=True, 
            semantics=ExprSemantics.ExprSemantics()
        )
        self.tags = []
        self.lastfn = []
        self.fn = None
        
    def root(self, dom):
        self.firsttag = 1
        self._children(self._Tagstate('[root]', None, None), dom)
    def startdef(self, funcdef):
        self.lastfn.append(self.fn)
        self.fn = self.module.startdef(funcdef)
        
    def enddef(self):
        self.fn = self.lastfn.pop()
        
    def tag(self, tag):
        if tag.name == 'else':
            return self._else(tag)
        ts = self._Tagstate(tag.name, tag.get('id'), self.fn and self.fn.block())
        self.tags.append(ts)
        self._process_attrs(tag.attrs, ts)
        self.firsttag = 0
        self._children(ts, tag)
        self._finalize(ts)
        self.tags.pop()

    def _default(self, attr, ts, v):
        if v: return v
        method = getattr(self, '_default_'+attr, lambda ts: v)
        return method(ts)

    def _default_for(self, ts):
        return '.'
        
    def _default_def(self, ts):
        return self._name_default(ts)+'(*)'
        
    def _default_param(self, ts):
        return self._name_default(ts)
        
    def _default_set(self, ts):
        return self._name_default(ts) + ' |contents'

    def _name_default(self, ts):
        if ts.id and ts.name not in ['head', 'body']:
            return ts.id
        # check that id is a valid name
        # check that name != 'do'
        return ts.name
    
    
    def _check_attrs(self, attrs, ts):
        if self.firsttag:
            attrs.setdefault('def', "html(*)")
            for attr in 'if', 'for':
                if attr in attrs:
                    warn("Attr not allowed on root tag: "+attr)
                    del attrs[attr]
                    
    _attrs = 'param', 'def', 'set', 'use', 'for', 'if'
    def _process_attrs(self, attrs, ts):
        attrs = attrs.copy()
        self._check_attrs(attrs, ts)
        for attr in self._attrs:
            if attr not in attrs: continue
            v = self._default(attr, ts, attrs.pop(attr))
            if attr == 'if' and not v:
                    self._process_elide(ts, '')
            else:
                    result = self.parser.parse(v, rule_name=attr+'Attr')
                    getattr(self, '_process_'+attr)(ts, result)
    
        if ts.build_tag:
            ts.StartAttrs({})
            for attr, val in attrs.items():
                if isinstance(val, list):
                    #multi-value attribute
                    val = ' '.join(val)
                ts.StartAttr()
                self.parse_text(ts, val, False)
                ts.EndAttr(attr)
            ts.EndAttrs()
        elif ts.emit_tag:
            ts.EmitQText('<'+ts.name)
            for attr, val in attrs.items():
                ts.EmitQText(' '+attr+'="')
                if isinstance(val, list):
                    #multi-value attribute
                    val = ' '.join(val)
                self.parse_text(val)
                ts.EmitQText('"')
            ts.EmitQText('>')
        else:
            if attrs:
                warn("Leftover attrs on <do>")

    class _Tagstate:
        ret = None
        dedent = 0
        if_pending = 0
        elide_pending = 0
        build_tag = 0
        attrs = None
        def __init__(self, name, id, block): 
            self.emit_tag = name != 'do'
            self.name = name
            self.id = id
            self.block = block
        def __getattr__(self, name):
            if name[:1] == '_': raise AttributeError
            cls = getattr(IR, name)
            fn = lambda *args: cls(*args).addto(self.block)
            setattr(self, name, fn)
            return fn
    def _finalize(self, ts):
        if ts.emit_tag:
            ts.EmitQText('</%s>' % ts.name)
        self._finish_elide(ts)
        ts.block.done()
        if ts.ret:
            self.enddef()

    def _finish_elide(self, ts):
        if ts.elide_pending:
            ts.ElideEnd()
            ts.elide_pending = False

    def _process_elide(self, ts, result):
        ts.ElideStart()
        ts.elide_pending = True
        
    def _process_def(self, ts, funcdef):
        self.startdef(funcdef)
        ts.block = self.fn.block()
        ts.ret = True

    def _process_set(self, ts, var):
        ts.SetStart()
        ts.SetEnd(var, IR.Value(ts.name))
        ts.build_tag = True
        ts.emit_tag = False
        
    def _process_if(self, ts, test):
        test.addto(ts.block)
        ts.if_pending = 1
        
    def _process_param(self, ts, v):
        self.fn.add_params(v)
        if len(v) == 1:
            ts.Asgn('dot', v[0].lvar)

    def _process_for(self, ts, obj):
        obj.addto(ts.block)
        
    def _process_use(self, ts, ast):
        ast.addto(ts.block)
        
    def _else(self, tag):
        tags = []
        for ts in self.tags[::-1]:
            if ts.emit_tag:
                tags.append(ts.name)
            if ts.if_pending or ts.elide_pending:
                break
        else:
            warn("No if found for <else>")
            return self._children(ts, tag)
             
        if tags:
            warn("<else> synthesized tags: "+str(tags))
        
        endtags = ''.join(['</%s>' % t for t in tags])
        starttags = ''.join(['<%s>' % t for t in tags])

        ts.EmitQText(endtags)
        self._finish_elide(ts)
                     
        attrs = tag.attrs
        if 'if' in attrs:
            test = self.parser.parse(attrs.pop('if'), rule_name='test')
            ts.Elif(test)
        else:
            ts.Else()

        if attrs:
            warn("Extraneous attributes on <else/>")

        ts.EmitQText(starttags)

        self._children(ts, tag)
    
    def _children(self, ts, tag):
        for c in tag.children:
            typ = c.__class__ 
            if typ is bs4.Tag:
                self.tag(c)
            elif typ is bs4.NavigableString:
                self.parse_text(ts, c)
            elif typ is bs4.Comment and c[:1] == '{':
                self._front_matter(ts, c)
            elif typ is bs4.Comment and c[:1] != '[':
                # comments ignored
                pass
            elif self.fn is None:
                # before first tag, we can't emit
                warn("Can't emit %s: %s" % (c.__class__.__name__, c))
            else:
                self.emit_other(ts, c)

    def _front_matter(self, ts, c):
        # update current fn/module... ideas for keys:
        # package, doc, param docs / required, sample data
        try:
            d = json.loads(c)
        except:
            warn("Front matter cannot be loaded in <%s>" % ts.name)
            d = None
        print 'Front matter:', d

    def emit_other(self, ts, c):
        # Emit other kind of node (CData, PI, )
        print "emit_other!"
        text = bs4.BeautifulSoup('')
        text.contents.append(c)
        text = unicode(text)
        ts.EmitQText(text)
    
    def parse_text(self, ts, text, quoted=1):
        result = []
        ix = text.find('{')
        if quoted:
            emit = lambda t: ts.EmitQText(escape(t.replace('}}', '}')))
        else:
            emit = lambda t: ts.EmitUText(t.replace('}}', '}'))
        while ix > -1 and ix < len(text) - 2:
            if text[ix+1] == '{':
                emit(text[:ix+1])
                text = text[ix+2:]
                ix = text.find('{')
                continue
            if ix > 0:
                emit(text[:ix])
                text = text[ix:]
            Top = self.parser.parse(text, rule_name='top')
            text = Top.rest
            
            Top.quoted = quoted
            Top.addto(ts.block)

            ix = text.find('{')
        emit(text)
        
def warn(s):
    print "Warning:", s

TESTS = '''
<html>
</html>
----
<html>
  {1}
</html>
----
<html>
  {a}
</html>
----
<html>
  <p if="a">a!</p>
  <p if="a">a!<else>no</p>
  <p if="a">a!<else if="0">no</p>
</html>
----
<html>
  {"hi"}/{0}/{['hi']}/{a?={a:1,b:2};a}
</html>
----
<html>
    {1..10}
    {1...10}
    {10...1}
    {10..1}

    <p for="i in 1...5">{i}</p>
    <p for="1...5">{.}</p>
    <p for="i, j in ['a', 'b', 'c']">{i}/{j}</p>

    <p for="i, j in ['a', 'b', 'c']" if="i > 1">
        {i}/{j}
    </p>
</html>
----
<html>{a = {[1, 2, *5..10]}; [*a, 1]}</html>
'''

CRASH = '''
<p if="a">a!<else><else if="0">no</p>
'''

MORETESTS = '''
<html>
  <h1 id="foo" style="{sty}">Hello world!</h1>
  <div def="a()" if="1">
      Hello world!
  </div>
  <div def="b(c)">
      <do if="c > 1">
          c={c}
      </do>
  </div>
  <do for="0..7">{b(.)}</do>
  <ol>
      <li for="sys::path">{.}</li>
  </ol>
</html>
----
<html>
    <ul>
    <li for="sys::path">{.}</li>
</html>
----
<html>
  <h1 def="b(a)" if="a">
      {a}
      <else>
      Nope
  </h1>
</html>
----
<html def="html(a)">
  <do def="b(a)" if="a">
      <h1>{a}</h1>
  <else>
      Nope
  </do>
  <do def="b(a)" if="a==1">
      <h1>{a}</h1>
  <else if="a==2">
      <h2>{a}</h2>
  </do>
  <h1 if>{""}</h1>
  <h2 if>{""}<else>no a!</h1>
</html>
----
<html>
  <foo param>{.}</foo>
  <h1 def="b(a)" if="a">
      {a}
      <else>
      Nope
  </h1>
</html>
----
<html use="base::html">
    <title set>Foo</title>
    <article set>
        Foo bar
    </article>
</html>
----
<html>
    {a}
</html>
----
<html>
    {a ~ /[0-9]/ ? 'number' : 'other'}
    {b = {['one', 'two', 'three']}; c = {{one: 'uno', two: 'dos', three: 'tres'}}}
    {d = {b[len(a)]}; c[d]}
    :{c.what}:{c[a]}:
</html>
----
<table def="table(t)">
    <tr for="r in t">
        <td for="c in r.itervalues()">{c}</td>
    </tr>
</table>
----
<table def>
    <tr param for>
        <td for=".itervalues()">{.}</td>
    </tr>
</table>
----
<table def>
    <tr param for>
        <td for="k, v in .">{v}</td>
    </tr>
</table>
----
Foo
<div class="{*:cls}">
  Errors: {++:errcount} Warnings: {++:warncount}
  {*:toomanyissuetext}
  <div for="[{type: 'error', title:'Hello'}, {type:'info', title:'Info'}, {type: 'error', title:'Hello'}, {type: 'error', title:'Hello'}, {type: 'error', title:'Hello'}]">
    {errcount(.type == 'error' ? 1 : 0); warncount(.type == 'error' ? 1 : 0); cls(.type); ""}
    <h2>{.title}</h2>
    Foo
  </div>
  <p use="toomanyissuetext" if="4 >= errcount > 1">There were some errors</p>
  <p use="toomanyissuetext" if="errcount > 3">FIX YOUR STUFF</p>
</div>
----
<p for="i, . in ['a', 'b', 'c']">{i}: {.}</p>
----
<h1>{{header}}</h1>
{{#bug}}
{{/bug}}

{{#items}}
  {{#first}}
    <li><strong>{{name}}</strong></li>
  {{/first}}
  {{#link}}
    <li><a href="{{url}}">{{name}}</a></li>
  {{/link}}
{{/items}}

{{#empty}}
  <p>The list is empty.</p>
{{/empty}}

{
    header = {"hello world"}; 
    items = {[{name:"blah"}, {url: "foo", name: "foo"}]}; 
}

<h1>{header}</h1>
<li for="items">
    <do elide>
        <a href="{.url}">{.name}</a>
        <else>
        <strong>{.name}</strong>
    </do>
</li>
----
{
    t = {[
       ['a', 'b', 'c'],
       {name:"hello", key: "ok"}
    ]}
}
<p for="t">
  <b class="{.class _}" for="t_tmpl.forloop(.)">
      {.counter}/{.counter0}/{.key}/{.value}/{.first}/{.last}
  </b>
</p>
----
<p for="t_tmpl.forloop(1..10)">
  {.current}
</p>
total: {.sum}

{
  data = {[
      {'cars': 2, 'tvs': 1, 'kids': 0},
      {'cars': 0, 'tvs': 0, 'kids': 0},
      {'cars': 1, 'tvs': 2, 'kids': 0},
      {'cars': 3, 'tvs': 3, 'kids': 0},
      {'cars': 2, 'tvs': 2, 'kids': 2},
      {'cars': 2, 'tvs': 3, 'kids': 0},
      {'cars': 2, 'tvs': 2, 'kids': 1},
  ]}
}

<table>
<tr for="t_tmpl.forloop(data, {preclass:'pre', postclass:'post'})">
  <do if=".pre">
      <th></th>
      <th>Cars</th>
      <th>TVs</th>
      <th>Kids</th>
  <else>
      <td if=".post">
          Total:
          <else>
          {.counter}
      </td>
      <td>{.current.cars}</td>
      <td>{.current.tvs}</td>
      <td>{.current.kids}</td>
  </do>
</tr>
----
<p for if use="wtf" def set param>hello!{.}</p>
'''


TESTS = map(str.strip, TESTS.split('----'))
del TESTS[5:]  # just do 5

def test():
    import sys
    def read(f): 
        with open(f) as fh:
            return fh.read()
    if sys.argv[1:]:
        TESTS = map(read, sys.argv[1:])
    for ix, test in enumerate(TESTS):
        print '---- %d: input ----' % (ix+1)
        print test
        print '---- %d: output ----' % (ix+1)
        py = compile(test, '<test:%d>' % (ix+1))
        print py
        print '---- %d: result ----' % (ix+1)
        d = {}
        try:
            exec py in d, d
            print d['html'](a='a')
        except Exception, e:
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()
