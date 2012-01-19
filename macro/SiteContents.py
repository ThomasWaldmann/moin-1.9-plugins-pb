#format python
"""
MoinMoin plugin: 'SiteContents' macro.

Displays a hierarchical sitemap view of the pages your wiki. Can be
used for a site map, or a navigation menu.

 * The selection of pages can be specified by boolean expressions using
   regular expressions.
 * The headings inside the pages are listed too.
 * Optionally, a summary of the pages (or headings) can be displayed.
 * Several options allow to control the generated layout.

For a navigation menu, the theme script should first set the form's
'here' key to the current page name, then embed a page calling the
SiteContents macro.

$Revision: 190 $
$Id: SiteContents.py 190 2010-02-11 18:35:16Z pascal $

-------------------------------------------------------------------------------

@copyright: (C) 2007-2009  Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com>
@license: GPL

-------------------------------------------------------------------------------

Usage:
  <<SiteContents>>
  <<SiteContents(KEYWORD=VALUE [, ...])>>

General keywords:

  Help                = 0, 1, 2      Displays 1:short or 2:full help in the page.
                                     Default: 0 (i.e. no help).

  Format              = 'FMT'        Formatting string to produce wiki text to
                                     display the final result. Use %s to insert
                                     the result.
                                     Default: '%s'

  LinkFormat          = 'FMT'        Format of links to pages.
                                     Default: '[[%(LINK)s|%(DISPLAY)s]]'

  LinkHighlightFormat = 'FMT'        Format to highlight the here-page. The
                                     here-page is specified by a form argument,
                                     in the URL, like this: &here=/my/page
                                     Default: "''' %s '''"  (i.e. bold)
                                     
  Collapse            = NUMBER       If not zero, links with a depth above
                                     this number will be collapsed,
                                     except if it has the same parents
                                     as the here-page.
                                     Default: 0 (i.e. do not collapse)

  CollapsedFormat     = 'FMT'
  OpenedFormat        = 'FMT'


  Pages               = 'EXPRESSION' A string containing a Python expression,
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
                                     Default: 'regular' (i.e. all regular
                                     pages)

  DoListPages         = 0, 1         Shorthand for:
                                       PageDisplayAs='l',
                                       HeadingsEnabled=0,
                                       PageSummaryFormat='%(SUMMARY)s'
                                     Default: 0

  DoSiteMap           = 0, 1         Shorthand for:
                                       PageDisplayAs="hhl",
                                       PageListStructured=1,
                                       HeadingsEnabled=0,
                                       HeadingsDisplay=0,
                                       LinkFormat="~- [ [[%s|%s]] ] -~",
                                     Default: 0

  DoSiteNavigation    = 0, 1         Shorthand for:
                                       PageDisplayAs="l",
                                       HeadingsEnabled=0,
                                       HeadingsDisplay=0,
                                       PageListStructured=1
                                     Default: 0

  DoOnePage           = 0, 1         Shorthand for:
                                       PageDisplayAs="p",
                                       HeadingsEnabled=0,
                                       HeadingsDisplay=0,
                                       PageListStructured=1
                                     Default: 0

  CountsDisplayFormat = 'FMT'        If specified, only display counts. The
                                     format string may contain regular text
                                     and:
                                     %(PAGES)d
                                     %(HEADINGS)d
                                     Default: None

Path-related keywords:

  PageMaxDepth        = NUMBER       The maximum level of subpages.
                                     Default: 0 (i.e. no limit)

  PageMinDepth        = NUMBER       The minimum level of subpages.
                                     Default: 0 (i.e. no limit)

  PageStripLevel      = 0, 1         If 1, strip extraneous leading levels
                                     automatically.
                                     Default: 1 (i.e. strip)

Headings-related keywords:

  HeadingsEnabled     = 0, 1         If 1, collect also headings (pages
                                     with no headings will not be listed
                                     in this case). If 0, do not care
                                     for headings, but just list all
                                     matching pages.
                                     Default: 1 (i.e. collect headings)

  HeadingsDisplay     = 0, 1         If 1, display collected headings; if 0
                                     collect headings but do not display them.
                                     Default: 1 (i.e. display headings)

  HeadingMaxDepth     = NUMBER       The maximum level of heading.
                                     Default: 0 (i.e. no limit)

  HeadingMinDepth     = NUMBER       The minimum level of heading.
                                     Default: 0 (i.e. no limit)

Pages-related keywords:

  PageDisplayAs       = 'H', 'h', 'l', 'p'
                                     If 'H', display pages as
                                     headings;
                                     If 'h', display pages as headings
                                     followed by a link;
                                     if 'l', display pages as list
                                     items, and sets PageSummaryFormat
                                     to '%(SUMMARY)s' by default;
                                     if 'p', concatenates pages contents;
                                     else: do not display pages.
                                     Default: 'h' (i.e. display as headings)

  PageOffset          = NUM          When PageDisplayAs is 'H'or 'h', add NUM
                                     level to the genrated heading.
                                     Default: 1

  PageDisplayLevel    = NUM          Defines which levels of page paths are
                                     displayed. E.g. 2 would strip out the
                                     two first levels.
                                     Default: 0 (i.e. display entire path)

  PageListFormat      = 'FMT'        When PageDisplayAs is 'l', FMT defines
                                     the kind of list.
                                     Default: ' 1. %s' (i.e. num list)

  PageListNoLink      = 0, 1         If 1, when PageDisplayAs is 'l', do not
                                     generate links in heading list or in page
                                     list.
                                     Default: 0 (i.e. generate links)

  PageListStructured  = 0, 1         When PageDisplayAs is 'l', outputs
                                     a structured list.
                                     Default: 0

  PagesOrder          = ('REGEX'...) or 'PAGE_NAME'
                                     With a REGEX list:
                                       A list of regex defining the
                                       sort order of the pages.
                                     With a page name:
                                       The list of page ordering is
                                       defined by the contents of that
                                       page, as a bullet list of page
                                       paths.
                                     The string '*' is special:
                                       instead of being a regex, it
                                       represents all pages not
                                       matching other regexes. It
                                       defines where unordered pages
                                       are inserted in the list. if
                                       omitted, unordered pages are
                                       appended to the end of the
                                       list.
                                     Default: None

  PagesOrderDebug     = 0, 1         If 1, only list unordered pages.
                                     Default: 0

  PagesReverse        = 0, 1         If 1, reverses the pages sort order.
                                     Default: 0 (i.e. ascending order)

Summaries-related keywords:

  Summary             = 'NAME'       Use predefined REGEX named NAME for both
                                     headings and pages. Equivalent to
                                     specifying the same NAME to both
                                     PageSummary and HeadingSummary.
                                     Available:
                                     'italics'    -> ^#*(''[^'].*?[^']''[^'])

  SummaryRx           = 'REGEX'      Defines REGEX for both headings and pages.
                                     Equivalent to specifying the same REGEX to
                                     both PageSummaryRx and HeadingSummaryRx.

  PageSummary         = 'NAME'       Use predefined REGEX named NAME. Available:
                                     'italics'   --> ^#*(''[^'].*?[^']''[^'])

  PageSummaryRx       = 'REGEX'      Regular expression to extract the page
                                     summary. If it contains groups, the result
                                     consists of their concatenation.
                                     Default: None (i.e. do not get summary)

  PageSummaryAsLink   = 0, 1         When listing a page in a list, if the page
                                     has a summary, use it instead of the page
                                     name to create the link to the page.
                                     Default: 0

  PageSummaryFormat   = 'FMT'        Formatting string to produce wiki text
                                     to display the page summary extracted by
                                     PageSummaryRx. Use %(SUMMARY)s to
                                     insert the text found by
                                     PageSummaryRx. Use %(LINK)s to
                                     insert the page link.
                                     Default: '%(SUMMARY)s'

  HeadingSummary      = 'NAME'       Use predefined REGEX named NAME.
                                     Available:
                                     'italics'    -> ^#*(''[^'].*?[^']''[^'])

  HeadingSummaryRx    = 'REGEX'      Regular expression to extract the page
                                     summary. If it contains groups, the result
                                     consists of their concatenation.
                                     Default: TBD

  HeadingSummaryFormat= 'FMT'        Formatting string to produce wiki text
                                     to display the heading summary extracted
                                     by HeadingSummaryRx. Use %s to insert the
                                     text found by HeadingSummaryRx.
                                     Default: '%s'

Keywords can be also given in upper or lower cases, or abbreviated.
Example: EnableHeadings, ENABLEHEADINGS, enableheadings, eh, EH, etc.

-------------------------------------------------------------------------------

Examples:
  see
  http://ten.homelinux.net/productivity/MoinMoinExtensions/macro/SiteContents

-------------------------------------------------------------------------------

TODO:
 * use gettext

 * per page: option to create a new sibling/child page, with an
   arbitrary path, pre-filled by the current path as parent:
   (add page)  <- opens/closes a subsection:
     Create new sibling page [Current/dir/            ]  [Create]
     Create new sub page     [Current/dir/PageName/   ]  [Create]

-------------------------------------------------------------------------------

ChangeLog:

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-12
  * Links can be collapsed

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-09
  * Compatibility for MoinMoin 1.7 and above

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2007-09-14:
  * Improved wiki_text -> html formatter

[v1.2.1] 2007-10-14 Pascal Bauermeister
  * Bug fixed

[v1.2.0] 2007-09-06 Pascal Bauermeister
  * Added PageSummary, HeadingSummary, SummaryRx, Summary, regular,
    this_page, others.

[v1.1.0] 2007-08-30 Pascal Bauermeister
  * Several fixes and improvements

[v1.0.0] 2007-08-09 Pascal Bauermeister
  * Original version

"""

# Imports
import re, sys, StringIO, urllib, sha, math
from string import ascii_lowercase, maketrans
from MoinMoin import config, wikiutil, version, search
from MoinMoin.Page import Page
    
Dependencies = ["pages"]
NAME = __name__.split(".")[-1]

HEAD_RX = re.compile("(?P<eq>=+) *(?P<title>.*?) *=+")


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
class _Error(Exception):
    pass


def split_title(s, enable_split):
    if len(s):
        s = s[0].upper() + s[1:]
    # uncamel a text
    if not enable_split:
        return s
    else:
        return config.split_regex.sub(r'\1 \2', s)

def execute(macro, text, args_re=None):
    try:
        return _execute(macro, text)
    except _Error, msg:
        return """
        <p><strong class="error">
        Error: macro %s: %s</strong> </p>
        """ % (NAME, msg)

def _array2str(a):
    def join_it(x):
        if x.__class__ == unicode or x.__class__ == str:
            return "".join(x)
        else:
            return " ".join(x)

    res = map(join_it, a)
    return res


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

    if full: return __doc__

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
    return '\n'.join(lines[start:end])


def _re_compile(text, name):
    try:
        return re.compile(text, re.IGNORECASE|re.MULTILINE|re.DOTALL)
    except Exception, msg:
        raise _Error("%s for regex argument %s: '%s'" % (msg, name, text))


def _get_all_pages(request):
    return request.rootpage.getPageList()


def get_rx(name):
    dico = {
        "italics": "^#*(''[^'].*?[^']''[^'])",
        }
    try:
        return dico[name]
    except KeyError:
        raise _Error("""unknown name: %s
        <br>(possible: %s)
        """ % (name, ', '.join(dico.keys())))


# The "raison d'etre" of this module
def _execute(macro, text):

    debug_html = ""
    if not text: text = ""

    try:
        params = eval("(lambda **opts: opts)(%s)" % text,
                       {'__builtins__': []}, {})
    except Exception, msg:
        raise _Error("""<pre>malformed arguments list:
        %s<br>cause:
        %s
        </pre>
        <br> usage:
        <pre>%s</pre>
        """ % (text, msg, _usage()))

    DEF_P   = 'name_matches("")'
    DEF_P   = 'regular'
    DEF_PSF = '%(SUMMARY)s'
    DEF_L   = '[[%(LINK)s|%(DISPLAY)s]]'
    DEF_LHI = "''' %s '''"
    DEF_CF  = " ~- [+] -~ "
    DEF_OF  = " ~- [+] -~ "

    enable_split = True

    # args
    arg_pages            = _param_get(params, 'Pages'               , DEF_P)

    arg_link_fmt         = _param_get(params, 'LinkFormat'          , DEF_L)
    arg_link_hi_fmt      = _param_get(params, 'LinkHighlightFormat' , DEF_LHI)

    arg_collapse         = _param_get(params, 'Collapse'            , 0)
    arg_collapsed_fmt    = _param_get(params, 'CollapsedFormat'     , DEF_CF)
    arg_opened_fmt       = _param_get(params, 'OpenedFormat'        , DEF_OF)

    arg_max_path_depth   = _param_get(params, 'PageMaxDepth'        , 0)
    arg_min_path_depth   = _param_get(params, 'PageMinDepth'        , 0)
    arg_page_strip_level = _param_get(params, 'PageStripLevel'      , 1)
    
    arg_max_head_depth   = _param_get(params, 'HeadingMaxDepth'     , 0)
    arg_min_head_depth   = _param_get(params, 'HeadingMinDepth'     , 0)

    arg_enable_heads     = _param_get(params, 'HeadingsEnabled'     , 1)
    arg_display_heads    = _param_get(params, 'HeadingsDisplay'     , 1)

    arg_display_counts_f = _param_get(params, 'CountsDisplayFormat' , None)
    arg_display_pages_as = _param_get(params, 'PageDisplayAs'       , 'h')
    arg_page_offset      = _param_get(params, 'PageOffset'          , 1)
    arg_page_disp_level  = _param_get(params, 'PageDisplayLevel'    , 0)
    arg_page_list_format = _param_get(params, 'PageListFormat'      , ' 1. %s')
    arg_structured       = _param_get(params, 'PageListStructured'  , 0)

    arg_page_summary_rx  = _param_get(params, 'PageSummaryRx'       , None)

    arg_page_summary_aslink= _param_get(params, 'PageSummaryAsLink' , 0)

    arg_page_summary_fmt = _param_get(params, 'PageSummaryFormat'   , DEF_PSF)
    arg_head_summary_rx  = _param_get(params, 'HeadingSummaryRx'    , None)
    arg_head_summary_fmt = _param_get(params, 'HeadingSummaryFormat', DEF_PSF)

    tmp                  = _param_get(params, 'SummaryRx'           , None)
    if tmp: arg_page_summary_rx = arg_head_summary_rx = tmp

    tmp                  = _param_get(params, 'Summary'             , None)
    if tmp: arg_page_summary_rx = arg_head_summary_rx = get_rx(tmp)

    tmp                  = _param_get(params, 'PageSummary'         , None)
    if tmp: arg_page_summary_rx = get_rx(tmp)

    tmp                  = _param_get(params, 'HeadingSummary'      , None)
    if tmp: arg_head_summary_rx = get_rx(tmp)

    arg_pages_order      = _param_get(params, 'PagesOrder'          , None)
    arg_pages_order_dbg  = _param_get(params, 'PagesOrderDebug'     , 0)
    arg_pages_reverse    = _param_get(params, 'PagesReverse'        , 0)

    arg_format           = _param_get(params, 'Format'              , '%s')
    arg_nolink           = _param_get(params, 'PageListNoLink'      , 0)

    opt_help             = _param_get(params, 'Help'                , 0)
    opt_debug            = _param_get(params, 'Debug'               , 0)

    # Shorthands
    tmp                  = _param_get(params, 'DoListPages'         , 0)
    if tmp:
        arg_display_pages_as = 'l'
        arg_enable_heads = 0
        arg_page_list_format = " * %s"
        enable_split = False
    tmp                  = _param_get(params, 'DoSiteNavigation'    , 0)
    if tmp:
        arg_display_pages_as = 'l'
        arg_enable_heads = 0
        arg_display_heads = 0
        arg_structured = 1
        arg_page_list_format = " * %s"
    tmp                  = _param_get(params, 'DoOnePage'           , 0)
    if tmp:
        arg_display_pages_as = 'p'
        arg_enable_heads = 0
        arg_display_heads = 0
        arg_structured = 1
    tmp                  = _param_get(params, 'DoSiteMap'           , 0)
    if tmp:
        arg_display_pages_as = 'HHl'
        arg_structured = 1
        arg_enable_heads = 0
        arg_display_heads = 0
        #arg_link_fmt = "~- [[%(LINK)s|:]] -~"
        #arg_page_summary_rx = get_rx('italics')
        #arg_page_summary_aslink = 1

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

    # things we'll need
    this_page = macro.formatter.page.page_name

    here_page = macro.request.form.get("here", None)
    if arg_collapse and here_page:
        here_path_part = here_page.split('/')[0:arg_collapse]
    else:
        here_path_part = None
        
    if arg_page_summary_rx:
        page_summary_rx = _re_compile(arg_page_summary_rx, 'PageSummaryRx')
    if arg_head_summary_rx:
        head_summary_rx = _re_compile(arg_head_summary_rx, 'HeadingSummaryRx')

    # empty page means this page; subpage are also handled
    if len(arg_pages) == 0 or arg_pages.startswith('/'):
        arg_pages = this_page + arg_pages
        hits = [arg_pages]

    # get a list of pages matching the PageRegex
    else:
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

            depth = page.count("/") + 1
            if arg_max_path_depth and depth > arg_max_path_depth:
                continue
            if arg_min_path_depth and depth < arg_min_path_depth:
                continue

            extra = ""
            if arg_collapse:
                page_path_part = page.split('/')[0:arg_collapse]
                if page_path_part != here_path_part:
                    if depth>arg_collapse:
                        continue # hide link
                if depth==arg_collapse: # mark page if has children
                    for p in all_pages:
                        if p.startswith(page+"/"):
                            if page_path_part != here_path_part:
                                extra = arg_collapsed_fmt
                            else:
                                extra = arg_opened_fmt
                            break

            hits.append((page, extra))

    #
    # Build a list of pages
    #
    if not arg_pages_order:
        hits.sort()
        if arg_pages_reverse: hits.reverse()
    else:
        # build the list of (regex, rank) pairs, one for each
        # PagesOrder term
        order = []
        rank = 0
        unassigned_rank = None

        # arg_pages_order may either be a list or a page name
        if isinstance(arg_pages_order, basestring):
            body = Page(macro.request, arg_pages_order).get_raw_body()
            lines = body.split("\n")
            lines = [l.strip() for l in lines]
            lines = [l[1:] for l in lines if l.startswith("*")]
            lines = [l.strip() for l in lines]

            #lines = [l.replace('.', r'\.') for l in lines]
            
            arg_pages_order = lines
            
        if arg_pages_reverse: arg_pages_order.reverse()
        display_unassigned_header = True
        for term in arg_pages_order:
            rank += 1
            if term == ".*":
                # do not remember rx, but remember position:
                # unassigned pages will be ordered here
                unassigned_rank = rank
                display_unassigned_header = False
                rank += 1
            else:
                term = "^%s *(Draft|draft|Internal|internal|)$" % term
                rx = _re_compile(term, 'PagesOrder')
                order.append((rx, rank, term))
        unassigned_rank = unassigned_rank or rank + 1
        unassigned_rank += 1 ## leave room for a grouper

        # build the list of (rank, hit) pairs, one for each hit
        ordered_hits = []
        has_unassigned = False
        for hit, extra in hits:
            my_rank = None
            for rx, rank, term in order:
                if rx.search(hit) is not None:
                    my_rank = rank
                    break
            if my_rank and arg_pages_order_dbg: continue
            if not my_rank and not has_unassigned \
                   and display_unassigned_header \
                   and not arg_pages_order_dbg:
                has_unassigned = True
                ordered_hits.append((unassigned_rank-1, "<Unordered>", ""))
            my_rank = my_rank or unassigned_rank
            ordered_hits.append((my_rank, hit, extra))

        # sort and keep only the list of hits
        ordered_hits.sort()
        if arg_pages_reverse: ordered_hits.reverse()
        hits = [each[1:3] for each in ordered_hits]

    #
    # Collect info in pages
    #

    results = []

    for page_name, extra in hits:
        # treat each page ...

        # get the body
        body = Page(macro.request, page_name).get_raw_body()

        # get the page summary
        page_summary = None
        if arg_page_summary_rx:
            txt = _array2str(re.findall(page_summary_rx, body))
            if txt: txt = txt[0]
            page_summary = txt

        #  easier than regex:
        matches = ("\n"+body).split("\n=")
        #  anything ?
        if len(matches) < 2:
            matches = []
        else:
            #  remove 1st part and restore leading '=' of each heading
            matches = ["=" + each for each in matches[1:]]

        heads = []
        if arg_enable_heads:
            # analyze the headings
            min_depth = None
            max_depth = None
            for match in matches:
                # split first line (heading) and others
                first_line, text = (match+"\n").split("\n", 1)
                if not first_line.endswith('='): continue
                text = text.strip('\n')
                # parse first line to get title and depth (number of '=')
                gd = HEAD_RX.search(first_line).groupdict()
                eqs = gd.get('eq', '=')
                head_title = gd.get('title', '<invalid>')
                depth = len(eqs)
                if min_depth is None or depth < min_depth: min_depth = depth
                if max_depth is None or depth > max_depth: max_depth = depth
                # get the heading summary
                head_summary = None
                if arg_head_summary_rx:
                    txt = _array2str(re.findall(head_summary_rx, text))
                    if txt: txt = txt[0]
                    head_summary = txt
                # remember heading
                heads.append([depth, head_title.strip(), head_summary])

            # re-align depth
            for head in heads: head[0] -= min_depth-1
            # filter for depth to be in-range
            def in_range(d):
                return (arg_min_head_depth==0 or d>=arg_min_head_depth) and \
                       (arg_max_head_depth==0 or d<=arg_max_head_depth)
            heads = [head for head in heads if in_range(head[0])]

        # collect all headings and contents
        results.append((page_name, page_summary, heads, extra))


    #
    # Wants counts only
    #
    if arg_display_counts_f:
        np = len(results)
        nh = sum([len(heads) for name, summary, heads, extra in results])
        dico = {
            "PAGES" : np,
            "HEADINGS" : nh,
            }

        text = arg_display_counts_f % dico
        html = text ##_format(text, macro.request, macro.formatter)

        return html


    if len(hits) == 0:
        ##raise _Error("no page matching '%s'!" % arg_pages)
        return ""

    #
    # Get the level shift
    #
    start_neg_offset = 0
    if arg_page_strip_level:
        for page_name, page_summary, heads, extra in results:
            l = len(page_name.split("/")) -1
            if start_neg_offset == 0 or l<start_neg_offset:
                start_neg_offset = l

    #
    # Output the results
    #
    wiki_text = ""
    wiki_text_prefix = []

    last_page_path = []
        
    for page_name, page_summary, heads, extra in results:
        level = len(page_name.split("/")) - arg_page_disp_level
        page_display_name = page_name
        page_path = page_name.split('/')[start_neg_offset:]

        if arg_page_disp_level:
            l = page_display_name.split('/')[arg_page_disp_level:]
            page_display_name = '/'.join(l)

        dico = {
            'SUMMARY': (page_summary or "").rstrip(),
            'LINK'   : page_name,
            'DISPLAY': split_title(page_name, enable_split)
            }

        if level >= len(arg_display_pages_as):
            display_pages_as = arg_display_pages_as[-1]
        else:
            display_pages_as = arg_display_pages_as[level]

        if display_pages_as == "h" or display_pages_as == "H":
            # look how this page and last page are common
            ix = 0
            for i in range(min(len(last_page_path), len(page_path))):
                if last_page_path[i] == page_path[i]: ix +=1
                else: break
            shortened_name = '/'.join(page_path[ix:])

            # generate heading for page name
            eq = "=" * (1+ix+arg_page_offset)
            wiki_text += (eq+" %s "+eq+"\n") % split_title(shortened_name, True)

            # page summary
            wiki_text += (arg_page_summary_fmt % dico).strip() + extra  + "\n"

            # page link
            if (display_pages_as == "h" and not arg_nolink):
                fmt = arg_link_fmt + "\n"
                wiki_text += fmt % dico + extra

        elif display_pages_as == "p":
            if not page_name.lower().endswith("draft"):
                body = Page(macro.request, page_name).get_raw_body()
                levels = page_name.split("/")[start_neg_offset:]
                h = "=" * len(levels)

                # schedule a prefix
                pf = "<<TableOfContents(5)>>"
                if not pf in wiki_text_prefix:
                    wiki_text_prefix.append(pf)
                
                # adjust attachments
                def replacer(m):
                    s = m.group(0)
                    return s[:13] + page_name + "/" + s[13:]
                rx = re.compile("\{\{attachment:[^/}]+?}}")
                body = rx.sub(replacer, body)
                rx = re.compile("\[\[attachment:[^/}]+?]]")
                body = rx.sub(replacer, body)
    
                # adjust headings
                rx = re.compile("^(=.*=) *$", re.M)
                body = rx.sub(h + r'\1' + h, body)
    
                # remove TOCs
                rx = re.compile("<<TableOfContents.*?>>")
                body = rx.sub("", body)
    
                # remove comments
                body = body.split("\n")
                body = [ l for l in body if not l.startswith("#") ]
                body = "\n".join(body)
    
                # add this page
                wiki_text += "<<BR>>" * 2 + "\n"
                #wiki_text += "----------\n"
                #wiki_text += "''(Page [[%s|%s]])''\n" % (page_name, page_name)
                #wiki_text += "<<BR>>" * 3 + "\n"
    
                ttl = split_title(levels[-1], True)
                wiki_text += "%s [%s] %s\n" % (h, ttl, h)
                wiki_text += body

        elif display_pages_as == "l":
            # insert missing levels as non-clickable items
            for i in range(len(page_path)-1):
                if i<len(last_page_path) and page_path[i]==last_page_path[i]:
                    continue
                wiki_text += " " * (i +1)
                wiki_text += arg_page_list_format % split_title(
                    page_path[i], True)
                wiki_text += "\n"

            # page as list item
            indent = " " * level
            page_list_format = arg_page_list_format

            if arg_nolink:
                link =  page_display_name
            else:
                if ":" in page_name:
                    # there is no wiki markup for page names
                    # containing ":", so we'll go via an external link
                    scriptname = macro.request.getScriptname()
                    url = macro.request.getBaseURL() + "/" + \
                          page_name.replace(" ", "_")
                    link = arg_link_fmt % {
                        'LINK'   : url,
                        'DISPLAY': split_title(page_display_name,
                                               enable_split),
                        }
                else:
                    if arg_structured:
                        parts = page_name.split("/")
                        page_display_name = parts[-1]
                        link = DEF_L % {
                            'LINK'   : page_name,
                            'DISPLAY': split_title(page_display_name,
                                                   enable_split),
                            }

                    # regular page name
                    else:
                        link =  arg_link_fmt % {
                            'LINK'   : page_name,
                            'DISPLAY': split_title(page_display_name,
                                                   enable_split),
                            }
            # page summary
            summary = (arg_page_summary_fmt % dico).strip()
            summary = [line for line in summary.split('\n') \
                       if not line.startswith("#") and line.strip()]

            if len(summary):
                summary_text = (indent + '\n').join(summary)
            else:
                summary_text = ""


            # highlight here-page
            if page_name == here_page:
                link = arg_link_hi_fmt % link

            link += extra

            # output link/summary
            if arg_page_summary_aslink and summary_text:
                summary_text = summary_text.replace("\n", " ") \
                               .strip() \
                               .strip("'")
                wiki_text += indent
                wiki_text += page_list_format % ("[[%s|%s]]" % (page_name, summary_text))
            else:
                wiki_text += indent + page_list_format % link
                if len(summary_text):
                    wiki_text += " <<BR>>" + summary_text + "\n"

            wiki_text += "\n"

        if arg_display_heads:
            # headings
            anchors = []
            for depth, head_title, head_summary in heads:
                # generate anchor
                s = page_name + head_title
                s = s. encode(config.charset)
                anchor = "#head-" + sha.new(s).hexdigest()
                # store anchor to count similar ones
                anchors.append(anchor)
                n = anchors.count(anchor)
                # add index if needed
                if n>1:
                    unique_anchor = anchor + "-%d" % n
                else:
                    unique_anchor = anchor
                # link
                l = page_name + unique_anchor
                if arg_nolink:
                    link = split_title(head_title)
                else:
                    link = arg_link_fmt % {
                        'LINK'   : l,
                        'DISPLAY': split_title(head_title, enable_split),
                        }
                wiki_text += " "*2*(depth-1+1) + " 1. " + link + extra + "\n"
                # summary
                wiki_text += " "*2*(depth+1) + arg_head_summary_fmt % {
                    'SUMMARY': (head_summary or "").rstrip() } + "\n"

        # ready for next page
        last_page_path = page_path

    # ready to output
    if wiki_text.strip():
        wiki_text = arg_format % wiki_text
    if wiki_text_prefix:
        wiki_text = "\n".join(wiki_text_prefix) + "\n" + wiki_text

    html = ""
    # debug
    if opt_debug:
        html += "<pre>%s</pre>\n" % wiki_text.replace("&", "&amp;").replace("<", "&lt;")

    # convert wiki text to html
    html += "\n%s\n" % _format(wiki_text, macro.request)

    return debug_html + html

# end
