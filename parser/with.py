#format python
"""
MoinMoin plugin: 'with' parser.

Preprocessor providing #define macros, like in the C language. Another
wiki page can be used as macro definition library.

The goal is to help keep wiki text simple, by defining enclosing
overhead once in a separate page (called 'resource'), and using it as
much as wanted. The resource can be used to hold the overhead and the
macro definitions.

This is a rewrite of the 'using' parser, this time using the external
program 'gpp' as preprocessoer, instead of python regex-based code.

$Revision: 184 $
$Id: with.py 184 2009-11-23 19:12:15Z pascal $

-------------------------------------------------------------------------------

Copyright (C) 2008-2009  Pascal Bauermeister <pascal.bauermeister@gmail.com>

This module is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

-------------------------------------------------------------------------------

Usage:
{{{#!using RESOURCE_PAGE[#SECTION] [OPTIONS]
BODY
}}}

OPTIONS:
  debug=0|1|2|3|4  (default 0)
    1: the raw text after gpp and before wiki formatting is shown before.
    2 and above: in addition, the implicite #defines are shown before.
    3: the raw text with resource merged is shown before.
    4: the raw text before gpp is shown before.

  raw=0|1|2
    1: the raw text passed to the parser is shown after.
    2: the complete parser block with delimiters and bang path is shown after.
    
  show=0|1   (default 1)
    if 0, does not show the formatted output.
    
  help=0|1   (default 0)
    if 1, dispays this help.

  define_KEYWORD=VALUE
    will produce #define KEYWORD VALUE


Notes:

  - All these options can be also passed in the URL, like in this
    example: ?define_NOW=Never?action=print&help=1

  - These macros are automatically generated like this:
    #define __PAGE__          MyPage
    #define __DATETIME__      Thu May  8 20:48:06 2008
    #define __DATE__          2008-05-08
    #define __TIME__          20:48:06
    #define __USER__          PascalBauermeister
    #define __ACTION__        show
    #define __WIKI__          MoinMoin
    #define __WIKI_VERSION__  1.5.2
    #define __WIKI_REVISION__ release

  - The macros are inserted in this order:
    1. automatically generated macros (__PAGE__ and the like)
    2. command-line macros (in no particular order)
    3. URL macros (in no particular order)


The parser does the following:

1. Prepends some wiki text before, and appends some wiki text
   after the BODY. This is done as follows:
 
   With a RESOURCE_PAGE containing:
     BODY-BEFORE
     #yield
     BODY-AFTER
 
   the parser will produce text as if the following was written:
     BODY-BEFORE
     BODY
     BODY-AFTER
 
   In addition, RESOURCE_PAGE may contain multiple resources sections:
     {{{ r1
       ...
     #yield
       ...
     }}}
     {{{ r2
       ...
     #yield
       ...
     }}}
   then the using page would specify this:
     {{{#!using MyResourcePage#r2
     ...
     }}}
   to to use the r2 resource.
 
2. The result gets unescaped as follows:

   - backslash + letter => letter  (where letter is not backslash nor space)
   - 2 x backslash => backslash
  
   allowing for example to write '{\{\{' in order to get '{{{', to insert
   a nested processor/parser block.

3. The resulting text is processed a bit similarly to a C
   preprocessor does it with '#define':
 
     #define MYSYMBOL         my value
     #define MYFUNCTION(x,y)  || x || y ||
 
4. The result gets formatted from wiki text to HTML.


Examples of use:
  TBD

-------------------------------------------------------------------------------

ChangeLog:

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-09
  * Compatibility for MoinMoin 1.7 and above
 
Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2008-05-08:
  * supports parameters (and defines) via cmdline and URL.
Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2008-03-19:
  * re-written using gpp.
Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2007-09-14:
  * Improved wiki_text -> html formatter.

"""


# Parser's name
NAME = __name__.split(".")[-1]

Dependencies = ["pages"]

import os, re, sha
import StringIO, string
from MoinMoin.action import AttachFile
from MoinMoin.Page import Page
from MoinMoin import wikiutil, config

DATA_RE = re.compile(r"^#data.*?^#end *$", re.M+re.S)

###############################################################################

def escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

###############################################################################

class GppError(Exception):
    pass

###############################################################################

def errStr(text, errn, errmsg):
    errl = (text+"\n").split("\n")[errn-2]
    text = text.encode('ascii', 'replace')
    lines = text.split("\n")
    for i in range(len(lines)):
        lines[i] = u"%4.0d: %s" % (i+1, lines[i])
    lines.insert(errn-1, "\n--------> %s\n"%errmsg.strip())

    return u"%s : %s\n\n%s" % (
        errl,
        errmsg,
        "\n".join(lines)
        )


###############################################################################

from MoinMoin import wikiutil
def _format (src_text, request):
    """Parse the text (in wiki source format) and make HTML, after
    diverting sys.stdout to a string"""
    
    Parser = wikiutil.searchAndImportPlugin(request.cfg,
                                            "parser",
                                            request.page.pi['format'])
    return wikiutil.renderText(request, Parser, src_text)

###############################################################################

import re
from subprocess import Popen, PIPE
import StringIO

#GPP = [ r'gpp --nostdinc --nocurinc +c "/*" "*/" +c "//" "\n" +c "\\\n" ""' ]
GPP = [ 'gpp', '--nostdinc', '--nocurinc' ]

class Preprocessor:

    def __init__(self, text, def_defines):
        def_defines = ["#define "+i for i in def_defines]
        def_defines = u"\n".join(def_defines)
        self.text = u"%s\n%s\n" % (def_defines.strip(), text.strip())
    

    def get_result(self):
        cmd = GPP
        try:
            p = Popen(cmd, shell=False, bufsize=0,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except OSError:
            raise RuntimeError(
                "Error executing command " \
                    "(maybe '%s' is not installed on the system?) : %s" % (
                    os.path.split(cmd[0])[-1], ' '.join(cmd)))

        stdout, stderr = p.communicate(self.text.encode("utf-8"))
        stdout = unicode(stdout, "utf-8")
        stderr = unicode(stderr, "utf-8")

        if stderr:
            errn = int(stderr.split(":")[1])
            errmsg = stderr.split(":", 2)[2]
            raise GppError(errStr(self.text, errn, errmsg))
        return stdout


###############################################################################

class Parser:

    extensions = ['.using']

    def __init__(self, raw, request, **kw):
        # save call arguments for later use in format()
        self.raw = raw.encode('utf-8')
        self.request = request
        args = kw.get('format_args', '').split()
        self.resource = args[0]
        args = ' '.join(args[1:])
        self.attrs, msg = wikiutil.parseAttributes(request, args)


    def _usage(self, full = False):

        """Returns the interesting part of the module's doc"""

        if full:
            return __doc__
        else:
            rx = re.compile("--$(.*?)^--", re.DOTALL + re.MULTILINE)
            return rx.findall(__doc__)[0].strip()


    def _get_include(self, page, ident, this_page):

        """Return the content of the given page; if ident is not empty,
        extract the content of an enclosed section:
        {{{ NAME
          ...content...
        }}}
        """

        body = self._get_page_body(page, this_page)

        if not ident: return body

        rx = re.compile("{{{  *%s *\n(.*?)}}}" % ident,
                         re.DOTALL + re.MULTILINE)
        matches = rx.findall(body)
        if len(matches)==0:
            raise GppError("Page '%s' contains no resource named %s" %
                              (page, ident))
        return matches[0].rstrip()


    def _get_page_body(self, page, this_page):

        """Return the content of a named page; accepts relative pages"""

        if page.startswith("/") or len(page)==0:
            page = this_page + page

        p = Page(self.request, page)
        if not p.exists():
            raise GppError("Page '%s' not found" % page)
        else:
            body = p.get_raw_body()
            return body


    def format(self, formatter):
        """The parser's entry point"""
        try:
            return self.do_format(formatter)
        except GppError, msg:
            self.request.write(formatter.rawHTML("""
            <p><strong class="error">
            Error: parser '%s': %s</strong> </p>
            """ % (
                NAME,
                msg.args[0].replace("\n", "<br>").replace(" ", "&nbsp;")
                )))
            return

    def do_format(self, formatter):
        
        text0 = unicode(self.raw, 'utf-8')
        text = text0

        # append some HTTP form items to cmdline arguments
        form = self.request.form
        form["action"] = form.get("action", ["show"])
        for (key, val) in form.items():
            if key.startswith("define_") or \
                   key in ("show","debug","help"):
                self.attrs[key] = '"%s"' % val[0]
            elif key == "action":
                self.attrs["define___ACTION__"] = '"%s"' % val[0]

        # parse bangpath for arguments
        opt_show = 1
        opt_dbg  = 0
        opt_raw  = 0
        opt_help = None

        for (key, val) in self.attrs.items():
            val = val[1:-1]
            if   key == 'show':  opt_show = int(val)
            elif key == 'debug': opt_dbg  = int(val)
            elif key == 'raw':   opt_raw  = int(val)
            elif key == 'help':  opt_help = val
            elif key.startswith("define_"): pass
            else:
                raise GppError("""invalid argument: %s
                <pre>%s</pre>""" % (str(key), self._usage()))

        # help ?
        if opt_help is not None and opt_help != '0':
            self.request.write(formatter.rawHTML("""
            <p>
            Parser '%s' usage:
            <pre>%s</pre></p>
            """ % (NAME, self._usage(True))))
            return

        # don't show ?
        if not opt_show: return
        
        # useful
        this_page = formatter.page.page_name

        # get the resource section or page
        if self.resource == "-":
            resource = ""
        else:
            x = (self.resource+"#").split("#")
            page, ident = x[0], x[1]
            resource = self._get_include(page, ident, this_page)

            # remove lines starting with #format
            lines = resource.split("\n")
            lines = [l for l in lines if not l.lower().startswith("#format")]
            resource = u"\n".join(lines)

        # insert the text into the resource
        if resource.find("\n#yield\n") > -1:
            text = resource.replace("\n#yield\n", text)
        else:
            text = resource + "\n%s"%text
        text1 = text

        # extract blocks (using re w/ re.M + re.S) in the form:
        # #data NAME
        # ... block
        # #end
        matches = [] # data matches
        frags = []   # data fragments to remove
        for match in DATA_RE.finditer(text):
            lineno = len(text[:match.start()].split("\n"))+1
            matches.append((text[match.start():match.end()], lineno))
            frags.insert(0, match)
        for match in frags:
            text = text[:match.start()] + text[match.end()+1:]

        # TODO:
        # convert blocks to YAML
        for match, lineno in matches:
            lines = match.split("\n")
            data = "\n".join(lines[1:-1])
            try:
                name = lines[0].split(" ")[1]
            except IndexError:
                raise GppError(
                    errStr(text1,
                           lineno,
                           "Data declaration must of form #data NAME"
                           )
                    )
            print "<br>%s: {%s}" % (name, data.replace('\n','\\n'))

        # insert them at end or at
        # #expand DATA
        # in declarative (#define NAME_PARENTKEY_..._KEY VALUE)
        # or imperative (#define NAME_LEVELN(KEY) VALUE)

        # remove lines beginning by '##'
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("##")]
        
        # stick lines ending with a single '\', except in #define clauses
        in_define = False
        new_lines = []
        for line in lines:
            sline = line.strip()
            back_end  = sline.endswith("\\")
            def_start = sline.startswith("#define")
            if def_start: in_define = True
            if not back_end: in_define = False

            if back_end and not in_define:
                new_lines.append(line.rstrip()[:-1])
            else:
                new_lines.append(line+"\n")
        text = u"".join(new_lines)
                
        # remove lines beginning by '##'
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("##")]
        text = u'\n'.join(lines)
        text2 = text
        
        # default definitions
        import time
        from MoinMoin.version import project, release, revision
        def_def = [
            "__PAGE__          " + this_page,
            "__DATETIME__      " + time.strftime("%c"),
            "__DATE__          " + time.strftime("%F"),
            "__TIME__          " + time.strftime("%T"),
            "__USER__          " + self.request.user.name,
            "__WIKI__          " + project,
            "__WIKI_VERSION__  " + release,
            "__WIKI_REVISION__ " + revision,
        ]

        # add definitions for form params such as define_vame="value"
        for (key, val) in self.attrs.items():
            if key.startswith("define_"):
                def_def.append(key[7:] + " " + val[1:-1])

        # process #define statements
        p = Preprocessor(text, def_def)

        try:
            text = p.get_result()
        except GppError, msg:
            msg = msg.__str__()
            msg = u"%s" % unicode(msg, "utf-8")
            msg = escape(msg)
            raise GppError("Gpp error<br>%s" % msg)

        # debug
        if opt_dbg:
            tt = text
            html = u"<pre>"
            if opt_dbg >=2:
                def_defines = ["#define "+i for i in def_def]
                def_defines = "\n".join(def_defines)
                html += u"<i>%s</i>\n" % escape(def_defines)
            if opt_dbg==3:
                tt = text1
            elif opt_dbg==4:
                tt = text2
            html += u"%s</pre>\n" % escape(tt)
            self.request.write(formatter.rawHTML(html))

        # convert wiki text to html
        html = _format(text, self.request)        
        self.request.write(formatter.rawHTML(html))

        # raw
        if opt_raw==1:
            html = u"<pre>%s</pre>\n" % escape(text0)
            self.request.write(formatter.rawHTML(html))
        elif opt_raw==2:
            html = u"<pre>{{{#!with %s %s\n%s\n}}}</pre>\n" % (
                self.resource,
                " ".join(["%s=%s" % (k,v) for k,v in self.attrs.items()
                          if k!="raw" and not k.startswith("define__")]),
                escape(text0)
                )
            self.request.write(formatter.rawHTML(html))


#end
