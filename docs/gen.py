import tatlrt
def html(**_kw):
    _, _q, _emit = tatlrt._ctx('attr')
    # locals: _tmp1, _tmp0, dot
    _emit(u'<html>\n<head>\n<meta charset="UTF-8">\n<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js" type="text/javascript"></script>\n<script>\n    $(function () {\n        function changetab() {\n            var target = document.location.hash\n            $(".selected").removeClass("selected");\n            $(\'[data-href="\'+target+\'"], \'+target).addClass("selected");\n        }\n        if (document.location.hash) {\n            changetab()\n        }\n        window.onhashchange = changetab\n    });\n    </script>\n<link href="docs.css" type="text/css" charset="utf-8" rel="stylesheet">\n<style>\n    article {display: none;}\n    article.selected {display:block;}\n    </style>\n</link></meta></head>\n<body>\n')
    for dot in _.iter(_.load(u'builder', [u'scandir'])('slides')):
        _emit(u'<article class="%s" id="%s">\n<nav>\n' % (_q('selected' if bool(_.get1(dot, u'first')) else None), _q(_.get1(dot, u'counter')),))
        _emit = _.elidestart()
        _emit(u'<a style="float: left;" href="#%s">\u2190 previous</a>' % (_q(_.get(dot, [u'prev', u'counter'])),))
        _noelide, _content, _emit = _.elidecheck()
        if _noelide:
            _emit(unicode(_content))
        # end
        _emit(u'\n')
        _emit = _.elidestart()
        _emit(u'<a style="float: right;" href="#%s">next \u2192</a>' % (_q(_.get(dot, [u'next', u'counter'])),))
        _noelide, _content, _emit = _.elidecheck()
        if _noelide:
            _emit(unicode(_content))
        # end
        _emit(u'\n<span>%s</span>\n</nav>\n        %s\n    </article>' % (_q((bool(_.get(dot, [u'value', u'title'])) or _.get(dot, [u'value', u'name']))), _q(_.get1(tatlrt, u'safe')( _.get(dot, [u'value', u'render'])(dot) )),))
    # end
    _emit(u'\n')
    for dot in _.iter(_.load(u'builder', [u'scandir'])('ref')):
        _emit(u'<article id="%s">\n<nav>\n' % (_q(_.get(dot, [u'value', u'name'])),))
        _emit = _.elidestart()
        _emit(u'<a style="float: left;" href="#%s">\u2190 previous</a>' % (_q(_.get(dot, [u'prev', u'name'])),))
        _noelide, _content, _emit = _.elidecheck()
        if _noelide:
            _emit(unicode(_content))
        # end
        _emit(u'\n')
        _emit = _.elidestart()
        _emit(u'<a style="float: right;" href="#%s">next \u2192</a>' % (_q(_.get(dot, [u'next', u'name'])),))
        _noelide, _content, _emit = _.elidecheck()
        if _noelide:
            _emit(unicode(_content))
        # end
        _emit(u'\n<span>%s</span>\n</nav>\n        %s\n    </article>' % (_q((bool(_.get(dot, [u'value', u'title'])) or _.get(dot, [u'value', u'name']))), _q(_.get1(tatlrt, u'safe')( _.get(dot, [u'value', u'render'])(dot) )),))
    # end
    _emit(u'\n</body>\n</html>')
    return _.result()
# end
