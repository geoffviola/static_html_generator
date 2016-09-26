#!/usr/bin/env python

import re
import bs4
import _collections_abc
from bs4 import BeautifulSoup


def my_decode(self, indent_level=None,
              eventual_encoding=bs4.DEFAULT_OUTPUT_ENCODING,
              formatter="minimal", preserve_newlines=False, whitespace_left=True, whitespace_right=True):
    """Returns a Unicode representation of this tag and its contents.

    :param eventual_encoding: The tag is destined to be
           encoded into this encoding. This method is _not_
           responsible for performing that encoding. This information
           is passed in so that it can be substituted in if the
           document contains a <META> tag that mentions the document's
           encoding.
    """

    # First off, turn a string formatter into a function. This
    # will stop the lookup from happening over and over again.
    if not isinstance(formatter, _collections_abc.Callable):
        formatter = self._formatter_for_name(formatter)

    attrs = []
    if self.attrs:
        for key, val in sorted(self.attrs.items()):
            if val is None:
                decoded = key
            else:
                if isinstance(val, list) or isinstance(val, tuple):
                    val = ' '.join(val)
                elif not isinstance(val, str):
                    val = str(val)
                elif (
                            isinstance(val, bs4.element.AttributeValueWithCharsetSubstitution)
                        and eventual_encoding is not None):
                    val = val.encode(eventual_encoding)

                text = self.format_string(val, formatter)
                decoded = (
                    str(key) + '='
                    + bs4.element.EntitySubstitution.quoted_attribute_value(text))
            attrs.append(decoded)
    close = ''
    closeTag = ''

    prefix = ''
    if self.prefix:
        prefix = self.prefix + ":"

    if self.is_empty_element:
        close = '/'
    else:
        closeTag = '</%s%s>' % (prefix, self.name)

    pretty_print = self._should_pretty_print(indent_level)
    space = ''
    indent_space = ''
    if indent_level is not None:
        indent_space = (' ' * (indent_level - 1))
    if pretty_print:
        space = indent_space
        indent_contents = indent_level + 1
    else:
        indent_contents = None
    current_preserve_newlines = preserve_newlines or self.name == "p" or self.name == "a"
    contents = self.decode_contents(
        indent_contents, eventual_encoding, formatter, current_preserve_newlines, whitespace_left, whitespace_right)

    if self.hidden:
        # This is the 'document root' object.
        s = contents
    else:
        s = []
        attribute_string = ''
        if attrs:
            attribute_string = ' ' + ' '.join(attrs)
        if indent_level is not None and not preserve_newlines or (preserve_newlines and whitespace_left):
            # Even if this particular tag is not pretty-printed,
            # we should indent up to the start of the tag.
            s.append(indent_space)
        s.append('<%s%s%s%s>' % (
            prefix, self.name, attribute_string, close))
        if pretty_print and (
                        (preserve_newlines != current_preserve_newlines and (
                                    not any(isinstance(x, bs4.Tag) for x in self) or (
                                            any(isinstance(x, bs4.Tag) for x in self) and any(
                                                x.find("\n") != -1 for x in
                                                self.contents)))) or not current_preserve_newlines or (
                            current_preserve_newlines and (any(x.find("\n") != -1 for x in self.contents) or (
                                    whitespace_left and len(contents) > 0)))):
            # if pretty_print and not current_preserve_newlines:
            s.append("\n")
        s.append(contents)
        if pretty_print and contents and contents[-1] != "\n" and (
                    not current_preserve_newlines or "a" != self.name and current_preserve_newlines and current_preserve_newlines != preserve_newlines):
            s.append("\n")
        if pretty_print and closeTag and (not preserve_newlines and "a" != self.name):
            s.append(space)
        s.append(closeTag)
        if indent_level is not None and closeTag and self.next_sibling and (
            not preserve_newlines or preserve_newlines and whitespace_right):
            # Even if this particular tag is not pretty-printed,
            # we're now done with the tag, and we should add a
            # newline if appropriate.
            s.append("\n")
        s = ''.join(s)
    return s


bs4.Tag.decode = my_decode


def list_ends_with_newline(list):
    return len(list) > 0 and isinstance(list[-1], str) and list[-1].find("\n") != -1


def my_decode_contents(self, indent_level=None,
                       eventual_encoding=bs4.DEFAULT_OUTPUT_ENCODING,
                       formatter="minimal", preserve_newlines=False, whitespace_left=True, whitespace_right=True):
    """Renders the contents of this tag as a Unicode string.

    :param indent_level: Each line of the rendering will be
       indented this many spaces.

    :param eventual_encoding: The tag is destined to be
       encoded into this encoding. This method is _not_
       responsible for performing that encoding. This information
       is passed in so that it can be substituted in if the
       document contains a <META> tag that mentions the document's
       encoding.

    :param formatter: The output formatter responsible for converting
       entities to Unicode characters.
    """
    # First off, turn a string formatter into a function. This
    # will stop the lookup from happening over and over again.
    if not isinstance(formatter, _collections_abc.Callable):
        formatter = self._formatter_for_name(formatter)

    pretty_print = (indent_level is not None)
    s = []
    non_whitespace_pattern = re.compile('\S')
    for i in range(len(self.contents)):
        c = self.contents[i]
        text = None
        if isinstance(c, bs4.NavigableString):
            text = c.output_ready(formatter)
        elif isinstance(c, bs4.Tag):
            next_whitespace_left = whitespace_left
            if i - 1 >= 0:
                prev_c = self.contents[i - 1]
                index_of_last_non_whitespace = non_whitespace_pattern.search(prev_c[::-1])
                if index_of_last_non_whitespace is None:
                    next_whitespace_left = len(prev_c) > 0
                else:
                    next_whitespace_left = index_of_last_non_whitespace.start(0) != 0
            next_whitespace_right = whitespace_right
            if i + 1 < len(self.contents):
                next_c = self.contents[i + 1]
                while isinstance(next_c, bs4.Tag):
                    next_c = next_c.contents[0]
                index_of_first_non_whitespace = non_whitespace_pattern.search(next_c)
                if index_of_first_non_whitespace is None:
                    next_whitespace_right = len(next_c) > 0
                else:
                    next_whitespace_right = index_of_first_non_whitespace.start(0) != 0
            s.append(c.decode(indent_level, eventual_encoding,
                              formatter, preserve_newlines, next_whitespace_left, next_whitespace_right))
        whitespace_at_end = False
        newline_at_beginning = False
        if text and indent_level and not self.name == 'pre':
            if preserve_newlines:
                first_newline = text.find("\n")
                if -1 != first_newline:
                    newline_at_beginning = not non_whitespace_pattern.findall(text, 0, first_newline + 1)
                last_whitespace_match = re.search("\s", text[::-1])
                if last_whitespace_match:
                    last_whitespace_idx = len(text) - last_whitespace_match.start() - 1
                    whitespace_at_end = not non_whitespace_pattern.findall(text, last_whitespace_idx)
            text = text.strip()
            if preserve_newlines:
                # reindent leading whitespace in between a tag
                lw_pattern = re.compile('^( |\t)+(.*)$', re.MULTILINE)
                text = lw_pattern.sub(lambda match_object: " " * (indent_level - 1) + match_object.group(2), text)
        if text:
            if pretty_print and not self.name == 'pre' and (
                        not preserve_newlines or (preserve_newlines and (newline_at_beginning or
                                                                             (0 == i and whitespace_left) or (
                                i > 0 and len(s[-1]) > 0 and '\n' == s[-1][-1])))):
                s.append(" " * (indent_level - 1))
            s.append(text)
            if pretty_print and not self.name == 'pre' and (
                        not preserve_newlines or (preserve_newlines and whitespace_at_end)):
                s.append("\n")
    return ''.join(s)


bs4.Tag.decode_contents = my_decode_contents
