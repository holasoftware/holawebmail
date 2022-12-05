import json


from django.utils.safestring import mark_safe
from django.template import Library, TemplateSyntaxError, Node


register = Library()


class RangeNode(Node):
    child_nodelists = ('nodelist_loop',)

    def __init__(self, loopvar, unresolved_range_params, nodelist_loop):
        self.loopvar = loopvar
        self.unresolved_range_params = unresolved_range_params
        self.nodelist_loop = nodelist_loop

    def __repr__(self):
        reversed_text = ' reversed' if self.is_reversed else ''
        return '<%s: range %s %s, tail_len: %d>' % (
            self.__class__.__name__,
            self.loopvar,
            self.range_params,
            len(self.nodelist_loop),
        )

    def render(self, context):
        if 'forloop' in context:
            parentloop = context['forloop']
        else:
            parentloop = {}

        with context.push():
            range_params = []

            for unresolved_param in self.unresolved_range_params:
                range_param = unresolved_param.resolve(context)
                try:
                    range_param = int(range_param)
                except ValueError:
                    raise TemplateSyntaxError("range params should be integers: %s" % range_param)

                range_params.append(range_param)

            nodelist = []

            # Create a forloop value in the context.  We'll update counters on each
            # iteration just below.
            context['forloop'] = {'parentloop': parentloop}

            for item in range(*range_params):
                context[self.loopvar] = item

                for node in self.nodelist_loop:
                    nodelist.append(node.render_annotated(context))

        return mark_safe(''.join(nodelist))


@register.tag('range')
def do_range(parser, token):
    bits = token.split_contents()
    if len(bits) < 3:
        raise TemplateSyntaxError("'range' statements should have at least three words: %s" % token.contents)

    if len(bits) > 5:
        raise TemplateSyntaxError("'range' statements should have at maximum five words: %s" % token.contents)

    loopvar = bits[1]

    if not (loopvar.isalnum() and loopvar[0].isalpha()):
        raise TemplateSyntaxError("loopvar should be alphunumeric starting with a letter")

    unresolved_range_params = []
    for bit in bits[2:]:
        unresolved_range_params.append(parser.compile_filter(bit))


    nodelist_loop = parser.parse(('endrange',))
    parser.next_token()

    return RangeNode(loopvar, unresolved_range_params, nodelist_loop)


@register.filter
def attr(obj, attribute_name):
    attribute_value = getattr(obj, attribute_name, None)

    return attribute_value

@register.filter
def dict_get(obj, key_name):
    try:
        value = obj[key_name]
    except KeyError:
        return None

    return value

def split_css_classes(css_classes):
    """Turn string into a list of CSS classes."""
    classes_list = str(css_classes).strip().split()
    return classes_list


def add_css_class(css_classes, css_class, prepend=False):
    """Add a CSS class to a string of CSS classes."""
    classes_list = split_css_classes(css_classes)
    classes_to_add = [c for c in split_css_classes(css_class) if c not in classes_list]
    if prepend:
        classes_list = classes_to_add + classes_list
    else:
        classes_list += classes_to_add
    return " ".join(classes_list)


def remove_css_class(css_classes, css_class):
    """Remove a CSS class from a string of CSS classes."""
    remove = set(split_css_classes(css_class))
    classes_list = [c for c in split_css_classes(css_classes) if c not in remove]
    return " ".join(classes_list)


@register.filter
def get_dict(dict_obj, key_name):
    print(dict_obj, key_name)

    try:
        return dict_obj[key_name]
    except KeyError:
        pass


@register.filter
def to_str(obj):
    return str(obj)


@register.filter
def to_json(obj):
    return mark_safe(json.dumps(obj))


@register.filter
def add_class_name(field, class_name):
    if "class" in field.field.widget.attrs:
        all_class_names = field.field.widget.attrs["class"]
        all_class_names = add_css_class(all_class_names, class_name)
        field.field.widget.attrs["class"] = all_class_names
    else:
        field.field.widget.attrs["class"] = class_name

    return field

