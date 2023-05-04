import jinja2

ENVIRONMENT = jinja2.Environment(
    block_start_string='<!',
    block_end_string='!>',
    variable_start_string='<<',
    variable_end_string='>>',
    comment_start_string='<#',
    comment_end_string='#>',
    trim_blocks=False,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render(template_filename, **args):
    with open(template_filename, encoding='utf-8') as template_file:
        template_str = template_file.read()
    template = ENVIRONMENT.from_string(template_str)
    return template.render(**args)
