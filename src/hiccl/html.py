"""Hiccl HTML5 Tag Helpers — Pythonic functional declarations of HTML5 elements."""

from hiccl.hiccup import tag

# Common layout and semantic elements
div = tag("div")
span = tag("span")
p = tag("p")
a = tag("a")
img = tag("img")
br = tag("br")
hr = tag("hr")

# Headings
h1 = tag("h1")
h2 = tag("h2")
h3 = tag("h3")
h4 = tag("h4")
h5 = tag("h5")
h6 = tag("h6")

# Structural / Semantic elements
header = tag("header")
footer = tag("footer")
nav = tag("nav")
main = tag("main")
section = tag("section")
article = tag("article")
aside = tag("aside")

# Lists
ul = tag("ul")
ol = tag("ol")
li = tag("li")

# Forms & Inputs
form = tag("form")
button = tag("button")
label = tag("label")
input_ = tag("input")  # Using input_ to avoid collision with built-in input()
textarea = tag("textarea")
select_ = tag("select")  # Using select_ to avoid potential namespace confusion
option = tag("option")
fieldset = tag("fieldset")
legend = tag("legend")

# Tables
table = tag("table")
thead = tag("thead")
tbody = tag("tbody")
tfoot = tag("tfoot")
tr = tag("tr")
td = tag("td")
th = tag("th")

# Multimedia & Embedded content
iframe = tag("iframe")
canvas = tag("canvas")
svg = tag("svg")
path = tag("path")

# Custom elements / scripting
script = tag("script")
style = tag("style")
pre = tag("pre")
code = tag("code")
