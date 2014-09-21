#TATL: Tag & Attribute Template Language
##A templating system thats good for outputting HTML, for Javascript and Python.

TATL templates are expressive, easy to learn, and cross easily from
server to client. TATL uses the natural block structure in your HTML code,
resulting in less repetition and more natural indentation.

Templates are precompiled into either Python or Javascript and then loaded
as modules.

There are 2 special tags and 6 special attributes:

    <do>
    <else>
    def=
    set=
    for=
    if=
    param=
    use=

Extended attributes:

    for="var in expr"
        Repeats tag, with {var} now available elsewhere in tag contents.
    for="expr"
        Same, var assumed to be . (dot).
    for
        Same, var and expr assumed to be . (dot).
    for="key, value in expr"
        When iterating over a map, gives key and value (sorted by key). When iterating over
        a list, gives index, value where index is 0-based.
    for="key, value in expr #unsorted"
        As above, but the keys and value are unsorted.
    for="var = expr; var2 = expr; key in expr"
        Set some variables before evaluating the expr

    if="expr"
        If the expression is false, do not include or the tag or the content or execute any
        substitions within. When <else> is present in tag, include the tag and content before
        the else if the expression is false, or the tag and content after the else if the
        expression is true.
    if
        If any variable substitutions are empty, elide this whole tag. Empty values are null
        and false. Also allows else as above.
    if="var = expr; var2 = expr; expr"
        Set some variables before evaluating the expr

    def="name(arg, arg)"
        Define a macro. Calling the macro will return the tag and its contents. The tag won't
        be included in the output at this location. Note that functions can be defined after
        they are called by a template. Functions do not have access to any variables defined
        thus far, only parameters.
    def="name(arg, arg, arg='default') |filter1|filter2"
        Like python decorators, name will be set to filter1(filter2(foo)). A primary use of
        filters is caching.
    def="name()"
        Macro with no args. You still have to call it.
    def="name(*)"
        Macro with args placeholder. Any variables defined by param="" or free variables
        (undefined variables) will become parameters.
    def="name(arg) = expr"
        Macro with result defined by expr. Can reference "." in expr, which is what would have
        been returned

    set="var"
        Sets variable to be the tag with all substitutions executed.
    set="var|filter"
        Sets var to be `filter(_tag_)`.
    set
        For `<do>` tag, same as set="inner". For other tags, same as set="_tagname_|contents"

    param="var"
        Define a parameter, scoped to the nearest def=. The parameter can be accessed anywhere
        in the scope; even if the tag itself isnt included/processed due to an if=. Within the
        tag, the parameter can be accessed by {.}.
    param
        Defines a parameter with the tag name, or for the <do> tag, named "inner".
    param="var, var"
        Defines multiple paramters. {.} is not set.

    use="template::html(expr, expr)"
        Set "inner" to be the tag with all substitutions executed, then call the given macro,
        passing in arguments as specified. The result is then used in place of the current tag.
    use="template::html"
        Call the given macro, automatically finding parameters from local variables.
    use="var = expr; var2 = expr; template::html"
        Same as above, but with some variables already set.

Variable substitution

    Variable substitution occurs in text nodes, and in normal attributes. In special
    attributes, where expr is called for, just use the {var} syntax but remove the parens
    (eg if="x", not if="{x}").

    {var}
        Simple variable substitution. Value is inserted in document, with context-sensitive
        quoting.
    {var.attr}
        Looks up attribute or key from object or map.
    {template::var}
        Access macro from template, or function from external module.
    {.}
        Within a for= or with=
    {var[0]}
    {.[0]}
    {var[var]}
        Can index with numbers or variables

    {macro(var, var)}
        Call macro

    {1...5}
        The numbers 1 up to and including 5 ie inclusive range (1, 2, 3, 4, 5)
    {0..5}
        The numbers 0 up to 5 ie exclusive range (0, 1, 2, 3, 4)

    {[var, "val", 3]}
        A list of three values. Would be outputted with one space between contents, eg
        "var val 3".
    {[var, "val", 3, *0..9]}
        A list of three values with inline splice.
    {{name: var1, "a key": "value"}}
        A map with keys "name" and "a key". Any value can be stored in a map; only numbers
        and strings can be keys. Would be outputted in JSON format.
    {{name: var1, name2: "value", *foo, name3: "value"}}
        A map, with inline splice. This creates a new map (foo is not modified) where the keys
        "name" and "name2" override the values in foo and foo overrides "name3".

    {expr |afilter}
        After evaluating expression, look up the filter function and call it. If there is no
        filter function, look up a locally defined function.
    {expr |module::func}
        Look up func in module and call it.

    {test ? value1 : value2}
        Ternary. Valid tests are a eq b, a ne b, a lt b, a lt b lt c, etc, (and le gt ge)
        a ~ /regex/, and a truthy test, with just the expression.
    {test ? value1}
        Ternary, value2 assumed to be empty
    {expr ?: default}
        Use the value of expr or default if not defined.
    {test ?}
        Either true or false. tests are not allowed in other places where expressions are
        allowed so this is useful to either do a boolean comparison elewhere or to coerce an
        expression to true/false.

    {var = "value"}
    {var = expr}
        expression or assignment. Value is not inserted into doc
    {var = expr; var}
        Same, but then a value is inserted.

    {var ?= value}
        Same as {var = var ?: value}



Special tags / quoting

    <do>
        Without attrs, this tag just disappears in the output. Which is useful to do with some
        of the special attributes above.

    <else/>
        No content (like <br>). Only allowed tags are if="". This should be used within a <do>
        only, otherwise the compiler will have to synthesize
        tags.

    {{ }}
        Doubled braces insert a single brace.

    <!-- -->
        Content within comments is not processed, and is not included in the document.
    <!--[ ]-->
        Content within comments beginning with [ is included in the document.
    <!--{ }-->
        Comments beginning with { are parsed as JSON to form front matter.
    # comment
        Comments starting with a hash sign can also appear at the end of special attributes
        and substitutions ({}).
    {# Another comment}


    <html param= use= def=>
        Only a few attrs are allow on the <html> root tag. There is an implied def="html(*)".

    <style>, <script>
        No substition occurs in <style> or <script>

    <label>, <output>
        for= does not have extended meaning.

Builtins

    len(x) -- return length of list
    true
    false
    null
    sum(nums) -- return sum of list of numbers (null if any arent numbers)
    forloop(iter, opts) -- swiss army knife of looping
    contents(inner) -- strip outer tag
    tag(name, attrs, inner) -- wrap with tag
    attrs(attrmap, inner) -- add attributes to outer tag

Built in filters

    url
    safe
    trim

###Compatibility

|Environment|Min version|Runtime?|Compiler?|Package?|
|-----------|-----------|--------|---------|--------|
|Python 2   |2.7        |Yes     |Yes      |Soon    |
|Python 3   |3.4        |Yes     |No       |No      |
|node       |???        |Yes     |No       |No      |
|Chrome     |???        |Yes     |No       |No      |
|Firefox    |???        |Yes     |No       |No      |
|IE         |???        |Yes     |No       |No      |
|Safari     |???        |Yes     |No       |No      |

###Needed and Possible changes

* Contextual quoting
* Placeholders -- need fixes
* Limit loading to specified modules
* packaging... npm, pip?
* Watch compiler
* Client code to reload changes
* Generate shadow dom code eg mithril
* The parser. bs4 + lxml adds <html><body><p> and loses line info. HTMLParsers() requires sax rewrite but seems more reliable.
* Pure python3 compiler?
* PyPy, Jython - check speed?
* js - use string concatenation. It's miles faster on browsers.
* Babel? Whats the JS solution?
* any and all -- boolean quantifiers
* Expand front matter to use built-in value syntax, (which is basically JSON5). // and /* */ Comments
* Further builtins... min, max, reversed, sorted, zip... groupby, batch...
