import tatlrt
def html(**_kw):
    _, _q, _emit = tatlrt._ctx('attr')
    _emit(u'<html>\n<head>\n<script src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js" type="text/javascript"></script>\n<script>\n\tfunction changetab(target) {\n\t\t$(".selected").removeClass("selected");\n\t\t$(\'[data-href="\'+target+\'"], \'+target).addClass("selected");\n\t\tdocument.location.replace(target)\n\t}\n    if (document.location.hash) {\n\t\tchangetab(document.location.hash)\n\t}\n\t</script>\n<style>\n\tarticle {display: none;}\n\tarticle.selected {display:block;}\n\t</style>\n</head>\n<body>\n')
    for dot in _.iter(_.load('builder', ['scandir'])('slides')):
        _emit('<article id="')
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
        _emit(u'\n</nav>\n\t\t')
        _emit(_q(_.get(dot, [u'value', u'render'])(dot)))
        _emit(u'\n\t</article>')
    # end
    _emit(u'\n</body>\n</html>')
    dot = _.result()
    return dot
# end
