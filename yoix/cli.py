"""Command line interface for Yoix."""

import click
from pathlib import Path

from .core import SiteBuilder


@click.command()
@click.option(
    '--config',
    '-c',
    default='yoix.config.toml',
    help='Path to config file (default: yoix.config.toml)',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=str)
)
@click.option(
    '--partials',
    '-p',
    help='Override partials directory path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str)
)
@click.option(
    '--output',
    '-o',
    help='Override public directory path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str)
)
@click.option(
    '--templates',
    '-t',
    help='Override templates directory path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str)
)
@click.option(
    '--input',
    '-i',
    help='Override content directory path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str)
)
def main(config, partials, output, templates, input):
    """Build a website from markdown files.
    
    This command builds a website from markdown files in the content directory,
    using configuration from the specified config file. Directory paths can be
    overridden using command line options.
    """
    try:
        # Initialize with config file
        site_builder = SiteBuilder(config)
        
        # Override paths if specified
        if partials:
            site_builder.partials_dir = Path(partials)
        if output:
            site_builder.public_dir = Path(output)
        if templates:
            site_builder.templates_dir = Path(templates)
        if input:
            site_builder.content_dir = Path(input)
            
        # Build site
        site_builder.build(site_builder.content_dir)
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
