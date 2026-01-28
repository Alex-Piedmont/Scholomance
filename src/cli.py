"""CLI interface for the university tech transfer scraper."""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from .config import settings
from .database import db, Database, Technology
from .scrapers import SCRAPERS, get_scraper
from .classifier import Classifier, ClassificationResult, ClassificationError
from .taxonomy import get_top_fields, get_subfields
from .patent_detector import patent_detector, PatentStatus

# Configure console for rich output
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity."""
    logger.remove()
    level = "DEBUG" if verbose else settings.log_level
    logger.add(sys.stderr, level=level, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    if settings.log_file:
        logger.add(settings.log_file, rotation="10 MB", level=level)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """University Tech Transfer Scraper CLI.

    Scrape and search technology listings from university tech transfer offices.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@main.command()
@click.option(
    "--university", "-u",
    type=click.Choice(list(SCRAPERS.keys())),
    help="University to scrape (e.g., 'stanford')"
)
@click.option("--all", "scrape_all", is_flag=True, help="Scrape all configured universities")
@click.option("--limit", "-l", type=int, default=None, help="Limit number of pages to scrape")
@click.pass_context
def scrape(ctx: click.Context, university: Optional[str], scrape_all: bool, limit: Optional[int]) -> None:
    """Scrape technology listings from university websites.

    Examples:
        tech-scraper scrape --university stanford
        tech-scraper scrape --all
        tech-scraper scrape -u stanford --limit 5
    """
    if not university and not scrape_all:
        console.print("[red]Error:[/red] Please specify --university or --all")
        raise SystemExit(1)

    universities = list(SCRAPERS.keys()) if scrape_all else [university]

    for uni in universities:
        asyncio.run(_scrape_university(uni, limit, ctx.obj["verbose"]))


async def _scrape_university(university: str, limit: Optional[int], verbose: bool) -> None:
    """Async function to scrape a single university."""
    console.print(f"\n[bold blue]Scraping {university}...[/bold blue]")

    try:
        scraper = get_scraper(university)
        technologies = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Scraping {university}...", total=None)

            page_count = 0
            async for tech in scraper.scrape():
                technologies.append(tech)

                if len(technologies) % 15 == 0:
                    page_count += 1
                    progress.update(task, description=f"Scraped {len(technologies)} technologies...")

                    if limit and page_count >= limit:
                        console.print(f"[yellow]Reached page limit ({limit})[/yellow]")
                        break

        # Store in database
        console.print(f"[dim]Storing {len(technologies)} technologies in database...[/dim]")
        new_count, updated_count = db.bulk_insert_technologies(technologies)

        console.print(f"[green]Done![/green] New: {new_count}, Updated: {updated_count}")

    except Exception as e:
        console.print(f"[red]Error scraping {university}:[/red] {e}")
        if verbose:
            logger.exception("Scraping error")
        raise SystemExit(1)


@main.command()
@click.option("--keyword", "-k", type=str, help="Search keyword in title/description")
@click.option("--university", "-u", type=str, help="Filter by university code")
@click.option("--field", "-f", type=str, help="Filter by top field")
@click.option("--subfield", "-s", type=str, help="Filter by subfield")
@click.option("--geography", "-g", type=str, help="Filter by patent geography")
@click.option("--from-date", type=click.DateTime(), help="Filter by scraped_at >= date (YYYY-MM-DD)")
@click.option("--to-date", type=click.DateTime(), help="Filter by scraped_at <= date (YYYY-MM-DD)")
@click.option("--limit", "-l", type=int, default=20, help="Maximum results to return")
@click.option("--offset", "-o", type=int, default=0, help="Pagination offset")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--csv", "output_csv", type=click.Path(), help="Export results to CSV file")
def search(
    keyword: Optional[str],
    university: Optional[str],
    field: Optional[str],
    subfield: Optional[str],
    geography: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    limit: int,
    offset: int,
    output_json: bool,
    output_csv: Optional[str],
) -> None:
    """Search technologies in the database.

    Examples:
        tech-scraper search --keyword "robotics"
        tech-scraper search -u stanford -k "machine learning"
        tech-scraper search --field "MedTech" --json
        tech-scraper search --from-date 2024-01-01 --csv results.csv
        tech-scraper search -g "US" --limit 100
    """
    results = db.search_technologies(
        keyword=keyword,
        university=university,
        top_field=field,
        subfield=subfield,
        patent_geography=geography,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    if not results:
        console.print("[yellow]No technologies found matching your criteria.[/yellow]")
        return

    if output_csv:
        import csv

        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "university", "tech_id", "title", "description",
                "url", "top_field", "subfield", "keywords", "patent_geography", "scraped_at"
            ])

            for tech in results:
                writer.writerow([
                    tech.id,
                    tech.university,
                    tech.tech_id,
                    tech.title,
                    tech.description or "",
                    tech.url,
                    tech.top_field or "",
                    tech.subfield or "",
                    "|".join(tech.keywords) if tech.keywords else "",
                    "|".join(tech.patent_geography) if tech.patent_geography else "",
                    tech.scraped_at.isoformat() if tech.scraped_at else "",
                ])

        console.print(f"[green]Exported {len(results)} results to {output_csv}[/green]")
        return

    if output_json:
        output = []
        for tech in results:
            output.append({
                "id": tech.id,
                "university": tech.university,
                "tech_id": tech.tech_id,
                "title": tech.title,
                "description": tech.description[:200] + "..." if tech.description and len(tech.description) > 200 else tech.description,
                "url": tech.url,
                "top_field": tech.top_field,
                "subfield": tech.subfield,
                "keywords": tech.keywords,
                "patent_geography": tech.patent_geography,
                "scraped_at": tech.scraped_at.isoformat() if tech.scraped_at else None,
            })
        click.echo(json.dumps(output, indent=2))
    else:
        table = Table(title=f"Technologies ({len(results)} results)")
        table.add_column("ID", style="dim")
        table.add_column("University", style="cyan")
        table.add_column("Title", style="bold")
        table.add_column("Field")
        table.add_column("URL", style="dim")

        for tech in results:
            title = tech.title[:50] + "..." if len(tech.title) > 50 else tech.title
            url = tech.url[:40] + "..." if len(tech.url) > 40 else tech.url
            table.add_row(
                str(tech.id),
                tech.university,
                title,
                tech.top_field or "-",
                url,
            )

        console.print(table)


@main.command()
@click.option("--university", "-u", type=str, help="Show stats for specific university")
def stats(university: Optional[str]) -> None:
    """Show database statistics.

    Examples:
        tech-scraper stats
        tech-scraper stats -u stanford
    """
    if university:
        count = db.count_technologies(university=university)
        console.print(f"[bold]{university}:[/bold] {count} technologies")
    else:
        total = db.count_technologies()
        console.print(f"[bold]Total technologies:[/bold] {total}")

        for uni_code in SCRAPERS.keys():
            count = db.count_technologies(university=uni_code)
            if count > 0:
                console.print(f"  {uni_code}: {count}")


@main.command()
@click.option("--batch", "-b", type=int, default=100, help="Number of technologies to classify")
@click.option("--university", "-u", type=str, help="Only classify technologies from this university")
@click.option("--force", is_flag=True, help="Re-classify already classified technologies")
@click.option("--dry-run", is_flag=True, help="Show what would be classified without making API calls")
@click.option("--model", type=str, default=None, help="Model to use (default: claude-3-5-haiku)")
@click.pass_context
def classify(
    ctx: click.Context,
    batch: int,
    university: Optional[str],
    force: bool,
    dry_run: bool,
    model: Optional[str],
) -> None:
    """Classify technologies using Claude API.

    Examples:
        tech-scraper classify --batch 100
        tech-scraper classify --university stanford --force
        tech-scraper classify --dry-run
    """
    # Get technologies to classify
    technologies = db.get_technologies_for_classification(
        university=university,
        force=force,
        limit=batch,
    )

    if not technologies:
        console.print("[yellow]No technologies to classify.[/yellow]")
        if not force:
            console.print("[dim]Use --force to re-classify already classified technologies.[/dim]")
        return

    console.print(f"\n[bold blue]Found {len(technologies)} technologies to classify[/bold blue]")

    if dry_run:
        console.print("[yellow]Dry run mode - no API calls will be made[/yellow]")
        table = Table(title="Technologies to classify")
        table.add_column("ID", style="dim")
        table.add_column("University")
        table.add_column("Title")
        table.add_column("Current Field")

        for tech in technologies[:20]:  # Show first 20
            title = tech.title[:50] + "..." if len(tech.title) > 50 else tech.title
            table.add_row(
                str(tech.id),
                tech.university,
                title,
                tech.top_field or "-",
            )

        console.print(table)
        if len(technologies) > 20:
            console.print(f"[dim]... and {len(technologies) - 20} more[/dim]")
        return

    # Initialize classifier
    try:
        classifier = Classifier(model=model) if model else Classifier()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Set ANTHROPIC_API_KEY in your environment or .env file[/dim]")
        raise SystemExit(1)

    # Run classification
    success_count = 0
    error_count = 0
    total_cost = 0.0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Classifying...", total=len(technologies))

        for tech in technologies:
            result = classifier.classify(tech.title, tech.description)

            if isinstance(result, ClassificationResult):
                # Update database
                db.update_technology_classification(
                    tech_id=tech.id,
                    top_field=result.top_field,
                    subfield=result.subfield,
                    confidence=result.confidence,
                    model=result.model,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    total_cost=result.total_cost,
                    raw_response={"reasoning": result.reasoning},
                )
                success_count += 1
                total_cost += result.total_cost

                if ctx.obj["verbose"]:
                    console.print(
                        f"[dim]{tech.id}:[/dim] {result.top_field} / {result.subfield} "
                        f"(confidence: {result.confidence:.2f})"
                    )
            else:
                # Classification error
                db.mark_classification_failed(tech.id, result.message)
                error_count += 1

                if ctx.obj["verbose"]:
                    console.print(f"[red]{tech.id}:[/red] Error - {result.message}")

            progress.update(task, advance=1, description=f"Classified {success_count}/{len(technologies)}")

    # Summary
    console.print(f"\n[bold green]Classification complete![/bold green]")
    console.print(f"  Successful: {success_count}")
    console.print(f"  Errors: {error_count}")
    console.print(f"  Total cost: ${total_cost:.4f}")


@main.command()
@click.option("--university", "-u", type=str, help="Show stats for specific university")
def classification_stats(university: Optional[str]) -> None:
    """Show classification statistics.

    Examples:
        tech-scraper classification-stats
        tech-scraper classification-stats -u stanford
    """
    # Get counts
    unclassified = db.count_unclassified(university=university)
    classified = db.count_classified(university=university)
    total = unclassified + classified

    console.print(f"\n[bold]Classification Status[/bold]")
    if university:
        console.print(f"University: {university}")
    console.print(f"  Total: {total}")
    console.print(f"  Classified: {classified} ({classified/total*100:.1f}%)" if total > 0 else "  Classified: 0")
    console.print(f"  Pending: {unclassified}")

    # Get detailed stats
    stats = db.get_classification_stats()
    if stats["total_classifications"] > 0:
        console.print(f"\n[bold]Cost Summary[/bold]")
        console.print(f"  Total API cost: ${stats['total_cost']:.4f}")
        console.print(f"  Total classifications: {stats['total_classifications']}")
        avg_cost = stats['total_cost'] / stats['total_classifications']
        console.print(f"  Average per tech: ${avg_cost:.6f}")

    if stats.get("by_field"):
        console.print(f"\n[bold]By Field[/bold]")
        for field, count in sorted(stats["by_field"].items(), key=lambda x: -x[1]):
            console.print(f"  {field}: {count}")


@main.command()
@click.option("--batch", "-b", type=int, default=100, help="Number of technologies to process")
@click.option("--university", "-u", type=str, help="Only detect patents for this university")
@click.option("--force", is_flag=True, help="Re-detect for technologies that already have patent status")
@click.option("--dry-run", is_flag=True, help="Show what would be detected without updating database")
@click.pass_context
def detect_patents(
    ctx: click.Context,
    batch: int,
    university: Optional[str],
    force: bool,
    dry_run: bool,
) -> None:
    """Detect patent status for technologies.

    Analyzes technologies to detect patent status from:
    - Raw data (API-provided patent info)
    - URL patterns (patent numbers)
    - Text content (keywords in title/description)

    Examples:
        tech-scraper detect-patents --batch 100
        tech-scraper detect-patents --university jhu --force
        tech-scraper detect-patents --dry-run
    """
    # Get technologies to process
    technologies = db.get_technologies_for_patent_detection(
        university=university,
        force=force,
        limit=batch,
    )

    if not technologies:
        console.print("[yellow]No technologies to process.[/yellow]")
        if not force:
            console.print("[dim]Use --force to re-detect for technologies with existing patent status.[/dim]")
        return

    console.print(f"\n[bold blue]Found {len(technologies)} technologies to process[/bold blue]")

    if dry_run:
        console.print("[yellow]Dry run mode - no database updates[/yellow]")

        table = Table(title="Patent Detection Results (Dry Run)")
        table.add_column("ID", style="dim")
        table.add_column("University")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Confidence")
        table.add_column("Source")

        status_counts: dict[str, int] = {}

        for tech in technologies[:50]:  # Show first 50
            result = patent_detector.detect(
                raw_data=tech.raw_data,
                url=tech.url,
                title=tech.title,
                description=tech.description,
            )

            status_str = result.status.value
            status_counts[status_str] = status_counts.get(status_str, 0) + 1

            # Color based on status
            if result.status == PatentStatus.GRANTED:
                status_display = f"[green]{status_str}[/green]"
            elif result.status == PatentStatus.PENDING:
                status_display = f"[yellow]{status_str}[/yellow]"
            elif result.status == PatentStatus.UNKNOWN:
                status_display = f"[dim]{status_str}[/dim]"
            else:
                status_display = status_str

            title = tech.title[:40] + "..." if len(tech.title) > 40 else tech.title
            table.add_row(
                str(tech.id),
                tech.university,
                title,
                status_display,
                f"{result.confidence:.2f}",
                result.source,
            )

        console.print(table)

        if len(technologies) > 50:
            console.print(f"[dim]... and {len(technologies) - 50} more[/dim]")

        console.print(f"\n[bold]Status Summary:[/bold]")
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            console.print(f"  {status}: {count}")
        return

    # Process technologies
    success_count = 0
    status_counts: dict[str, int] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting patents...", total=len(technologies))

        for tech in technologies:
            result = patent_detector.detect(
                raw_data=tech.raw_data,
                url=tech.url,
                title=tech.title,
                description=tech.description,
            )

            # Update database
            db.update_technology_patent_status(
                tech_id=tech.id,
                patent_status=result.status.value,
                confidence=result.confidence,
                source=result.source,
            )

            status_str = result.status.value
            status_counts[status_str] = status_counts.get(status_str, 0) + 1
            success_count += 1

            if ctx.obj["verbose"]:
                console.print(
                    f"[dim]{tech.id}:[/dim] {result.status.value} "
                    f"(confidence: {result.confidence:.2f}, source: {result.source})"
                )

            progress.update(task, advance=1, description=f"Processed {success_count}/{len(technologies)}")

    # Summary
    console.print(f"\n[bold green]Patent detection complete![/bold green]")
    console.print(f"  Processed: {success_count}")
    console.print(f"\n[bold]By Status:[/bold]")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        console.print(f"  {status}: {count}")


@main.command()
@click.option("--batch", "-b", type=int, default=50, help="Number of technologies to process")
@click.option(
    "--university", "-u",
    type=click.Choice(["mit", "columbia", "jhu"]),
    required=True,
    help="University to enrich (must be MIT, Columbia, or JHU)"
)
@click.option("--force", is_flag=True, help="Re-enrich technologies that already have patent status")
@click.option("--dry-run", is_flag=True, help="Show what would be enriched without fetching pages")
@click.pass_context
def enrich_patents(
    ctx: click.Context,
    batch: int,
    university: str,
    force: bool,
    dry_run: bool,
) -> None:
    """Enrich patent data by fetching detail pages for HTML-based scrapers.

    This command fetches individual technology detail pages to extract
    patent information that isn't available in the listing/API data.

    Supports: MIT, Columbia, JHU

    Examples:
        tech-scraper enrich-patents --university mit --batch 50
        tech-scraper enrich-patents -u jhu --force
        tech-scraper enrich-patents -u columbia --dry-run
    """
    asyncio.run(_enrich_patents(university, batch, force, dry_run, ctx.obj["verbose"]))


async def _enrich_patents(
    university: str,
    batch: int,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Async function to enrich patent data from detail pages."""
    from .scrapers import get_scraper

    # Get technologies with unknown patent status for this university
    technologies = db.get_technologies_for_patent_detection(
        university=university,
        force=force,
        limit=batch,
    )

    if not technologies:
        console.print(f"[yellow]No technologies to enrich for {university}.[/yellow]")
        if not force:
            console.print("[dim]Use --force to re-enrich technologies with existing patent status.[/dim]")
        return

    console.print(f"\n[bold blue]Found {len(technologies)} technologies to enrich from {university}[/bold blue]")

    if dry_run:
        console.print("[yellow]Dry run mode - no pages will be fetched[/yellow]")

        from rich.table import Table
        table = Table(title=f"Technologies to Enrich ({university})")
        table.add_column("ID", style="dim")
        table.add_column("Title")
        table.add_column("URL", style="dim")
        table.add_column("Current Status")

        for tech in technologies[:30]:
            title = tech.title[:40] + "..." if len(tech.title) > 40 else tech.title
            url = tech.url[:50] + "..." if len(tech.url) > 50 else tech.url
            table.add_row(
                str(tech.id),
                title,
                url,
                tech.patent_status or "unknown",
            )

        console.print(table)
        if len(technologies) > 30:
            console.print(f"[dim]... and {len(technologies) - 30} more[/dim]")
        return

    # Get the scraper for this university
    try:
        scraper = get_scraper(university)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    # Process technologies
    enriched_count = 0
    detected_count = 0
    error_count = 0
    status_counts: dict[str, int] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Enriching patent data...", total=len(technologies))

        for tech in technologies:
            try:
                # Fetch detail page
                detail = await scraper.scrape_technology_detail(tech.url)

                if detail:
                    enriched_count += 1

                    # Merge detail data into raw_data
                    raw_data = tech.raw_data or {}
                    raw_data.update(detail)

                    # Re-detect patent status with enriched data
                    result = patent_detector.detect(
                        raw_data=raw_data,
                        url=tech.url,
                        title=tech.title,
                        description=tech.description,
                    )

                    # Update database with enriched raw_data and patent status
                    db.update_technology_with_enriched_data(
                        tech_id=tech.id,
                        raw_data=raw_data,
                        patent_status=result.status.value,
                        patent_confidence=result.confidence,
                        patent_source=result.source,
                    )

                    if result.status.value != "unknown":
                        detected_count += 1

                    status_str = result.status.value
                    status_counts[status_str] = status_counts.get(status_str, 0) + 1

                    if verbose:
                        console.print(
                            f"[dim]{tech.id}:[/dim] {result.status.value} "
                            f"(confidence: {result.confidence:.2f})"
                        )
                else:
                    error_count += 1
                    if verbose:
                        console.print(f"[red]{tech.id}:[/red] Could not fetch detail page")

                # Rate limiting
                await asyncio.sleep(scraper.delay_seconds)

            except Exception as e:
                error_count += 1
                if verbose:
                    console.print(f"[red]{tech.id}:[/red] Error - {e}")

            progress.update(task, advance=1, description=f"Enriched {enriched_count}/{len(technologies)}")

    # Clean up scraper session
    await scraper._close_session()

    # Summary
    console.print(f"\n[bold green]Patent enrichment complete![/bold green]")
    console.print(f"  Enriched: {enriched_count}")
    console.print(f"  With patent info: {detected_count}")
    console.print(f"  Errors: {error_count}")
    console.print(f"\n[bold]By Status:[/bold]")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        console.print(f"  {status}: {count}")


@main.command()
@click.option("--university", "-u", type=str, help="Show stats for specific university")
def patent_stats(university: Optional[str]) -> None:
    """Show patent status statistics.

    Examples:
        tech-scraper patent-stats
        tech-scraper patent-stats -u jhu
    """
    counts = db.count_by_patent_status(university=university)

    console.print(f"\n[bold]Patent Status Statistics[/bold]")
    if university:
        console.print(f"University: {university}")

    total = sum(counts.values())
    console.print(f"  Total: {total}")

    for status in ["granted", "pending", "provisional", "filed", "expired", "unknown"]:
        count = counts.get(status, 0)
        pct = (count / total * 100) if total > 0 else 0
        console.print(f"  {status.capitalize()}: {count} ({pct:.1f}%)")


@main.command()
def list_fields() -> None:
    """List all available classification fields and subfields.

    Example:
        tech-scraper list-fields
    """
    from .taxonomy import TAXONOMY

    for field_name, definition in TAXONOMY.items():
        console.print(f"\n[bold cyan]{field_name}[/bold cyan]")
        console.print(f"[dim]{definition.description}[/dim]")
        console.print("Subfields:")
        for subfield in definition.subfields:
            console.print(f"  - {subfield}")


@main.command()
def list_universities() -> None:
    """List all configured university scrapers.

    Example:
        tech-scraper list-universities
    """
    from .scrapers import list_scrapers
    from .scrapers.registry import get_registry_info

    info = get_registry_info()

    console.print(f"\n[bold]Configured Universities ({info['enabled_universities']}/{info['total_universities']} enabled)[/bold]\n")

    table = Table()
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Base URL", style="dim")
    table.add_column("Status")

    for uni in info["universities"]:
        status = "[green]Enabled[/green]" if uni["enabled"] else "[red]Disabled[/red]"
        table.add_row(
            uni["code"],
            uni["name"],
            uni["base_url"],
            status,
        )

    console.print(table)


@main.command()
@click.option("--weekly", is_flag=True, help="Set up weekly schedule")
@click.option("--daily", is_flag=True, help="Set up daily schedule")
@click.option("--university", "-u", type=str, help="University to schedule (default: all)")
@click.option("--hour", type=int, default=2, help="Hour to run (0-23)")
@click.option("--day", type=str, default="sun", help="Day of week for weekly (mon-sun)")
@click.option("--run", is_flag=True, help="Run scheduler in foreground")
@click.option("--list", "list_jobs", is_flag=True, help="List scheduled jobs")
def schedule(
    weekly: bool,
    daily: bool,
    university: Optional[str],
    hour: int,
    day: str,
    run: bool,
    list_jobs: bool,
) -> None:
    """Set up scheduled scraping tasks.

    Examples:
        tech-scraper schedule --weekly --run
        tech-scraper schedule --daily -u stanford --hour 3
        tech-scraper schedule --list
    """
    from .scheduler import scheduler as scrape_scheduler

    if list_jobs:
        jobs = scrape_scheduler.list_jobs()
        if not jobs:
            console.print("[yellow]No scheduled jobs.[/yellow]")
            return

        table = Table(title="Scheduled Jobs")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Next Run")
        table.add_column("Trigger")

        for job in jobs:
            table.add_row(
                job["id"],
                job["name"],
                job["next_run"] or "-",
                job["trigger"],
            )

        console.print(table)
        return

    if not weekly and not daily and not run:
        console.print("[red]Please specify --weekly, --daily, or --list[/red]")
        raise SystemExit(1)

    # Add the scheduled job
    if weekly:
        job_id = scrape_scheduler.add_weekly_scrape(
            university=university,
            day_of_week=day,
            hour=hour,
        )
        console.print(f"[green]Added weekly scrape job:[/green] {job_id}")
        console.print(f"  Runs every {day} at {hour:02d}:00")

    if daily:
        job_id = scrape_scheduler.add_daily_scrape(
            university=university,
            hour=hour,
        )
        console.print(f"[green]Added daily scrape job:[/green] {job_id}")
        console.print(f"  Runs daily at {hour:02d}:00")

    if run:
        console.print("[bold blue]Starting scheduler...[/bold blue]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")

        scrape_scheduler.start()

        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping scheduler...[/yellow]")
            scrape_scheduler.stop()
            console.print("[green]Scheduler stopped.[/green]")


@main.command()
def init_db() -> None:
    """Initialize the database schema.

    This creates the necessary tables if they don't exist.
    For full setup, use the schema.sql file directly with psql.
    """
    try:
        console.print("[dim]Initializing database...[/dim]")
        db.init_db()
        console.print("[green]Database initialized successfully![/green]")
        console.print("\n[dim]For full schema with extensions and views, run:[/dim]")
        console.print("  psql -d your_database -f schema.sql")
    except Exception as e:
        console.print(f"[red]Error initializing database:[/red] {e}")
        raise SystemExit(1)


@main.command()
@click.option("--upgrade", is_flag=True, help="Upgrade to the latest revision")
@click.option("--downgrade", type=str, help="Downgrade to a specific revision (or -1 for previous)")
@click.option("--revision", type=str, help="Target revision for upgrade/downgrade")
@click.option("--current", is_flag=True, help="Show current revision")
@click.option("--history", is_flag=True, help="Show migration history")
def migrate(
    upgrade: bool,
    downgrade: Optional[str],
    revision: Optional[str],
    current: bool,
    history: bool,
) -> None:
    """Run database migrations with Alembic.

    Examples:
        tech-scraper migrate --upgrade
        tech-scraper migrate --downgrade -1
        tech-scraper migrate --current
        tech-scraper migrate --history
    """
    from alembic.config import Config
    from alembic import command
    import os

    # Find alembic.ini relative to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini = os.path.join(project_root, "alembic.ini")

    if not os.path.exists(alembic_ini):
        console.print(f"[red]alembic.ini not found at {alembic_ini}[/red]")
        raise SystemExit(1)

    alembic_cfg = Config(alembic_ini)

    try:
        if current:
            console.print("[bold]Current revision:[/bold]")
            command.current(alembic_cfg, verbose=True)
            return

        if history:
            console.print("[bold]Migration history:[/bold]")
            command.history(alembic_cfg, verbose=True)
            return

        if upgrade:
            target = revision or "head"
            console.print(f"[dim]Upgrading database to {target}...[/dim]")
            command.upgrade(alembic_cfg, target)
            console.print("[green]Database upgraded successfully![/green]")
            return

        if downgrade:
            target = downgrade
            console.print(f"[dim]Downgrading database to {target}...[/dim]")
            command.downgrade(alembic_cfg, target)
            console.print("[green]Database downgraded successfully![/green]")
            return

        console.print("[yellow]Please specify an action: --upgrade, --downgrade, --current, or --history[/yellow]")

    except Exception as e:
        console.print(f"[red]Migration error:[/red] {e}")
        raise SystemExit(1)


@main.command()
@click.argument("tech_id", type=int)
def show(tech_id: int) -> None:
    """Show details for a specific technology by ID.

    Example:
        tech-scraper show 123
    """
    tech = db.get_technology_by_id(tech_id)

    if not tech:
        console.print(f"[red]Technology with ID {tech_id} not found.[/red]")
        raise SystemExit(1)

    console.print(f"\n[bold cyan]{tech.title}[/bold cyan]")
    console.print(f"[dim]University:[/dim] {tech.university}")
    console.print(f"[dim]Tech ID:[/dim] {tech.tech_id}")
    console.print(f"[dim]URL:[/dim] {tech.url}")

    if tech.top_field:
        console.print(f"[dim]Field:[/dim] {tech.top_field}")
    if tech.subfield:
        console.print(f"[dim]Subfield:[/dim] {tech.subfield}")
    if tech.keywords:
        console.print(f"[dim]Keywords:[/dim] {', '.join(tech.keywords)}")

    console.print(f"\n[bold]Description:[/bold]")
    console.print(tech.description or "No description available.")


@main.command()
@click.option("--host", "-h", type=str, default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", type=int, default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the web dashboard API server.

    Examples:
        tech-scraper serve
        tech-scraper serve --port 8080
        tech-scraper serve --reload
        tech-scraper serve --host 0.0.0.0 --port 8000
    """
    import uvicorn

    console.print(f"\n[bold blue]Starting Tech Transfer Dashboard API[/bold blue]")
    console.print(f"[dim]Server:[/dim] http://{host}:{port}")
    console.print(f"[dim]API docs:[/dim] http://{host}:{port}/docs")
    console.print(f"[dim]Reload:[/dim] {'enabled' if reload else 'disabled'}")
    console.print()

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
