#!/usr/bin/env python
import os
import sys
import argparse
import json
from singer import metadata, get_logger
from InquirerPy.prompts.checkbox import CheckboxPrompt
from InquirerPy.base.control import Choice

logger = get_logger().getChild('singer-discover')

def breadcrumb_name(breadcrumb):
    name = ".".join(breadcrumb)
    name = name.replace('properties.', '')
    name = name.replace('.items', '[]')
    return name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', type=str, required=True)

    if sys.stdin.isatty():
        parser.add_argument('--input', '-i', type=str, required=True)

        args = parser.parse_args()

        with open(args.input) as f:
            catalog = json.load(f)

    else:

        args = parser.parse_args()

        catalog = json.loads(sys.stdin.read())

        sys.stdin = sys.stdout

    logger.info("Catalog configuration starting...")
    
    base_checkbox = {
            'enabled_symbol': '◼',
            'disabled_symbol': '◻',
            "pointer": ">",
            "instruction": "Press <space> to select, <a> to toggle all, <i> to invert selection and <u> to unset all.",
            'keybindings': {
                "toggle-all": [{"key": "i"}],
                "toggle-all-true": [{"key": "a"}],
                "toggle-all-false": [{"key": "u"}],
            }
        }
    
    stream_choices = [Choice(stream['stream']) for stream in catalog['streams']]

    select_streams = dict({
        'message': 'Select Streams',
        'choices': stream_choices
    }, **base_checkbox)

    selected_streams = CheckboxPrompt(**select_streams).execute()

    for i, stream in enumerate(catalog['streams']):

        mdata = metadata.to_map(stream['metadata'])

        if stream['stream'] not in selected_streams:
            mdata = metadata.write(
                mdata, (), 'selected', False
            )
        else:
            mdata = metadata.write(
                mdata, (), 'selected', True
            )

            fields = []

            field_reference = {}

            for breadcrumb, field in mdata.items():

                if breadcrumb != ():
                    enabled = False
                    if metadata.get(
                            mdata, breadcrumb, 'inclusion') == 'automatic':
                        enabled = True

                    elif metadata.get(
                            mdata, breadcrumb, 'selected-by-default'):
                        enabled = True

                    name = breadcrumb_name(breadcrumb)

                    field_reference[name] = breadcrumb

                    fields.append(Choice(name, enabled=enabled))

            try:
                fields = sorted(fields, key=lambda field: field.name)
            except KeyError:
                pass
            
            select_streams = dict({
                'message': f"Select fields from stream: `{stream['stream']}`",
                'choices': fields
            }, **base_checkbox)

            selections = CheckboxPrompt(**select_streams).execute()

            selections = [
                field_reference[n] for n in selections
                if n != "Select All"
            ]

            for breadcrumb in mdata.keys():
                if breadcrumb != ():
                    if (
                        metadata.get(
                            mdata, breadcrumb, 'inclusion') == "automatic"
                    ) or (
                        breadcrumb in selections
                    ):
                        mdata = metadata.write(
                            mdata, breadcrumb, 'selected', True)
                    else:
                        mdata = metadata.write(
                            mdata, breadcrumb, 'selected', False)

            catalog['streams'][i]['metadata'] = metadata.to_list(mdata)

    logger.info("Catalog configuration saved.")

    with open(args.output, 'w') as f:
        json.dump(catalog, f, indent=2)


if __name__ == '__main__':
    main()
