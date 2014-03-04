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

	Variable substitution occurs in text nodes, and in normal attributes. In extended attributes, where expr 
	is called for, just use the {var} syntax but remove the parens.
	
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
				
	{macro(var, var)}
		Call macro
		
	{var = "value"}
	{var = expr}
		expression or assignment. Value is not inserted into doc
	{var = expr; var}
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
		A map, with inline splice
		
	{expr |afilter}
		Override the default quoting on the expression. 
	
	{test ? value1 : value2}
		Ternary. Valid tests are a eq b, a ne b, a lt b, a lt b lt c, etc, (and le gt ge)
		a ~ /regex/, and a truthy test, with just the expression. 
	{test ? value1}
		Ternary, value2 assumed to be empty
	{test ?: value2} 


Special tags / quoting

	<do>
		Without attrs, this tag just dispapears in the output. Which is useful to do with some of the special attributes above.
		This is process="content"
		
	<else/>
		No content (like <br>). Only allowed tags are if="". This should be used within a <do> only, otherwise the compiler will have to synthesize 
		tags.

	{{ }}
		Doubled braces insert a single brace.

	<!-- --> 
		Content within comments is not processed, and is not included in the document.
	<!--[ ]--> 
		Content within comments beginning with [ is not included in the document.
	<!--{ }-->
		Comments beginning with { are parsed as JSON to form front matter.
		
	<html param= use= def=>
		Only a few attrs are allow on the <html> root tag. There is an implied def="html(*)".
		
	<style>
		No substition occurs in <style> or <script>
		
	<label>, <output>
		for= does not have extended meaning.

Needed and Possible changes

* IR /OpList -- lvars /rvars etc should be lazy per target like code(). Move all code out of ExprSemantics. Simplify the logic, there are may base classes.
* packaging... npm, pip?
* The parser. bs4 + lxml adds <html><body><p> and loses line info. HTMLParsers() requires sax rewrite but seems more reliable  
* More python versions... 3.4, maybe 2.6?
* js - use string concatenation. Its miles faster on browsers.
* py - Re-deploy peepholers
* Babel? Whats the JS solution?
* Do filters need to be special? Could we just get people to call {safe(expr)}? Could expr1|foo(*,expr2) be syntax for foo(expr1, expr2) or similar? 

Built in utils
	forloop
	trim
	batch(value, linecount, fill_with=None)
	dictsort
	group
