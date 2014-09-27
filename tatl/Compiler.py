import bs4
import sys, os
import json, copy, re
import ExprParser, ExprSemantics
from cgi import escape

from tatl import IR

def run_file(f):
    return run_string(open(f).read())

def compile(s, source, out='py', warn=None, parser='html.parser'):
    """Return Python that implements the template"""
    dom = _ensure_html_root(bs4.BeautifulSoup(s, parser))
    c = Compiler(source, warn)
    c.root(dom)
    c.module.done()
    if out == 'ir':
        return c.module.view()
    assert out in ('py', 'js')
    code = c.module.code(out)
    if out == 'js':
        # detect unicode literals in JS
        assert not re.search("""u(['"]).*?\\1""", out)
    return code

def _ensure_html_root(dom):
    """Return a DOM that is guaranteed to have a root-level <html> tag"""
    nontag = 0; tags = []; comments = []
    for c in dom.contents:
        if type(c) is bs4.NavigableString:
            if c.strip():
                nontag = True
            tags.append(c)
        elif type(c) is bs4.Tag:
            tags.append(c)
        elif type(c) is bs4.Comment:
            comments.append(c)
        else:
            print "Extra stuff at front", c
    if nontag or len(tags) != 1 or tags[0].name != 'html':
        new_root_tag = bs4.Tag(name='html')
        new_root_tag.contents = tags
        dom.contents = comments + [new_root_tag]
    return dom

def main():
    args = sys.argv[1:]

    opts = {
        t: '-'+t in args and not args.remove('-'+t)
        for t in ('py', 'js')
    }
    if not (opts['py'] or opts['js']):
        opts['py'] = opts['js'] = True

    for inp in args:
        if inp == '-':
            html = sys.stdin.read()
        elif not inp.endswith(('.html', '.tatl')):
            print "Expected .html or .tatl file:", inp
            continue
        else:
            with open(inp) as f:
                html = f.read()
            base = inp[:-4]

        for target in 'py', 'js':
            if opts[target]:
                try:
                    code = compile(html, inp, target)
                except:
                    import traceback, pdb
                    traceback.print_exc()
                    pdb.post_mortem()
                if inp == '-':
                    sys.stdout.write(code)
                else:
                    with open(base + target, 'w') as f:
                        f.write(code)

class Compiler:
    def __init__(self, source, warn=None):
        modname = os.path.splitext(os.path.basename(source))[0]
        self.module = IR.Module(source, modname, IR.Modfinder(source), IR.Modformat())
        self.parser = ExprParser.ExprParser(
            parseinfo=True,
            semantics=ExprSemantics.ExprSemantics()
        )
        self.tags = []
        self.lastfn = []
        self.fn = None
        if warn:
            self.warn = warn

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
        if tag.name in ('script', 'style'):
            # just output it
            ts.EmitQText(unicode(tag))
            return
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
        return ts.name+'(*)'

    def _default_param(self, ts):
        return 'inner' if ts.name == 'do' else ts.name

    def _default_set(self, ts):
        return 'inner' if ts.name == 'do' else ts.name + '|contents'

    def _check_attrs(self, attrs, ts):
        if self.firsttag:
            attrs.setdefault('def', "html(*)")
            for attr in 'if', 'for':
                if attr in attrs:
                    self.warn("Attr not allowed on root tag: "+attr)
                    del attrs[attr]

    _attrs = 'def', 'param', 'set', 'use', 'for', 'if', 'process'
    def _process_attrs(self, attrs, ts):
        attrs = attrs.copy()
        self._check_attrs(attrs, ts)
        for attr in self._attrs:
            if attr not in attrs: continue
            v = self._default(attr, ts, attrs.pop(attr))
            if attr == 'if' and not v:
                    self._process_elide(ts, '')
            elif attr == 'process':
                if v in ['raw']:
                    ts.process = v
                else:
                    # ignored silently
                    raise SyntaxError("Invalid value for process= attribute (%r)" % v)
            else:
                    try:
                        result = self.parser.parse(v, rule_name=attr+'Attr')
                    except:
                        raise SyntaxError("Syntax error on <%s %s='%s'>" % (ts.name, attr, v))
                    getattr(self, '_process_'+attr)(ts, result)

        if ts.emit_tag:
            ts.EmitQText('<'+ts.name)
            for attr, val in attrs.items():
                self._emit_attr(ts.for_attr(attr), attr, val)
            ts.EmitQText('>')
        else:
            if attrs:
                self.warn("Leftover attrs on <do>")

    _boolable = re.compile('\s*\{[^{].*\}\s*$').match
    def _emit_attr(self, ts, attr, val):
        #import pdb
        #pdb.set_trace()
        # bool attributes have speical handling when the entire attribute is
        # a substitution.
        if isinstance(val, list):
            val = ' '.join(val)
        if ts.bool_attr:
            #print 'bool:', ts.name, attr, val
            if not val:
                ts.EmitQText(' '+attr)
                return
            elif self._boolable(val):
                Top = self.parser.parse(val, rule_name='top')
                if Top.boolable():
                    ts.BoolAttr(attr, Top)
                    return
        ts.EmitQText(' '+attr+'="')
        self.parse_text(ts, val)
        ts.EmitQText('"')

    class _Tagstate:
        ret = None
        if_pending = 0
        elide_pending = 0
        end_if = False
        bool_attr = False
        process = "html"
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
        def copy(self, **kw):
            new = copy.copy(self)
            new.__dict__.update(kw)
            return new
        def for_attr(self, attr):
            # If the attribute needs special handling,
            # return a new Tagstate. Otherwise return self
            if attr in ('selected', 'checked', 'disabled'):
                return self.copy(bool_attr=True)
            return self
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

    def _process_set(self, ts, obj):
        obj.addto(ts.block)

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
        #import pdb
        #pdb.set_trace()
        ast.addto(ts.block)

    def _else(self, tag):

        tags = []
        for ts in self.tags[::-1]:
            if ts.emit_tag:
                tags.append(ts.name)
            if ts.if_pending or ts.elide_pending:
                break
        else:
            self.warn("No if found for <else>")
            return self._children(ts, tag)
        if ts.end_if:
            self.warn("<else> after <else> ignored")
            return self._children(ts, tag)

        if tags:
            self.warn("<else> synthesized tags: "+str(tags))

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
            ts.end_if = True

        if attrs:
            self.warn("Extraneous attributes on <else/>")

        ts.EmitQText(starttags)

        self._children(ts, tag)

    def _children(self, ts, tag):
        for c in tag.children:
            typ = c.__class__
            if ts.process == 'raw':
                ts.EmitQText(unicode(c))
            elif typ is bs4.Tag:
                self.tag(c)
            elif typ is bs4.NavigableString:
                if ts.block is None:
                    if c.strip():
                        self.warn("Top-level content ignored: %r" % c.strip())
                else:
                    self.parse_text(ts, c)
            elif typ is bs4.Comment and c[:1] == '{':
                self._front_matter(ts, c)
            elif typ is bs4.Comment and c[:1] != '[':
                # comments ignored
                pass
            elif self.fn is None:
                # before first tag, we can't emit
                self.warn("Can't emit %s: %s" % (c.__class__.__name__, c))
            else:
                self.emit_other(ts, c)

    def _front_matter(self, ts, c):
        # update current fn/module... ideas for keys:
        # package, doc, param docs / required, sample data
        try:
            d = json.loads(c)
        except:
            self.warn("Front matter cannot be loaded in <%s>" % ts.name)
            d = None

    def emit_other(self, ts, c):
        # Emit other kind of node (CData, PI, )
        print "emit_other!", c
        text = bs4.BeautifulSoup('')
        text.contents.append(c)
        text = unicode(text)
        ts.EmitQText(text)

    def parse_text(self, ts, text):
        result = []
        ix = text.find('{')
        emit = lambda t: ts.EmitQText(escape(t.replace('}}', '}')))
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
            Top.addto(ts.block)
            text = Top.rest
            ix = text.find('{')
        emit(text)

    def warn(self, s):
        #TODO pass line number
        print>>sys.stderr, "*Warning:", s
