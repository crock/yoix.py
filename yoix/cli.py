"""Command line interface for Yoix."""

import click
import csv
import json
from datetime import datetime
from pathlib import Path

from .core import SiteBuilder
from .db import DatabaseManager
from .utils.automap import auto_map_columns, top_candidates

@click.group()
def yoix():
    click.echo('Starting Yoix...')

@yoix.command("build")
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
def yoix_build(config, partials, output, templates, input):
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


@yoix.command("import")
@click.argument("filename", required=True, type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=str))
@click.option("--name", "-n", help="Dataset name for storage (default: filename without extension)")
@click.option("--threshold", "-t", default=75, help="Auto-mapping confidence threshold (0-100, default: 75)")
@click.option("--preview", "-p", is_flag=True, help="Preview mapping without importing")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing dataset")
def yoix_import(filename: str, name: str, threshold: int, preview: bool, force: bool):
    """Import CSV data for use in templates.
    
    This command imports CSV data, automatically maps column headers to canonical fields,
    and stores the data in the database for use in site templates and plugins.
    """
    try:
        file_path = Path(filename)
        dataset_name = name or file_path.stem
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Check if dataset already exists
        existing_data = db_manager.cache_get(f"dataset:{dataset_name}")
        if existing_data and not force:
            click.echo(f"Dataset '{dataset_name}' already exists. Use --force to overwrite.", err=True)
            raise click.Abort()
        
        # Read CSV file
        click.echo(f"Reading CSV file: {file_path}")
        rows = []
        headers = []
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            # Try to detect delimiter, fall back to comma
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except csv.Error:
                delimiter = ','
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            headers = reader.fieldnames or []
            
            # Read sample rows for auto-mapping (first 100 rows)
            sample_rows = []
            for i, row in enumerate(reader):
                if i < 100:  # Sample for auto-mapping
                    sample_rows.append(row)
                rows.append(row)
        
        if not headers:
            click.echo("Error: No headers found in CSV file", err=True)
            raise click.Abort()
        
        click.echo(f"Found {len(headers)} columns and {len(rows)} rows")
        
        # Get any previously learned mappings for this dataset
        learned_mappings = db_manager.cache_get(f"mappings:{dataset_name}") or {}
        
        # Auto-map columns
        click.echo("Auto-mapping column headers...")
        mapping, scores = auto_map_columns(headers, sample_rows, learned_mappings, threshold)
        
        # Display mapping results
        if mapping:
            click.echo("\nAuto-mapped columns:")
            for field, header in mapping.items():
                score = next((s["score"] for s in scores[field] if s["header"] == header), 0)
                click.echo(f"  {field} -> {header} (confidence: {score}%)")
        else:
            click.echo("No columns were auto-mapped with sufficient confidence.")
        
        # Show unmapped columns
        unmapped = [h for h in headers if h not in mapping.values()]
        if unmapped:
            click.echo(f"\nUnmapped columns: {', '.join(unmapped)}")
        
        # Show mapping suggestions for unmapped columns
        for header in unmapped:
            click.echo(f"\nSuggestions for '{header}':")
            for field, field_scores in scores.items():
                candidates = [(s["header"], s["score"]) for s in field_scores if s["header"] == header]
                if candidates and candidates[0][1] > 0:
                    click.echo(f"  {field}: {candidates[0][1]}% confidence")
        
        if preview:
            click.echo("\nPreview mode - no data imported.")
            return
        
        # Store the dataset in database
        dataset = {
            "name": dataset_name,
            "filename": str(file_path),
            "headers": headers,
            "mapping": mapping,
            "rows": rows,
            "total_rows": len(rows),
            "mapped_fields": list(mapping.keys()),
            "unmapped_columns": unmapped,
            "import_date": datetime.now().isoformat()
        }
        
        # Store main dataset
        db_manager.cache_set(f"dataset:{dataset_name}", dataset, category="import")
        
        # Store learned mappings for future imports
        if mapping:
            # Convert mapping to learned format (field -> [header])
            learned_for_storage = {}
            for field, header in mapping.items():
                learned_for_storage[field] = learned_mappings.get(field, []) + [header]
                # Remove duplicates while preserving order
                learned_for_storage[field] = list(dict.fromkeys(learned_for_storage[field]))
            
            db_manager.cache_set(f"mappings:{dataset_name}", learned_for_storage, category="import")
        
        click.echo(f"\nSuccessfully imported dataset '{dataset_name}':")
        click.echo(f"  - {len(rows)} rows imported")
        click.echo(f"  - {len(mapping)} columns mapped")
        click.echo(f"  - {len(unmapped)} columns unmapped")
        click.echo(f"\nDataset is now available in templates as 'datasets.{dataset_name}'")
        
    except FileNotFoundError:
        click.echo(f"Error: File '{filename}' not found", err=True)
        raise click.Abort()
    except csv.Error as e:
        click.echo(f"Error reading CSV file: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

