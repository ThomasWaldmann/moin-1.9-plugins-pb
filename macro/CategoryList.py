#format python
"""
MoinMoin plugin: 'CategoryList' macro.

A macro to list category pages, with hints on tagged pages (such as
the number of pages belonging to that category). It can also generate
a tag cloud.

$Revision: 193 $
$Id: CategoryList.py 193 2010-05-14 12:31:05Z pascal $

-------------------------------------------------------------------------------

@copyright: (C) 2008-2009 Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com>
@license: GPL

-------------------------------------------------------------------------------

Usage:
  <<CategoryList>>
  <<CategoryList(KEYWORD=VALUE [, ...])>>

General keywords:

  Help                = 0, 1, 2
                        Displays 1:short or 2:full help in the page.
                        Default: 0 (i.e. no help).

  ByPages             = 0, 1, 2
                        If 0, list categories;
                        if 1, list pages;
                        if 2, list pages, including those without categories;
                        Default: 0 (list categories)

  Cloud               = 0, 1 or more
                        When 1 or more and ByPages is 0, output as cloud.
                        The value+1 specifies the maximum font size in em.
                        Default: 0

  Pages               = 'EXPRESSION'
                        A string containing a Python expression,
                        applied on each existing page, that may
                        use boolean operators, parentheses, and
                        these available function:
                        - logical operators (and, not, or)
                        - name_contains(NAME)
                        - name_startswith(NAME)
                        - name_endsswith(NAME)
                        - name_is(NAME)
                        - name_matches(REGEX)
                        - contains(REGEX)
                        - this      --> the current page
                        - children  --> sub-pages of the current
                        - has_child --> pages having children
                        - system    --> is a system page
                        - regular   --> not tmp/dict/categ/grp/sys
                        - this_page --> is the current page
                        - others    --> is not the current page
                        - all       --> all pages
                        If the expression is missing, the current
                        page is used.
                        Default: 'regular'

  Format              = 'EXPRESSION'
                        A formatting string containing wiki
                        markup, to display each category page.

                        When ByPages=0, may contain these tokens:
                        - %(categorypage)s  category page name
                        - %(categoryname)s  category name
                        - %(pages)s         pages nr per category
                        - %(pagelist)s      links to pages per category
                        - %(unit)s          unit string, dep. on pages nr

                        When ByPages>0, may contain these tokens:
                        - %(page)s          page path
                        - %(pagename)s      page path (pretty)
                        - %(pagelastname)s  page name without parent page
                        - %(categorypages)s list of category pages
                        - %(categorynames)s list of categories
                        - %(categorylinks)s list of category links

                        Default when ByPages=0 :
                          " * [[%(categorypage)s|%(categoryname)s]] ~-(''%(pages)d %(unit)s'')-~"
                        Default when ByPages>0 :
                          " 1. [[%(page)s|%(pagelastname)s]] ~-(''%(categorynames)s'')-~"

  Header              = 'TEXT'
                        Text preceeding the list or cloud, if pages were found.
                        Default: None

  EmptyHeader         = 'TEXT'
                        Text preceeding the list or cloud, if no pages were found.
                        Default: None

  Unit                = 'NAME, NAME, ...'
                        A string containing comma-separated words
                        used when the number of pages is 0, 1,
                        etc.
                        Default: 'page, page, pages'

  CategoryWord        = 'NAME'
                        The string used to mark categories.
                        Default: 'Category'

  Category            = 'NAME'
                        Optional category name to limit search to a
                        given category. This name may or may not begin
                        with the string specified by CategoryWord.
                        Default: omitted                        

  Reverse             = 0|1
                        Reverses the sort order.
                        Default: 0 (forward sorting)

Keywords can be also given in upper or lower cases, or abbreviated.
Example: Pages, PAGES, pages, p, etc.

-------------------------------------------------------------------------------

Examples:
  see
  http://ten.homelinux.net/productivity/MoinMoinExtensions/macro/CategoryList

-------------------------------------------------------------------------------

ChangeLog:

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2010-05-14
  * Compatibility for MoinMoin 1.9 and above
  * Implemented a simple parser to replace eval() which was a security hole
    (a 2nd eval() usage remains to be fixed)
  * Fixed usage(): HTML-escape text to have correct display of <>& chars

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-13
  * Added category cloud, and system pages

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-09
  * Compatibility for MoinMoin 1.7 and above

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com>:
[v1.0.0] 2008-11-19 Pascal Bauermeister
  * Original version

"""


DEF_P   = 'regular'
DEF_U   = 'page, page, pages'
DEF_FC  = " * [[%(categorypage)s|%(categoryname)s]] ~-(''%(pages)d %(unit)s'')-~"
DEF_FP  =  " 1. [[%(page)s|%(pagelastname)s]] ~-(''%(categorynames)s'')-~"


# Imports
import re, sys, StringIO, urllib, sha, math
from string import ascii_lowercase, maketrans
from MoinMoin import config, wikiutil, version, search
from MoinMoin.Page import Page
    
Dependencies = ["pages"]
NAME = __name__.split(".")[-1]


class _Error(Exception):
    pass

def escape(s):
        return s \
               .replace('&', '&amp;') \
               .replace('<', '&lt;') \
               .replace('>', '&gt;')


def split_title(s):
    s = s.replace("/", " / ")
    return config.split_regex.sub(r'\1 \2', s)


def execute(macro, text, args_re=None):
    try:
        return _execute(macro, text)
    except _Error, msg:
        return """
        <p><strong class="error">
        Error: macro %s: %s</strong> </p>
        """ % (NAME, msg)


def _delparam(keyword, params):
    value = params[keyword]
    del params[keyword]
    return value


FAKETRANS = maketrans("","")
def _param_get(params, spec, default):

    """Returns the value for a parameter, if specified with one of
    several acceptable keyword names, or returns its default value if
    it is missing from the macro call. If the parameter is specified,
    it is removed from the list, so that remaining params can be
    signalled as unknown"""

    # param name is litteral ?
    if params.has_key(spec): return _delparam(spec, params)

    # param name is all lower or all upper ?
    lspec = spec.lower()
    if params.has_key(lspec): return _delparam(lspec, params)
    uspec = spec.upper()
    if params.has_key(uspec): return _delparam(uspec, params)

    # param name is abbreviated ?
    cspec = spec[0].upper() + spec[1:] # capitalize 1st letter
    cspec = cspec.translate(FAKETRANS, ascii_lowercase)
    if params.has_key(cspec): return _delparam(cspec, params)
    cspec = cspec.lower()
    if params.has_key(cspec): return _delparam(cspec, params)

    # nope: return default value
    return default


def _usage(full = False):

    """Returns the interesting part of the module's doc"""

    import cgi
    if full:
        return cgi.escape(__doc__)

    lines = __doc__.replace('\\n', '\\\\n'). splitlines()
    start = 0
    end = len(lines)
    for i in range(end):
        if lines[i].strip().lower() == "usage:":
            start = i
            break
    for i in range(start, end):
        if lines[i].startswith('--'):
            end = i
            break
    return cgi.escape('\n'.join (lines [start:end]))


def _re_compile(text, name):
    try:
        return re.compile(text, re.IGNORECASE|re.MULTILINE|re.DOTALL)
    except Exception, msg:
        raise _Error("%s for regex argument %s: '%s'" % (msg, name, text))


def _get_all_pages(request):
    return request.rootpage.getPageList()


###############################################################################

from MoinMoin import wikiutil
def _format (src_text, request):
    """Parse the text (in wiki source format) and make HTML, after
    diverting sys.stdout to a string"""
    
    Parser = wikiutil.searchAndImportPlugin(request.cfg,
                                            "parser",
                                            request.page.pi['format'])
    return wikiutil.renderText(request, Parser, src_text).strip()

###############################################################################

import cStringIO, tokenize

class SimpleEval(object):

    def quark (self, token, allow_name=False):
        if token[0] is tokenize.NAME:
            if token[1] == "True":
                return True
            elif token[1] == "False":
                return False
            elif allow_name:
                return token[1]

        if token[0] is tokenize.STRING:
            return unicode(token[1][1:-1].decode("string-escape"), "utf8")
        elif token[0] is tokenize.NUMBER:
            try:
                return int(token[1], 0)
            except ValueError:
                return float(token[1])
        elif token[1] == "-":
            token = self.next()
            return -self.atom(token)
        else:
            raise SyntaxError("malformed expression (%s)" % `token[1]`)
    
    def atom(self, token, name_key=False):
        if token[1] == "{":
            out = {}
            token = self.next()
            while token[1] != "}":
                key = self.quark(token, name_key)
                token = self.next()
                if token[1] != ":":
                    SyntaxError("expected ':' (%s)" % token[1])
                token = self.next()
                value = self.atom(token)
                out[key] = value
                token = self.next()
                if token[1] == ",":
                    token = self.next()
            return out
        elif token[1] == "(":
            out = []
            token = self.next()
            has_comma = False
            while token[1] != ")":
                out.append(self.atom(token))
                token = self.next()
                if token[1] == ",":
                    has_comma = True
                    token = self.next()
            if len(out) == 1 and not has_comma:
                return out[0] # (x)
            else:
                return tuple(out) # (x,...)
        else:
            return self.quark(token)

    def eval(self, source):
        src = cStringIO.StringIO(source).readline
        tok = tokenize.generate_tokens(src)
        self.next = tok.next
        return self.atom(self.next())

    def params_eval(self, source):
        source = "{%s}" % source.strip()
        src = cStringIO.StringIO(source).readline
        tok = tokenize.generate_tokens(src)
        self.next = tok.next
        return self.atom(self.next(), name_key=True)

def parseArgs(s):
    """Parse the given string and return a dict."""
    return SimpleEval().params_eval(s.strip().encode('utf8'))

###############################################################################

# The "raison d'etre" of this module
def _execute(macro, text):

    result = ""
    if not text:
        text = ""
    
    try:
        params = parseArgs(text)
        #params = eval("(lambda **opts: opts)(%s)" % text,
        #              {'__builtins__': []}, {})
    except Exception, msg:
        raise _Error("""<pre>malformed arguments list:
        %s<br>cause:
        %s
        </pre>
        <br> usage:
        <pre>%s</pre>
        """ % (text, msg, _usage()))

    # args
    arg_pages            = _param_get(params, 'Pages'   , DEF_P)
    opt_bypages          = _param_get(params, 'ByPages' , 0)
    opt_cloud            = _param_get(params, 'Cloud'   , 0)
    opt_format           = _param_get(params, 'Format'  , None)
    opt_header           = _param_get(params, 'Header'  , None)
    opt_empty_header     = _param_get(params, 'EmptyHeader', None)
    opt_unit             = _param_get(params, 'Unit'    , DEF_U).split(',')
    opt_help             = _param_get(params, 'Help'    , 0)
    opt_debug            = _param_get(params, 'Debug'   , 0)

    opt_category_word    = _param_get(params, 'CategoryWord',  "Category")
    opt_category         = _param_get(params, 'Category', None)

    opt_reverse          = _param_get(params, 'Reverse',  0)

    if opt_format is None:
        if opt_bypages: opt_format = DEF_FP
        else:           opt_format = DEF_FC
        
    # help ?
    if opt_help:
        return """
        <p>
        Macro %s usage:
        <pre>%s</pre></p>
        """ % (NAME, _usage(opt_help==2))

    # check the args a little bit
    if len(params):
        raise _Error("""unknown argument(s): %s
        <br> usage:
        <pre>%s</pre>
        """ % (`params.keys()`, _usage()))

    # get a list of pages matching the PageRegex
    else:

        # things we'll need
        this_page = macro.formatter.page.page_name

        def name_contains(what):
            what = what.replace("_", " ")
            return page.find(what) >= 0

        def name_is(what):
            what = what.replace("_", " ")
            return page == what

        def name_startswith(what):
            what = what.replace("_", " ")
            return page.startswith(what)

        def name_endswith(what):
            what = what.replace("_", " ")
            return page.endswith(what)

        def name_matches(what):
            what = what.replace("_", " ")
            if nm_dict.has_key(what):
                rx = nm_dict[what]
            else:
                rx = _re_compile(what, 'name_matches')
                nm_dict[what] = rx
            return rx.search(page) is not None

        def contains(what):
            if hits_dict.has_key(what):
                hits = hits_dict[what]
            else:
                parser = search.QueryParser(regex=1)
                query = parser.parse_query(what)
                results = search.searchPages(macro.request, query)
                hits = [h.page_name for h in results.hits]
                hits_dict[what] = hits
            return page in hits

        def name_is_this(what):
            return name_is(macro.request.page.page_name)

        def name_is_child(what):
            return name_startswith(this_page + "/")

        def has_children(what):
            me = what+"/"
            for p in all_pages:
                if p.startswith(me): return True
            return False

        all_pages = _get_all_pages(macro.request)

        hits = []
        hits_dict = {}
        nm_dict = {}

        cfg = macro.request.cfg

        for page in all_pages:
            is_syspage = wikiutil.isSystemPage(macro.request, page)
            is_special = ( \
                name_matches(cfg.page_category_regex) or \
                name_matches(cfg.page_dict_regex) or \
                name_matches(cfg.page_group_regex) or \
                name_matches(cfg.page_template_regex) \
                ) and not "/" in page
            is_regular = not (is_syspage or is_special)

            locs = {
                # functions:
                'name_contains': name_contains,
                'name_is': name_is,
                'name_startswith': name_startswith,
                'name_endswith': name_endswith,
                'name_matches': name_matches,
                'contains': contains,
                # vars (for each page we must rebuild this dict for them):
                'regular': is_regular,
                'system' : is_syspage,
                'this_page' : page == this_page,
                'others' : page != this_page,
                'all' : True,
                'this': name_is_this(page),
                'children': name_is_child(page),
                'has_child': has_children(page),
                }

            try:
                if not eval(arg_pages, {'__builtins__': []}, locs):
                    continue
            except Exception, msg:
                raise _Error("""invalid expression for Pages argument: %s
                <br>(reason: %s)
                """ % (arg_pages, msg))

            hits.append(page)

    # Search into the collected pages for category keywords
    categories_hits = {}
    pages_hits = {}
    content_regex = r"\b%s\S+\b" % opt_category_word

    # Want a particular category ?
    if opt_category:
        if opt_category.startswith(opt_category_word):
            opt_category = opt_category[len(opt_category_word):]
        category_regex = r"\b%s%s\b" % (opt_category_word, opt_category)
        category_rx = re.compile(category_regex)

    # Ignore categories ?
    if opt_bypages == 2:
        for p in hits: pages_hits[p] = set()

    parser = search.QueryParser(regex=1, case=1) # case-sensitive
    query = parser.parse_query(content_regex)
    results = search.searchPages(macro.request, query)
    is_name_rx = re.compile('^\w+$')
    for hit in results.hits:

        # if particular category specified and not here, do not keep
        # this hit
        if opt_category:
            found = False
            for match in hit.get_matches():
                cat = match.re_match.group()
                if category_rx.match(cat): found = True
            if not found: continue

        # keep this hit and remember to what it belongs
        for match in hit.get_matches():
            if hit.page_name not in hits: continue
            cat = match.re_match.group()
            if not is_name_rx.match(cat): continue
            # remember category
            if not categories_hits.has_key(cat):
                categories_hits[cat] = set()
            categories_hits[cat].add(hit.page_name)
            # remember page
            if not pages_hits.has_key(hit.page_name):
                pages_hits[hit.page_name] = set()
            pages_hits[hit.page_name].add(cat)


    # format the output
    res = []
    cat_offset = len(opt_category_word)

    if opt_bypages == 0 and not opt_cloud:
        keys = sorted(categories_hits.keys())
        if opt_reverse: keys.reverse()
        for k in keys:
            v = sorted(categories_hits[k])  # k=cat, v=pages
            #print k,'<br>',v,'<br><br>'
            l = len(v)
            l2 = l
            if l2 >= len(opt_unit): l2 = len(opt_unit)-1
            unit = opt_unit[l2]
    
            pl = [ "[[%s|%s]]" % (p, split_title(p)) for p in v ]
            pl = ', '.join(pl)
            w = opt_format % {
                "categorypage": k,
                "categoryname": split_title(k[cat_offset:]),
                "pages"       : l,
                "pagelist"    : pl,
                "unit"        : unit,
                }
            res.append(w)

    elif opt_bypages == 0 and opt_cloud:
        keys = sorted(categories_hits.keys())
        if opt_reverse: keys.reverse()
        min_l = 1000
        max_l = 0
        res2 = []
        for k in keys:
            v = categories_hits[k]
            l = len(v)
            l2 = l
            if l2 >= len(opt_unit): l2 = len(opt_unit)-1
            unit = opt_unit[l2]
            max_l = max(max_l, l)
            min_l = min(min_l, l)
            fmt = "[[%(categorypage)s|%(categoryname)s]]"

            pl = [ "[[%s|%s]]" % (p, split_title(p)) for p in v ]
            pl = ', '.join(pl)
            category_name = split_title(k[cat_offset:])
            w = fmt % {
                "categorypage": k,
                "categoryname": category_name.replace(" ", u"\u00A0"),
                "pages"       : l,
                "pagelist"    : pl,
                "unit"        : unit,
                }
            res2.append((
                _format(w, macro.request),
                l,
                "%s: %d %s" % (category_name, l, unit)
                ))
        html = ""
        span = float(max_l - min_l)
        if opt_header and len(res2):
            html += _format(opt_header, macro.request) + "<BR/>"
        if opt_empty_header and not len(res2):
            html += _format(opt_empty_header, macro.request) + "<BR/>"
        for w, l, title in res2:
            # TODO: in w, remove the enclosing <p>
            l = float(opt_cloud) * ( 0.75 + (l - min_l) / (span/1.25) )
            html += """
            <span style="font-size: %fem" title="%s"> %s </span> &nbsp;
            """ % (l, title, w)
        return html
        
    elif opt_bypages:
        keys = sorted(pages_hits.keys())
        if opt_reverse: keys.reverse()
        for k in keys:
            v = sorted(pages_hits[k])  # k=page, v=cats
            l = len(v)
            l2 = l
            if l2 >= len(opt_unit): l2 = len(opt_unit)-1
            unit = opt_unit[l2]

            if len(v):
                cpages = v
                cnames = [ split_title(p[cat_offset:]) for p in v ]
                clinks = [ "[[%s|%s]]" % (p, split_title(p[cat_offset:])) \
                           for p in v ]
                cpages = ', '.join(cpages)
                cnames = ', '.join(cnames)
                clinks = ', '.join(clinks)
            else:
                cpages = "``"
                cnames = "``"
                clinks = "``"

            w = opt_format % {
                "page"          : k,
                "pagename"      : split_title(k),
                "pagelastname"  : split_title(k.split("/")[-1]),
                "categorypages" : cpages,
                "categorynames" : cnames,
                "categorylinks" : clinks,
                }
            res.append(w)

    html = ""
    if opt_debug:
        html += "<pre>%s</pre>\n" % "\n".join(res)
    if opt_header and len(res):
        html += _format(opt_header, macro.request)
    if opt_empty_header and not len(res):
        html += _format(opt_empty_header, macro.request)
    html += _format("\n".join(res), macro.request)
    return html

# end
