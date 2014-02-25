import tatlrt
def html(**_kw):
    _, _q, _emit = tatlrt._ctx('attr')
    # locals: _tmp0, dot
    _emit(u'<html>\n<head>\n<meta charset="UTF-8"></meta>\n<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js" type="text/javascript"></script>\n<script>\n    $(function () {\n        function changetab() {\n            var target = document.location.hash\n            $(".selected").removeClass("selected");\n            $(\'[data-href="\'+target+\'"], \'+target).addClass("selected");\n        }\n        if (document.location.hash) {\n            changetab()\n        }\n        window.onhashchange = changetab\n    });\n    </script>\n<link href="docs.css" type="text/css" charset="utf-8" rel="stylesheet"></link>\n<style>\n    article {display: none;}\n    article.selected {display:block;}\n    </style>\n</head>\n<body>\n')
    for dot in _.iter(_.load('builder', ['scandir'])('slides')):
        _emit('<article class="')
        _emit(_q('selected' if bool(_.get1(dot, 'first')) else None))
        _emit('" id="')
        _emit(_q(_.get1(dot, 'counter')))
        _emit(u'">\n<nav>\n')
        _emit = _.elidestart()
        _emit('<a style="float: left;" href="#')
        _emit(_q(_.get(dot, ['prev', 'counter'])))
        _emit(u'">\u2190 previous</a>')
        _noelide, _content, _emit = _.elidecheck()
        if _noelide:
            _emit(unicode(_content))
        # end
        _emit(u'\n')
        _emit = _.elidestart()
        _emit('<a style="float: right;" href="#')
        _emit(_q(_.get(dot, ['next', 'counter'])))
        _emit(u'">next \u2192</a>')
        _noelide, _content, _emit = _.elidecheck()
        if _noelide:
            _emit(unicode(_content))
        # end
        _emit(u'\n<span>')
        _emit(_q((bool(_.get(dot, [u'value', u'title'])) or _.get(dot, [u'value', u'name']))))
        _emit(u'</span>\n</nav>\n        ')
        _emit(_q(_.get1(tatlrt, u'safe')( _.get(dot, [u'value', u'render'])(dot) )))
        _emit(u'\n    </article>')
    # end
    _emit(u'\n</body>\n</html>')
    return _.result()
# end
