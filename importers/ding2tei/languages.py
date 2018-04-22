"""This module contains the language-specific pre- and postprocessors."""

import re

# forgive me, but I actually really need all of them
from dictstructure import AbstractParser, ChunkType, Definition, Form, \
        GramGrp, ParserError, SemNode, Sense, Translation, Unprocessed, Usage

class DeuEngParser(AbstractParser):
    GENDER = ['n', 'm', 'f'] # ontology?
    NUMBER = {'pl': 'pl', 'sing': 'sg', 'no pl': 'no pl'}
    POS = {'adj':'adj', 'adv': 'adv', 'art': 'art', 'conj': 'conj',
            'idiom': 'phrase', 'interj': 'int',
            'n': 'n', 'num': 'num', 'prp': 'prep', 'prep': 'prep',
            'prn': 'pron', 'ppron': 'pron', 'pron': 'pron',
            'v': 'v', 'vi': 'vi', 'vr': 'vr', 'vt': 'vt', 'vti': 'vti'}
    CASE_RGX = re.compile(r"""([A-Z|a-z]\??)?\s* # optional collocate with optional question mark
        \+?\s*(Gen|Dat|Akk|conj)\.? # grammatical case
            /?\s*(.*)$ # optional preposition/collocate
        """, re.VERBOSE)

    def handle_single_token_in_brace(self, outer, text):
        if text in self.GENDER:
            return (GramGrp(pos='n', gender=text),)
        elif text in self.NUMBER:
            return (GramGrp(pos='n', number=self.NUMBER[text]),)
        elif text in self.POS:
            return (GramGrp(pos=self.POS[text]),)
        # ToDo: use subc here
        elif re.search(r'^\w+\s+\+\s+\w+', text):
            pos, subc = [p.strip() for p in text.split('+')]
            return (GramGrp(pos=self.POS[pos], subc=subc))
        elif self.CASE_RGX.search(text):
            g = GramGrp()
            self.handle_case_in_brace(outer, g, text)
            return (g,)
        else:
            raise ParserError('unrecognized token "{%s}"' % text)

    def handle_comma_in_brace(self, text):
        """comma is either for multiple genders, for a gender and a "pl"
        declaration or rarely for different verb forms."""
        g = GramGrp(pos='n') # it's a noun
        for token in (t.strip() for t in text.split(',')):
            if token in self.NUMBER:
                g.number = self.NUMBER[token]
            elif token in self.GENDER:
                g.add_child(GramGrp(gender=token))
            elif token in self.POS:
                g.pos = token
            elif len(token) > 3 and ' ' in token: # usage hint
                g.usg = token
            else:
                raise ParserError("Unknown token in {%s}" % text)
        return (g,)


    def handle_brace(self, node_class, outer, chunk):
        nodes = []
        text = chunk[1].rstrip('. ')
        # semicolon takes precedence over comma and others
        if ';' in text:
            nodes.extend(self.handle_semicolon_in_brace(node_class, outer, text))
        elif ',' in text:
            nodes.extend(self.handle_comma_in_brace(text))
        elif '/' in text: # only seen that for vt/vi
            tokens = text.split('/')
            if all(t.strip() in self.POS for t in tokens):
                nodes.extend(GramGrp(children=\
                    [GramGrp(pos=self.POS[pos.strip()]) for pos in tokens]))
            else:
                print("ToDo: remove me")
                #raise ParserError("Encountered unknown (POS) token {%s}" % repr(chunk))

        else:
            nodes.extend(self.handle_single_token_in_brace(outer, text))
        return nodes

    def handle_semicolon_in_brace(self, node_class, outer, text):
        tokens = [t.strip() for t in text.split(';')]
        if all(t in self.POS for t in tokens):
            return (GramGrp(children=[GramGrp(pos=t) for t in tokens]),)
        elif len(tokens) == 2: # past participle, etc. of a verb
            f = node_class(text=tokens)
            f.add_attr("type", "infl")
            return (f,)
        else:
            # try to find case hints, etc.
            g = GramGrp()
            for token in tokens:
                if token in self.POS:
                    g.pos = token
                    continue

                if self.CASE_RGX.search(token):
                    # note: this method appends to `outer` and *changes* `g`
                    self.handle_case_in_brace(outer, g, token)
                else:
                    raise ParserError("Couldn't recognize expression: {%s}" % text)
            return (g,)

    def handle_case_in_brace(self, outer, g, token):
        match = self.CASE_RGX.search(token).groups()
        outer.add_child(Usage(match[1], attrs={'type': 'gram'}))
        for colloc in (x for x in (match[0], match[2]) if x):
            if colloc in self.POS:
                g.pos = self.POS[colloc] # missing semicolon to POS
            else:
                g.colloc = colloc


    #pylint: disable=too-many-arguments
    def mk_term(self, outer, term, gram=None, new_form=False, attrs=None):
        """Create a translation for sense or add headword to orth."""
        #pylint: disable=redefined-variable-type
        relevant_node = outer
        if isinstance(outer, Form):
            if new_form:
                relevant_node = Form(term)
                outer.add_child(relevant_node)
            else:
                outer.add_text(term)
            if gram:
                relevant_node.add_child(gram)
        else: # handle translations
            relevant_node = Translation(term)
            if gram:
                relevant_node.add_child(gram)
            outer.add_child(relevant_node)
        if attrs: # set attributes
            for k, v in attrs.items():
                relevant_node.add_attr(k, v)
        return relevant_node # optional return to reuse node

    def handle_paren(self, parent, chunks, idx):
        """Check for certain chunk arrangements to discover informal phrase
        abbreviations and other human-intuitive encodings of words and
        parenthesis.
        This function should discover and split such chunk arrangements. It
        returns a tuple containing the new index and a list of nodes to
        attach."""
        # ^v: idx is used to detect whether changes to the outer node have been
        start = idx
        # made
        # helper functions
        isword = lambda i: len(chunks[i]) == 2 and chunks[i][0] == ChunkType.Word
        isparen = lambda i: len(chunks[i]) == 2 and chunks[i][0] == ChunkType.Paren
        enough_chunks_left = lambda num: idx + num < len(chunks)
        # format: "word m/f"; gender info
        if enough_chunks_left(2):
            if isword(idx) and isparen(idx+1) and chunks[idx+1][1] in ('m/f', 'm/f.'):
                gram = GramGrp(gender=['m', 'f'])
                self.mk_term(parent, chunks[idx][1], gram=gram)
                idx += 2
            # format: "term (collocate" and "term (explanation blah blah)"
            elif isword(idx) and isparen(idx+1):
                if ' ' in chunks[idx+1][1] or len(chunks[idx+1][1]) > 3:
                    node = self.mk_term(parent, chunks[idx][1], new_form=True)
                    usg = Usage(chunks[idx+1][1])
                    usg.add_attr('type', "hint")
                    node.add_child(usg)
                else: # it's a collocate
                    node = self.mk_term(parent, chunks[idx][1], new_form=True)
                    node.add_child(GramGrp(colloc=chunks[idx+1][1]))
                idx += 2 # last two chunks have been processed
            elif isparen(idx) and isparen(idx+1):
                parent.add_child(Usage(
                        '%s, %s' % (chunks[idx][1], chunks[idx+1][1])))
                idx += 2
        # format: "foo (bar) baz (explanation)"
        elif enough_chunks_left(4) and isword(idx) and isparen(idx+1) and \
                    isword(idx+2) and isparen(idx+3):
            # add term without chunk[idx+1] and again with it
            self.mk_term(parent, '%s %s' % (chunks[idx][1], chunks[idx+2][1]))
            self.mk_term(parent, '%s %s %s' % (chunks[idx][1], chunks[idx+1][1],
                chunks[idx+2][1]))
            parent.add_child(Definition(chunks[idx+3][1]))
            idx += 4
        if start == idx: # nothing has changed, because nothing matched
            text = []
            while idx < len(chunks) and (isword(idx) or isparen(idx)):
                if isparen(idx):
                    text.append('(%s)' % chunks[idx][1])
                else:
                    text.append(chunks[idx][1])
                idx += 1
            self.mk_term(parent, ' '.join(text))
            return idx
        else:
            return idx

    def handle_unprocessed(self, outer):
        while outer.get_children() and isinstance(outer.get_children()[0],
                Unprocessed):
            # unhandled chunks are in the text attribute
            unprocessed = outer.get_children().pop(0).get_text()
            required_inner = (Form if outer.__class__ == Form else Translation)
            start = 0
            # iterate over chunks with fast-forward option
            while start < len(unprocessed):
                chunk = unprocessed[start]
                if chunk[0] == ChunkType.Brace:
                    try:
                        nodes = self.handle_brace(required_inner, outer, chunk)
                    except ParserError as p:
                        raise ParserError(p.args[0], 'Chunk parsed: %s' % repr(chunk))
                    # ToDo: that should be useless, but not all braces are parsed yet
                    for node in nodes:
                        if isinstance(node, (SemNode)):
                            outer.add_child(node)
                        else:
                            print("ignoring",chunk)
                elif chunk[0] == ChunkType.Bracket:
                    outer.add_child(Usage((chunk[1],)))
                else:
                    newstart = getattr(self, 'handle_' + chunk[0].name.lower())\
                            (outer, unprocessed, start)
                    if newstart:
                        start = newstart -1
                start += 1
        return outer

    def handle_word(self, x, y, z):
        """Delegate word to handle_paren, with which it is deeply
        intertwined."""
        self.handle_paren(x, y, z)

    def handle_slash(self, outer, chunks, index):
        """Handle expressions enclosed in /foo/. The issue is that they might
        contain a abbreviation, a mnemonic, be a parser error like "foo/bar/baz"
        or could be part of a problematic markup."""
        chunk = chunks[index]
        if len(chunk[1]) < 2: # mnemonic or similar, ungroupable
            return

        # check for abbreviations
        counted = 0 # check for upper case first
        for c in chunk[1]:
            if c.isupper():
                counted += 1
            if counted >= 2:
                break

        # abbreviations start with upper case or end with dot
        if counted >= 2 or '.' in chunk[1] or len(chunk[1]) < 5:
            self.mk_term(outer, chunk[1], new_form=True, attrs={"type": "abbr"})
        else: # it must have been a problematic markup
            child = None
            for ch in reversed(outer.get_children()):
                if isinstance(ch, (Form, Translation)):
                    child = ch
                    break
            if child:
                child.get_text()[-1] += ' /%s/' % chunk[1]
            else:
                self.mk_term(outer, '/%s/' % chunk[1])

    def simplify_markup(self, node):
        return node


class SpaDeuParser(DeuEngParser):
    def __init__(self):
        self.POS['Demonstrativpronomen'] = 'pron'

    # handle a few grammatical things differently
    def handle_brace(self, node_class, outer, chunk):
        text = chunk[1].rstrip().rstrip('.')
        if text == 'mf' or text == 'fm':
            return GramGrp(pos='n', gender=list(text))
        elif text == 's': # 'that's gender n
            return super().handle_brace(node_class, outer, (chunk[0], 'n'))
        else:
            return super().handle_brace(node_class, outer, chunk)

    def simplify_markup(self, entry):
        getall = lambda x, y: [c for c in enumerate(x.get_children()) if
                isinstance(c[1], y)]
        for elem in [Form, Sense]:
            children = getall(entry, elem)
            if len(children) == 1:
                inner = getall(children[0][1], elem)
                if len(inner) > 0:
                    entry.pop(0)
                for child in inner:
                    entry.add_child(child[1])

        if any_pos(entry, 'adj'):
            forms = getall(entry, Form)
            if len(forms) == 2: # adjective, both male and female form
                # first only has word, second has GramGrp
                if forms[0][1].num_children() == 0 and forms[1][1].num_children() == 1:
                    second_form = entry.pop(forms[1][0])
                    for text in second_form.get_text():
                        forms[0][1].add_text(text)
                    # re-add gramgrp element, only child of second form
                    forms[0][1].add_child(second_form.get_children()[0])
        for elem in [Form, Sense]:
            children = [c[1] for c in getall(entry, elem)]
            for child in children:
                children.extend(c[1] for c in getall(child, elem)) # grandchildren
                gramgrps = getall(child, GramGrp)
                if len(gramgrps) > 1:
                    newgram = GramGrp(pos=gramgrps[0][1].pos)
                    deleted = 0
                    for idx, grp in gramgrps:
                        child.pop(idx - deleted)
                        deleted += 1
                        for attr in ['gender', 'number', 'usg']:
                            data = getattr(grp, attr)
                            if data: # gram. info present
                                setattr(newgram, attr, data)
                    child.add_child(newgram)
        return entry

def any_pos(node, pos):
    """Search for a given part of speech recursively in the current and children
    nodes."""
    node_pos = False
    if isinstance(node, (GramGrp)):
        node_pos = node.pos == pos
    for child in node.get_children():
        node_pos = node_pos or any_pos(child, pos)
    return node_pos


