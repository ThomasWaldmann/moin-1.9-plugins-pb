# -*- coding: iso-8859-1 -*-

"""
    Raw HTML Macro

    Originally by Christian Bird <chris.bird@lineo.com>
    Modified by Adam Shand <adam@personaltelco.net> on 14 April 2003
    Now allows arbitrary HTML if the page is immutable.

    Much thanks to Thomas and Jürgen for all the help.

    Usage: [[HTML(<b>This is HTML.</b>)]]
"""

import cgi

def execute(macro, args):
    _ = macro.request.getText
    page = macro.formatter.page

    if 0 and page.isWritable():
        ret = '<p><strong class="error">%s</strong></p>' % _('Raw HTML not returned because page is writable.')
        ret += cgi.escape(args)
    else:
        ret = "\n<!-- Begin HTML.py Output -->\n %s \n<!-- End HTML.py Output -->\n" % args

    return macro.formatter.rawHTML(ret)
