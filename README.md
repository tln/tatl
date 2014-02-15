t template language

Tag (well, more *attribute*) based template language. Because indentation of other languages sucks IMO.

	<do>
	<else>
	def=
	set=
	for=   except on <label> <output>
	if=
	param=
	use=

Extended attributes:

	for="var in expr"
		Repeats tag, with {var} now available elsewhere in tag contents.
		Can use $var in other attributes of same tag. Cannot repeat on tag.
	for="expr"
		Same, var assumed to be {(_)} {.}
	for
		Same, var and expr assumed to be . 
	for="key, value in expr"
		When iterating over a dict. Fancier destructuring not possible.
	for="var = expr; var2 = expr; key in expr"
		Set some variables before evaluating the expr
				
	if="expr"
		If the expression is false, do not include or the tag or the content or execute any substitions within. Also allows 
		<else> tag.
	if
		If any variable substitutions are empty, elide this whole tag (this can be spelled elide or elide="elide").
	if="var = expr; var2 = expr; expr"
		Set some variables before evaluating the expr
	
	def="name(arg, arg)"
		Define a macro. Calling the macro will return the tag and its contents. The tag won't be included in the output at this location.
	def="name(arg, arg, arg='default') |filter"
		Like python, name will be set to decorator1(decorator2(foo)). A primary use of decorators is caching.
	def="name()"
		Macro with no args. You still have to call it.
	def="name(*)"
		Macro with args defined by param="".
	def="name(arg) = expr"
		Macro with result defined by expr. Can reference "Result" in expr, which is what would have been returned

	set="var = expr; var2 = expr"
		Defines some variables.
	set="var"
		Same as "var = Tag()". Tag() returns on object with keys for .name .attrs .contents
	set 
		Defines a variable named for the id="" or, for head and body tags, the tag name.
		
	param="var"
		Define a parameter, scoped to the nearest def= with (*). The parameter can be accessed anywhere 
		in the scope; even if the tag itself isnt included/processed due to an if=. Within the tag, the 
		parameter can be accessed by {.}.
	param
		Defines a parameter named for the id="" or, for head and body tags, the tag name.
	param="var, var"
		Defines multiple paramters. {.} is not set.
		
	use="template::html(expr, expr)"
		After processing all tags, call the given macro, passing in args from the current execution. The result
		is then used in place of the current tag. If the result was a Tag() object, it's formatted.
	use="template::html"
		Call the given macro, automatically finding parameters from local variables.
	use="var = expr; var2 = expr; template::html"
		Same as above, but with some variables already set.
		
Variable substitution
	Variable substitution occurs in text nodes, and in normal attributes. In extended attributes, where expr is called for, just use the {var} or {(expr)} syntax but remove the parens.
	
	{var}
		Simple variable substitution. Value is inserted in document, with context-sensitive quoting.
	{var.var}
		Uses django style logic to descend "paths"
	{template::var}
		Access name from template
	{.}
		Within a for= or with=
	{var[0]}
	{.[0]}
	{var[var]}
		Can index with numbers or variables
		
	[NOTE: not implemented and we may have to save parens for grouping!]
	{(expr)}
		expression in python. Parens can be used in expr, as long as its balanced.
	{(dot)}
	{(dot.foo)}
		Equivalent to {.} and {.foo}
		
	{macro(var, var)}
		Call macro
		
	{var = path}
	{var = "value"}}
	{var = expr}
		expression or assignment. Value is not inserted into doc
	{var = (path); path}
		Same, but then a value is inserted.
	
	{1...5}
		The numbers 1 up to and including 5 ie inclusive range (1, 2, 3, 4, 5)
	{0..5}
		The numbers 0 up to 5 ie exclusive range (0, 1, 2, 3, 4)
		
	{[var, "val", 3]}
		A list of three values
	{[var, "val", 3, *0..9]}
		A list of three values with inline splice
	{{name: var1, name2: "value", *foo, name3: "value"}}
		A map 
		
	{expr |afilter}
		Override the default quoting on the expression. 
	
	{test ? value : value}
		Ternary. Valid tests are a == b, a!= b, a < b, a< b < c, etc, (and <= > >=),
		a ~ /regex/, and a truthy test, with just the expression. 
	
Syntax
	name = [a-zA-Z_][a-zA-Z_]+
	path = name | path "[" expr "]" | name "." path | \.+ path
	value = path | \d+ | \d+\.\d+ | (["']).*?\1
	regex = /.*?/
	test = value | value "==" value | value "~" regex
	ternary = test "?" value ":" value
	matcher = "~~" regex | "~=" value
	matchlist = value ( matcher "->" value )* (":" value)
	range = value (".."|"...") value
	list = "[" expr ("," expr)+ ","? "]"
	map = "{" name ":" expr
	expr = matchlist | ternary | value | range

Special tags
	<do>
		Without attrs, this tag just dispapears in the output. Which is useful to do with some of the special attributes above.
		This is process="content"
		
	<else/>
		No content (like <br>). Only allowed tags are if="". This should be used within a <do> only, otherwise the compiler will have to synthesize 
		tags.

	<!-- --> 
		Content within comments is not processed, and is not included in the document.
		
	<html param= filt=>
		Only a few attrs are allow on the <html> root tag. There is an implied def="html(*)".
		
	<style>
	 	For style without a type or with type text/css, $var is used as an equivalent to {var}. Fancier forms not supported.
	<style type="text/sass">
		Post processes SASS; also any $vars that are used but NOT defined in the SASS will be auto-defined.

	<script>
		Default processor is "no". There's way too much overlap with javasript.
	<script filt="inject_vars('a, b, c')">
		Script tags need special handling. No substitution occurs within scripts, whether or not they are wrapped in a comment.
		This is because the variable syntax is a conflict. Instead there is a convenient way to set parameters. With inject_vars, they
		become global variables. Also filt="inject_args('a, b, c')"
	<script filt="exec">
		Execute the script now, in Python
		
	<label>, <output>
		for= does not have extended meaning.

Template inheritence
	filt="use(template::html)"
		Inherit the given template.	The output from this template is ignored; the variables set as a side-effect will be used
		as the parameters to the template; and then that template will be called.
		----- base.html -----
		<html param="head, title, body, h1">
		<head>
		<title extend>$title</title>
		</head>
		<body>
			<h1>$(h1 or title)</title>
			<nav></nav>
			<div id="content">$body</div>
		</body>
		</html>
		----- layout1.html -----
		<html inherit="base" param="title,articles">
		<body>
			<section for=articles>
				<h1>{.title}</h1>
			</section>
		</body>
		</html>
		
		Inherit can work with macros, or even functions from modules too. 

Flavors
	process="t.ex"
		T template language with {()} and process="exec" support. Looks for tags as spelled above.
		
	data-process="t.ex"
		T template language with {()} and process="exec" support. Looks for tags with data- prefixes,
		so as to be more "compliant". Tags become <t-do> and <t-else>.

	t:xmlns="http://ttmpl.com/t.ex"
		Looks for attrs with namespaces.
	
Processing logic
	Start processing. Determine initial flavor from start tag
	
	Determine processor (process). Processor may turn off ALL processing.

	Handle extend -> param, replace, add
	
	Handle param. Add name to current variables, and to template parameters. If we're in a parent template,
	
	Handle def. Set name to function and continue below tag. Steps below occur when 
	tag is called.
	
	Handle replace. for, repeat, elide conflict.
	
	Handle repeat. for, if confict.

	Handle for.
	
	Handle add (for each)
	
	Handle elide (for each)
	
	Handle ws (for each)
