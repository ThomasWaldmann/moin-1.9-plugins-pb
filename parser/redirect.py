#format python
"""
MoinMoin plugin: 'redirect' parser.

Define permalinks and flexible redirections: this parser redirects
(using Javascript) according to query terms encoded in the URL, and
rules defined in the parser's page body.

$Revision: 184 $
$Id: redirect.py 184 2009-11-23 19:12:15Z pascal $

-------------------------------------------------------------------------------

Copyright (C) 2008-2009  Pascal Bauermeister <pascal.bauermeister@gmail.com>

This module is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

-------------------------------------------------------------------------------

Usage:
{{{#!redirect

NAME=PATTERN, ... : LINK
...
}}}

Where:
* 

-------------------------------------------------------------------------------

ChangeLog:

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-09
  * Compatibility for MoinMoin 1.7 and above

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2008/12/19:
  * Initial version
"""

# Parser's name
NAME = __name__.split(".")[-1]

Dependencies = ["time"] # never cached

import re
from MoinMoin.Page import Page
from MoinMoin import wikiutil

html_template = """
<p>
You should be redirected shortly.  If your browser does not
redirect you please click <a href="%(url)s">here</a>.
</p>

<script language="javascript">
<!--
try {
  document.location.replace("%(url)s");
} catch(e) {
try {
  window.location = "%(url)s";
} catch(e) {
  location.href = "%(url)s";
}}
//-->
</script>
"""

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

class Parser:

    def __init__(self, raw, request, **kw):
        # save call arguments for later use in format()
        self.raw = raw
        self.request = request

    def _usage(self, full = False):
        """Returns the interesting part of the module's doc"""

        if full:
            return __doc__
        else:
            rx = re.compile("--$(.*?)^--", re.DOTALL + re.MULTILINE)
            return rx.findall(__doc__)[0].strip()

    def format(self, formatter):
        """The parser's entry point"""

        text = self.raw

        # parse bangpath for arguments
        opt_dbg  = False
        opt_help = 0
        self.attrs = {}

        for (key, val) in self.attrs.items():
            val = val[1:-1]
            if False: pass
            elif key == 'debug': opt_dbg  = int(val)
            elif key == 'help':  opt_help = int(val)
            else:
                self.request.write(formatter.rawHTML("""
                <p><strong class="error">
                Error: parser '%s': invalid argument: %s
                <pre>%s</pre></strong> </p>
                """ % (NAME, str(key), self._usage())))
                return

        # help ?
        if opt_help:
            self.request.write(formatter.rawHTML("""
            <p>
            Parser '%s' usage:
            <pre>%s</pre></p>
            """ % (NAME, self._usage(opt_help))))
            return

        # split and remove comments
        lines = [l.strip() for l in text.split('\n')]
        lines = [l for l in lines if l and not l.startswith("#")]

        form = self.request.values  # we need stuff from querystring (values has qs + posted form data)
        rules = []

        # go
        for line in lines:
            if opt_dbg: print line, "<br>"
            factors, wikilink = line.split(":", 1)

            factors = [ r.strip() for r in factors.split(",") ]
            unmatched = False

            link = _format(wikilink, self.request)
            rx = re.compile('href="(.*)"', re.I|re.MULTILINE)
            url = rx.search(link).groups()[0]
            
            rules.append( (factors, wikilink, link, url) )
            if opt_dbg: print "- factors:", factors, "<br>"
            for factor in factors:
                name, value = [ i.strip() for i in factor.split("=") ]
                if opt_dbg: print "-- checking", name, value, "<br>"
                if form.has_key(name):
                    if opt_dbg: print "-- key ok <br>"
                    value = re.escape(value).replace(r'\*', '.*')
                    value = '^%s$' % value
                    rx = re.compile(value)
                    if not rx.match(form[name]):
                        unmatched = True
                        break
                else:
                    unmatched = True
                    break

            # OK, it matches these factors
            if not unmatched:
                if opt_dbg: print "YES<br>"

                # At this point,it's too late to emit HTTP headers, as
                # we have already started the page construction
                ## self.request.http_redirect('%s' % url)

                # So we can only emit some javascript:
                html = html_template % { 'url': url, 'link': link }
                self.request.write(formatter.rawHTML(html))
                return

        # nothing found
        wiki = ["No redirection defined for this URL query."]        
        if True or opt_dbg:
            wiki.append("Possible redirections are:")
            wiki.append(
                '||<rowbgcolor="lightgray"> URL query (wildcard pattern char is \'*\') || Links to ||')
            for factors, wikilink, link, url in rules:
                wiki.append("|| `%s` || %s ||" % ("?" + "&".join(factors), wikilink) )
                
        html = _format("\n".join(wiki), self.request)
        self.request.write(formatter.rawHTML(html))
            
#end

