#format python
"""
MoinMoin parser: 'if'.

This parser allows to display blocks conditionally.

-------------------------------------------------------------------------------

Copyright (C) 2005-2008  Pascal Bauermeister <pascal.bauermeister@gmail.com>

This module is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

-------------------------------------------------------------------------------

Usage:
{{{#!if EXPRESSION
   Wiki text block 1 (mandatory)
#elif EXPRESSION
   Wiki text block 2 (optional, can be repeated)
#else
   Wiki text block 3 (optional)
}}}

Where:
* EXPRESSION must be a valid Python expression which may contain:
    user_name
      string giving the current user name, or "" if not logged-in.

    action
      string giving the page's action.

    is_member (group)
      function returning 1 if the user is member of the given group, 0
      otherwise.

  When EXPRESSION is omitted, this help is displayed.

* #elif (or #elsif, or #elseif) is optional

* #else is optional

-------------------------------------------------------------------------------

Sample 1: area restricted to logged-in members

{{{#!if user_name != ""
= Here are some info restricted to logged-in users =
...

#else
= Public infos =
...
}}}

----

Sample 2: area restricted to members of a certain groups

{{{#!if is_member("BlueGroup") or is_member("YellowGroup")
= Green info =
...
}}}

-------------------------------------------------------------------------------

ChangeLog:

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-09
  * Compatibility for MoinMoin 1.7 and above

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2008/05/25:
  * Made the plugin a parser (not a processor); supports MoinMoin 1.6.

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2007/09/14:
  * Improved wiki_text -> html formatter
 
Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2005/12/14:
  * Help added

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2005/02/21:
  * Initial version

"""

# Parser's name
NAME = __name__.split(".")[-1]

Dependencies = ["pages"]

import os, re, sha
import StringIO
from MoinMoin.Page import Page
from MoinMoin import wikiutil
try:
    from MoinMoin.parser import text_moin_wiki as wiki # >= 1.6
except ImportError:
    from MoinMoin.parser import wiki # < 1.6


class _Error (Exception): pass

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

    def _evaluate(self, expr):
        def is_member(group):
            return self.request.dicts.has_member(group, self.request.user.name)

        user_name = self.request.user.name

        if self.request.form.has_key('action'):
            action = self.request.form['action'][0]
        else:
            action = ""

        try:
            val = eval(expr,
                       { '__builtins__': [] },
                       { 'user_name' : user_name,
                         'action'    : action,
                         'is_member' : is_member,
                         'form'      : self.request.form,
                         }
                       )
        except Exception: val = False
        return val


    def _process(self, formatter, lines):
        blocks = []
        command = None

        if len(lines[0].strip()) <= 4:
            raise _Error("<pre>%s</pre>" % _usage())

        # split lines into blocks delimited by "#command [cond]"
        block = []
        for l in lines:
            ll = l.strip()

            iscmd = False
            for each in ("#if", "#elif", "#elsif", "#elseif", "#else"):
                if ll.startswith(each): iscmd = True
            
            if iscmd:
                if command: blocks.append((command, block))
                command, block = ll[1:], []
            else: block.append(l)
        if command:  blocks.append((command, block))

        # treat each block
        for command, block in blocks:

            # split command line into cmd, condition
            parts = command.split(" ", 1)
            parts.append("")
            cmd, cond = parts[0:2]
            cmd = cmd.strip("!")

            doit = False
            if cmd in ("if", "elif", "elsif", "elseif"):
                if self._evaluate(cond): doit = True
            elif cmd == "else":
                if cond: block.insert(0, cond)
                doit = True
            else:
                raise _Error("<pre>Unknown command: %s</pre>" % cmd)

            if doit:
                html = _format("\n".join(block), self.request)
                self.request.write(formatter.rawHTML(html))
                return


    def __init__(self, raw, request, **kw):
        # save call arguments for later use in format()
        self.raw = raw
        self.request = request

        # get args; 1st one is the macro name
        args = kw.get('format_args', '').split()
        self.macro_name = args[0]

        # next args are options
        args = ' '.join(args[1:])
        self.attrs, msg = wikiutil.parseAttributes(request, args)

        self.raw = "#if " + kw.get('format_args', '') + "\n" + self.raw


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
        opt_show = True
        self.attrs = {}

        for (key, val) in self.attrs.items():
            val = val[1:-1]
            if False: pass
            elif key == 'debug': opt_dbg  = int(val)
            elif key == 'help':  opt_help = int(val)
            elif key == 'show':  opt_show = int(val)
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

        # don't show ?
        if not opt_show: return

        # remove comments
        lines = [line for line in text.split('\n')]

        # go
        try:
            self._process(formatter, lines)
        except _Error, str:
            self.request.write(formatter.rawHTML("""
            <p><strong class="error">
            Error: parser %s: %s
            </strong> </p>
            """ % (NAME, str) ))

#end
