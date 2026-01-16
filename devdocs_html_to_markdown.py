# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "html2text==2024.2.26"
# ]
# ///

# HTML to Markdown Conversion Tool for DevDocs.
# Base on https://github.com/youssef-tharwat/devdocs-crawler.
# Authors: DeepSeek🧙‍♂️, scillidan🤡
# Usage: uv run file.py <input_dirname> [--output OUTPUT_DIR]
# Default output: _output/<input_dirname>

import os
import sys
import re
import argparse
import shutil
import logging
from pathlib import Path
from typing import List, Optional
import html2text

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be filesystem-safe.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    # Remove leading/trailing underscores and dots
    filename = filename.strip('_.')
    return filename


def html_to_markdown_content(html_content: str, base_path: str = "") -> str:
    """
    Convert HTML content to Markdown using html2text with proper configuration.

    Args:
        html_content: Raw HTML content
        base_path: Base path for relative URL resolution (optional)

    Returns:
        Markdown formatted text
    """
    try:
        # Initialize html2text with DevDocs-optimized configuration
        h = html2text.HTML2Text()

        # Configure for DevDocs-style documentation
        h.ignore_links = False
        h.ignore_images = True  # Don't include images in markdown
        h.ignore_tables = False
        h.ignore_emphasis = False

        # Wrap text at 120 characters for readability
        h.body_width = 120

        # Preserve newlines in the HTML
        h.single_line_break = False

        # Use GitHub-flavored markdown
        h.github_flavored = True

        # Handle relative URLs
        h.baseurl = base_path if base_path else ""

        # Convert HTML to Markdown
        markdown = h.handle(html_content)

        # Post-processing cleanup
        # Remove multiple blank lines
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)

        # Fix code block formatting
        markdown = re.sub(r'```\s*\n```', '```', markdown)

        return markdown.strip()
    except Exception as e:
        logger.error(f"Error converting HTML to Markdown: {e}")
        # Fallback to basic conversion
        return html_to_markdown_basic(html_content)


def html_to_markdown_basic(html_content: str) -> str:
    """
    Basic HTML to Markdown conversion as fallback.

    Args:
        html_content: Raw HTML content

    Returns:
        Basic Markdown formatted text
    """
    # Remove HTML comments
    markdown = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)

    # Headers
    markdown = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<h6[^>]*>(.*?)</h6>', r'###### \1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)

    # Paragraphs
    markdown = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', markdown, flags=re.IGNORECASE | re.DOTALL)

    # Bold
    markdown = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', markdown, flags=re.IGNORECASE | re.DOTALL)

    # Italic
    markdown = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', markdown, flags=re.IGNORECASE | re.DOTALL)
    markdown = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', markdown, flags=re.IGNORECASE | re.DOTALL)

    # Code blocks
    markdown = re.sub(
        r'<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>',
        r'```\n\1\n```',
        markdown,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Inline code
    markdown = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', markdown, flags=re.IGNORECASE | re.DOTALL)

    # Links
    markdown = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        r'[\2](\1)',
        markdown,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove remaining HTML tags
    markdown = re.sub(r'<[^>]+>', '', markdown)

    # Clean up whitespace
    markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
    markdown = re.sub(r'[ \t]+\n', '\n', markdown)

    return markdown.strip()


def convert_html_file(html_path: Path, output_path: Path) -> bool:
    """
    Convert a single HTML file to Markdown.

    Args:
        html_path: Path to HTML file
        output_path: Path for output Markdown file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Read HTML content
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        # Determine relative path for baseurl
        rel_path = str(html_path.parent.relative_to(html_path.parents[-2]))

        # Convert HTML to Markdown
        markdown_content = html_to_markdown_content(html_content, rel_path)

        # If conversion produced empty content, use basic method as fallback
        if not markdown_content or markdown_content.isspace():
            logger.warning(f"html2text produced empty output for {html_path}, using basic conversion")
            markdown_content = html_to_markdown_basic(html_content)

        # Write Markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        logger.debug(f"Converted: {html_path} -> {output_path}")
        return True

    except UnicodeDecodeError:
        # Try with different encodings
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(html_path, 'r', encoding=encoding) as f:
                    html_content = f.read()

                markdown_content = html_to_markdown_content(html_content, str(html_path.parent))

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Converted from: {html_path.name}\n")
                    f.write("# Note: Original file was in non-UTF-8 encoding\n")
                    f.write(f"# Original encoding: {encoding}\n")
                    f.write("\n" + "="*80 + "\n\n")
                    f.write(markdown_content)

                logger.warning(f"Converted with {encoding} encoding: {html_path}")
                return True
            except:
                continue

        logger.error(f"Encoding error with {html_path}, skipping")
        return False

    except Exception as e:
        logger.error(f"Error converting {html_path}: {e}")
        return False


def get_output_filename(html_path: Path, input_base: Path) -> str:
    """
    Generate output filename for Markdown file.

    Args:
        html_path: Path to HTML file
        input_base: Base directory of input

    Returns:
        Output filename
    """
    # Get relative path from input base
    rel_path = html_path.relative_to(input_base)

    # Change extension to .md
    if rel_path.suffix.lower() in ['.html', '.htm']:
        return str(rel_path.with_suffix('.md'))
    else:
        return str(rel_path) + '.md'


def convert_directory(input_dir: str, output_dir: str) -> int:
    """
    Convert all HTML files in directory to Markdown.

    Args:
        input_dir: Input directory containing HTML files
        output_dir: Output directory for Markdown files

    Returns:
        Number of files successfully converted
    """
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()

    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return 0

    if not input_path.is_dir():
        logger.error(f"Input path is not a directory: {input_dir}")
        return 0

    # Count HTML files
    html_files = list(input_path.rglob("*.html")) + list(input_path.rglob("*.htm"))

    if not html_files:
        logger.warning(f"No HTML files found in {input_dir}")
        return 0

    logger.info(f"Found {len(html_files)} HTML files in {input_dir}")
    logger.info(f"Output directory: {output_dir}")

    # Clean output directory
    if output_path.exists():
        logger.warning(f"Output directory exists, cleaning: {output_dir}")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Set conversion date for metadata
    os.environ['CONVERSION_DATE'] = os.environ.get('CONVERSION_DATE', 'local_test')

    # Process each HTML file
    successful = 0
    failed = 0
    failed_files = []

    for i, html_file in enumerate(html_files, 1):
        # Generate output path
        output_filename = get_output_filename(html_file, input_path)
        output_file = output_path / output_filename

        # Log progress
        if i % 100 == 0 or i == len(html_files):
            logger.info(f"Processing file {i}/{len(html_files)}: {html_file}")

        # Convert file
        if convert_html_file(html_file, output_file):
            successful += 1
        else:
            failed += 1
            failed_files.append(str(html_file))

    # Print summary statistics
    print("\n" + "="*60)
    print("CONVERSION SUMMARY")
    print("="*60)
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Total HTML files found:  {len(html_files)}")
    print(f"Successfully converted:  {successful}")
    print(f"Failed:                  {failed}")
    print(f"Conversion date:         {os.environ.get('CONVERSION_DATE', 'unknown')}")

    if failed_files:
        print(f"\nFailed files ({len(failed_files)}):")
        for file in failed_files[:10]:  # Show first 10 failed files
            print(f"  - {file}")
        if len(failed_files) > 10:
            print(f"  ... and {len(failed_files) - 10} more")

    # Show output directory structure
    if successful > 0:
        print(f"\nGenerated files in {output_dir}:")
        try:
            for root, dirs, files in os.walk(output_dir):
                level = root.replace(str(output_dir), '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in sorted(files)[:5]:  # Show first 5 files per directory
                    print(f"{subindent}{file}")
                if len(files) > 5:
                    print(f"{subindent}... and {len(files) - 5} more files")
        except Exception as e:
            print(f"  Could not list output directory: {e}")

    print("="*60)

    return successful


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert HTML files to Markdown while preserving directory structure"
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing HTML files to convert"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: _output/<input_dir_basename>)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output, only show summary"
    )

    args = parser.parse_args()

    # Set logging level
    if args.quiet:
        logger.setLevel(logging.WARNING)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        input_basename = os.path.basename(os.path.normpath(args.input_dir))
        output_dir = f"_output/{input_basename}"

    # Convert directory
    try:
        successful = convert_directory(args.input_dir, output_dir)
        if successful > 0:
            logger.info(f"\nMarkdown files saved to: {output_dir}")
            sys.exit(0)
        else:
            logger.error("\nNo files were converted")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nConversion interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\nConversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
