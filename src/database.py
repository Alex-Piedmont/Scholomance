"""Database models and operations for the tech transfer scraper."""

from datetime import datetime, timezone
from typing import Any, Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    DECIMAL,
    ForeignKey,
    func,
    or_,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    Session,
    relationship,
)
from sqlalchemy.sql import text
from loguru import logger

from .config import settings
from .scrapers.base import Technology as TechnologyData


Base = declarative_base()


class Technology(Base):
    """SQLAlchemy model for technologies table."""

    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, server_default=text("uuid_generate_v4()"))

    # Core identifiers
    university = Column(String(100), nullable=False)
    tech_id = Column(String(200), nullable=False)

    # Basic information
    title = Column(Text, nullable=False)
    description = Column(Text)
    url = Column(Text, nullable=False)

    # Temporal tracking
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    first_seen = Column(DateTime(timezone=True), server_default=func.now())

    # Raw data from source
    raw_data = Column(JSONB)

    # Derived/classified fields
    top_field = Column(String(100))
    subfield = Column(String(100))
    patent_geography = Column(ARRAY(Text))
    keywords = Column(ARRAY(Text))

    # Status tracking
    classification_status = Column(String(50), default="pending")
    classification_confidence = Column(DECIMAL(3, 2))
    last_classified_at = Column(DateTime(timezone=True))

    # Unique constraint
    __table_args__ = (
        Index("idx_technologies_university", "university"),
        Index("idx_technologies_top_field", "top_field"),
        Index("idx_technologies_subfield", "subfield"),
        Index("idx_technologies_scraped_at", "scraped_at"),
        Index("idx_technologies_classification_status", "classification_status"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<Technology(id={self.id}, university={self.university}, tech_id={self.tech_id})>"


class University(Base):
    """SQLAlchemy model for universities table."""

    __tablename__ = "universities"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    base_url = Column(Text, nullable=False)
    scraper_config = Column(JSONB)
    last_scraped = Column(DateTime(timezone=True))
    total_technologies = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<University(code={self.code}, name={self.name})>"


class ScrapeLog(Base):
    """SQLAlchemy model for scrape_logs table."""

    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True)
    university = Column(String(100), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(50))
    technologies_found = Column(Integer, default=0)
    technologies_new = Column(Integer, default=0)
    technologies_updated = Column(Integer, default=0)
    error_message = Column(Text)
    metadata_ = Column("metadata", JSONB)

    def __repr__(self):
        return f"<ScrapeLog(id={self.id}, university={self.university}, status={self.status})>"


class ClassificationLog(Base):
    """SQLAlchemy model for classification_logs table."""

    __tablename__ = "classification_logs"

    id = Column(Integer, primary_key=True)
    technology_id = Column(Integer, ForeignKey("technologies.id", ondelete="CASCADE"))
    classified_at = Column(DateTime(timezone=True), server_default=func.now())
    model = Column(String(100))
    top_field = Column(String(100))
    subfield = Column(String(100))
    confidence = Column(DECIMAL(3, 2))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_cost = Column(DECIMAL(10, 6))
    raw_response = Column(JSONB)

    technology = relationship("Technology", backref="classification_logs")

    def __repr__(self):
        return f"<ClassificationLog(id={self.id}, technology_id={self.technology_id})>"


class Database:
    """Database manager class for all database operations."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.get_database_url()
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def init_db(self) -> None:
        """Initialize database tables (use schema.sql for full setup)."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def insert_technology(
        self,
        tech_data: TechnologyData,
        session: Optional[Session] = None,
    ) -> Technology:
        """
        Insert or update a technology record.

        Uses UPSERT logic: inserts new records, updates existing ones.
        """

        def _insert(s: Session) -> Technology:
            existing = (
                s.query(Technology)
                .filter(
                    Technology.university == tech_data.university,
                    Technology.tech_id == tech_data.tech_id,
                )
                .first()
            )

            if existing:
                # Update existing record
                existing.title = tech_data.title
                existing.description = tech_data.description
                existing.url = tech_data.url
                existing.raw_data = tech_data.raw_data
                existing.keywords = tech_data.keywords
                existing.updated_at = datetime.now(timezone.utc)
                logger.debug(f"Updated technology: {tech_data.tech_id}")
                return existing
            else:
                # Insert new record
                tech = Technology(
                    university=tech_data.university,
                    tech_id=tech_data.tech_id,
                    title=tech_data.title,
                    description=tech_data.description,
                    url=tech_data.url,
                    raw_data=tech_data.raw_data,
                    keywords=tech_data.keywords,
                    scraped_at=tech_data.scraped_at,
                )
                s.add(tech)
                s.flush()
                logger.debug(f"Inserted new technology: {tech_data.tech_id}")
                return tech

        if session:
            return _insert(session)
        else:
            with self.get_session() as s:
                result = _insert(s)
                s.commit()
                return result

    def bulk_insert_technologies(
        self,
        technologies: list[TechnologyData],
        session: Optional[Session] = None,
    ) -> tuple[int, int]:
        """
        Bulk insert/update technologies.

        Returns:
            Tuple of (new_count, updated_count)
        """

        def _bulk_insert(s: Session) -> tuple[int, int]:
            new_count = 0
            updated_count = 0

            for tech_data in technologies:
                existing = (
                    s.query(Technology)
                    .filter(
                        Technology.university == tech_data.university,
                        Technology.tech_id == tech_data.tech_id,
                    )
                    .first()
                )

                if existing:
                    existing.title = tech_data.title
                    existing.description = tech_data.description
                    existing.url = tech_data.url
                    existing.raw_data = tech_data.raw_data
                    existing.keywords = tech_data.keywords
                    existing.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                else:
                    tech = Technology(
                        university=tech_data.university,
                        tech_id=tech_data.tech_id,
                        title=tech_data.title,
                        description=tech_data.description,
                        url=tech_data.url,
                        raw_data=tech_data.raw_data,
                        keywords=tech_data.keywords,
                        scraped_at=tech_data.scraped_at,
                    )
                    s.add(tech)
                    new_count += 1

            return new_count, updated_count

        if session:
            return _bulk_insert(session)
        else:
            with self.get_session() as s:
                result = _bulk_insert(s)
                s.commit()
                return result

    def search_technologies(
        self,
        keyword: Optional[str] = None,
        university: Optional[str] = None,
        top_field: Optional[str] = None,
        subfield: Optional[str] = None,
        patent_geography: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Technology]:
        """
        Search technologies with filters.

        Args:
            keyword: Search in title and description
            university: Filter by university code
            top_field: Filter by top field classification
            subfield: Filter by subfield classification
            patent_geography: Filter by patent geography (contains)
            from_date: Filter by scraped_at >= from_date
            to_date: Filter by scraped_at <= to_date
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of matching Technology objects
        """
        with self.get_session() as session:
            query = session.query(Technology)

            if university:
                query = query.filter(Technology.university == university)

            if top_field:
                query = query.filter(Technology.top_field == top_field)

            if subfield:
                query = query.filter(Technology.subfield == subfield)

            if patent_geography:
                # Filter by patent geography array contains
                query = query.filter(Technology.patent_geography.any(patent_geography))

            if from_date:
                query = query.filter(Technology.scraped_at >= from_date)

            if to_date:
                query = query.filter(Technology.scraped_at <= to_date)

            if keyword:
                # Case-insensitive search in title and description
                search_pattern = f"%{keyword}%"
                query = query.filter(
                    or_(
                        Technology.title.ilike(search_pattern),
                        Technology.description.ilike(search_pattern),
                    )
                )

            query = query.order_by(Technology.scraped_at.desc())
            query = query.offset(offset).limit(limit)

            # Detach results from session
            results = query.all()
            return results

    def get_technology_by_id(self, tech_id: int) -> Optional[Technology]:
        """Get a technology by its database ID."""
        with self.get_session() as session:
            return session.query(Technology).filter(Technology.id == tech_id).first()

    def get_technology_by_tech_id(
        self, university: str, tech_id: str
    ) -> Optional[Technology]:
        """Get a technology by university and tech_id."""
        with self.get_session() as session:
            return (
                session.query(Technology)
                .filter(
                    Technology.university == university,
                    Technology.tech_id == tech_id,
                )
                .first()
            )

    def count_technologies(self, university: Optional[str] = None) -> int:
        """Count technologies, optionally filtered by university."""
        with self.get_session() as session:
            query = session.query(func.count(Technology.id))
            if university:
                query = query.filter(Technology.university == university)
            return query.scalar() or 0

    def get_universities(self) -> list[University]:
        """Get all configured universities."""
        with self.get_session() as session:
            return session.query(University).filter(University.active == True).all()

    def get_university(self, code: str) -> Optional[University]:
        """Get a university by its code."""
        with self.get_session() as session:
            return session.query(University).filter(University.code == code).first()

    def create_scrape_log(
        self,
        university: str,
        status: str = "running",
    ) -> ScrapeLog:
        """Create a new scrape log entry."""
        with self.get_session() as session:
            log = ScrapeLog(
                university=university,
                status=status,
            )
            session.add(log)
            session.flush()
            return log

    def update_scrape_log(
        self,
        log_id: int,
        status: str,
        technologies_found: int = 0,
        technologies_new: int = 0,
        technologies_updated: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """Update a scrape log entry."""
        with self.get_session() as session:
            log = session.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
            if log:
                log.status = status
                log.completed_at = datetime.now(timezone.utc)
                log.technologies_found = technologies_found
                log.technologies_new = technologies_new
                log.technologies_updated = technologies_updated
                log.error_message = error_message

    def get_unclassified_technologies(
        self,
        university: Optional[str] = None,
        limit: int = 100,
    ) -> list[Technology]:
        """Get technologies that haven't been classified yet."""
        with self.get_session() as session:
            query = session.query(Technology).filter(
                Technology.classification_status == "pending"
            )

            if university:
                query = query.filter(Technology.university == university)

            query = query.order_by(Technology.scraped_at.desc())
            query = query.limit(limit)

            return query.all()

    def get_technologies_for_classification(
        self,
        university: Optional[str] = None,
        force: bool = False,
        limit: int = 100,
    ) -> list[Technology]:
        """
        Get technologies for classification.

        Args:
            university: Filter by university
            force: If True, include already classified technologies
            limit: Maximum number to return
        """
        with self.get_session() as session:
            query = session.query(Technology)

            if university:
                query = query.filter(Technology.university == university)

            if not force:
                query = query.filter(Technology.classification_status == "pending")

            query = query.order_by(Technology.scraped_at.desc())
            query = query.limit(limit)

            return query.all()

    def update_technology_classification(
        self,
        tech_id: int,
        top_field: str,
        subfield: str,
        confidence: float,
        model: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_cost: float = 0.0,
        raw_response: Optional[dict] = None,
    ) -> bool:
        """
        Update classification for a technology.

        Returns True if successful.
        """
        with self.get_session() as session:
            tech = session.query(Technology).filter(Technology.id == tech_id).first()
            if not tech:
                return False

            # Update technology
            tech.top_field = top_field
            tech.subfield = subfield
            tech.classification_status = "completed"
            tech.classification_confidence = confidence
            tech.last_classified_at = datetime.now(timezone.utc)

            # Create classification log
            log = ClassificationLog(
                technology_id=tech_id,
                model=model,
                top_field=top_field,
                subfield=subfield,
                confidence=confidence,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_cost=total_cost,
                raw_response=raw_response,
            )
            session.add(log)

            return True

    def mark_classification_failed(
        self,
        tech_id: int,
        error_message: str,
    ) -> bool:
        """Mark a technology classification as failed."""
        with self.get_session() as session:
            tech = session.query(Technology).filter(Technology.id == tech_id).first()
            if not tech:
                return False

            tech.classification_status = "failed"
            return True

    def count_unclassified(self, university: Optional[str] = None) -> int:
        """Count unclassified technologies."""
        with self.get_session() as session:
            query = session.query(func.count(Technology.id)).filter(
                Technology.classification_status == "pending"
            )
            if university:
                query = query.filter(Technology.university == university)
            return query.scalar() or 0

    def count_classified(self, university: Optional[str] = None) -> int:
        """Count classified technologies."""
        with self.get_session() as session:
            query = session.query(func.count(Technology.id)).filter(
                Technology.classification_status == "completed"
            )
            if university:
                query = query.filter(Technology.university == university)
            return query.scalar() or 0

    def get_classification_stats(self) -> dict:
        """Get classification statistics."""
        with self.get_session() as session:
            # Total cost
            total_cost = session.query(func.sum(ClassificationLog.total_cost)).scalar() or 0

            # Total classifications
            total_classifications = session.query(func.count(ClassificationLog.id)).scalar() or 0

            # By field
            field_counts = (
                session.query(Technology.top_field, func.count(Technology.id))
                .filter(Technology.classification_status == "completed")
                .group_by(Technology.top_field)
                .all()
            )

            return {
                "total_cost": float(total_cost),
                "total_classifications": total_classifications,
                "by_field": {field: count for field, count in field_counts if field},
            }


# Global database instance
db = Database()
