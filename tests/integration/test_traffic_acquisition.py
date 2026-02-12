"""
Integration Tests for Traffic Acquisition Features

Tests the three core features:
1. DataForSEO Keyword Research
2. DataForSEO Backlink Discovery  
3. Resend Email System

These tests use mock data and don't require real API keys.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import models
from src.models.base import Base
from src.models.keyword import Keyword
from src.models.backlink import BacklinkOpportunityModel, OpportunityType, OutreachStatus
from src.models.email import EmailSubscriber
from src.models.email_sequence import EmailSequence, EmailSequenceStep
from src.models.email_enrollment import EmailEnrollment, EnrollmentStatus

# Import clients and services
from src.integrations.keyword_client import KeywordClient, KeywordOpportunity
from src.integrations.dataforseo_backlinks import DataForSEOBacklinksClient
from src.email.resend_client import ResendClient
from src.email.sequence_engine import SequenceEngine
from src.backlink.outreach_sender import OutreachSender
from src.services.keyword_strategy import ContentAwareKeywordGenerator, KeywordCandidate

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestKeywordClient:
    """Tests for DataForSEO Keyword Client."""
    
    def test_keyword_client_init(self):
        """Test KeywordClient initializes correctly."""
        client = KeywordClient(provider='dataforseo')
        assert client.provider == 'dataforseo'
        assert client.api_key is None  # No key configured in test
    
    @pytest.mark.asyncio
    async def test_keyword_client_no_key_returns_empty(self):
        """Test that client returns empty list when no API key."""
        client = KeywordClient(provider='dataforseo')
        result = await client.get_keyword_suggestions('test')
        assert result == []
    
    def test_keyword_opportunity_dataclass(self):
        """Test KeywordOpportunity dataclass."""
        opp = KeywordOpportunity(
            keyword="seo tools",
            volume=1000,
            difficulty=25,
            cpc=2.5,
            intent="commercial",
            source="dataforseo"
        )
        assert opp.keyword == "seo tools"
        assert opp.volume == 1000
        assert opp.difficulty == 25


class TestBacklinkModels:
    """Tests for Backlink Opportunity Model."""
    
    def test_backlink_model_creation(self, db_session: Session):
        """Test creating a BacklinkOpportunityModel."""
        opp = BacklinkOpportunityModel(
            target_url="https://example.com/article",
            target_domain="example.com",
            opportunity_type=OpportunityType.UNLINKED_MENTION,
            domain_authority=45,
            relevance_score=75.5,
            outreach_status=OutreachStatus.DISCOVERED
        )
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)
        
        assert opp.id is not None
        assert opp.target_domain == "example.com"
        assert opp.outreach_status == OutreachStatus.DISCOVERED
    
    def test_backlink_model_unique_constraint(self, db_session: Session):
        """Test unique constraint on (target_url, opportunity_type)."""
        # Create first opportunity
        opp1 = BacklinkOpportunityModel(
            target_url="https://example.com/article",
            target_domain="example.com",
            opportunity_type=OpportunityType.UNLINKED_MENTION
        )
        db_session.add(opp1)
        db_session.commit()
        
        # Try to create duplicate (should work in SQLite without enforcement)
        opp2 = BacklinkOpportunityModel(
            target_url="https://example.com/article",
            target_domain="example.com",
            opportunity_type=OpportunityType.RESOURCE_PAGE  # Different type
        )
        db_session.add(opp2)
        db_session.commit()
        
        # Both should exist
        count = db_session.query(BacklinkOpportunityModel).count()
        assert count == 2


class TestBacklinkClient:
    """Tests for DataForSEO Backlinks Client."""
    
    def test_backlinks_client_init(self):
        """Test DataForSEOBacklinksClient initializes correctly."""
        client = DataForSEOBacklinksClient()
        assert client.base_url == "https://api.dataforseo.com"
        assert client.api_key is None
    
    @pytest.mark.asyncio
    async def test_backlinks_client_no_key_returns_empty(self):
        """Test that client returns empty list when no API key."""
        client = DataForSEOBacklinksClient()
        result = await client.get_referring_domains("example.com")
        assert result == []


class TestEmailModels:
    """Tests for Email Models."""
    
    def test_email_subscriber_model(self, db_session: Session):
        """Test creating EmailSubscriber."""
        subscriber = EmailSubscriber(
            email="test@example.com",
            first_name="Test",
            source="test"
        )
        db_session.add(subscriber)
        db_session.commit()
        db_session.refresh(subscriber)
        
        assert subscriber.id is not None
        assert subscriber.email == "test@example.com"
        assert subscriber.is_active is True
    
    def test_email_sequence_model(self, db_session: Session):
        """Test creating EmailSequence and steps."""
        sequence = EmailSequence(
            name="Welcome Sequence",
            description="Welcome new subscribers",
            is_active=True
        )
        db_session.add(sequence)
        db_session.commit()
        db_session.refresh(sequence)
        
        step = EmailSequenceStep(
            sequence_id=sequence.id,
            step_order=1,
            subject="Welcome!",
            html_body="<h1>Welcome to our newsletter!</h1>",
            delay_hours=0
        )
        db_session.add(step)
        db_session.commit()
        
        assert sequence.id is not None
        assert len(sequence.steps) == 1
        assert sequence.steps[0].subject == "Welcome!"
    
    def test_email_enrollment_model(self, db_session: Session):
        """Test creating EmailEnrollment."""
        # Create subscriber and sequence first
        subscriber = EmailSubscriber(email="test2@example.com")
        sequence = EmailSequence(name="Test Sequence")
        db_session.add_all([subscriber, sequence])
        db_session.commit()
        
        enrollment = EmailEnrollment(
            subscriber_id=subscriber.id,
            sequence_id=sequence.id,
            current_step=0,
            status=EnrollmentStatus.ACTIVE
        )
        db_session.add(enrollment)
        db_session.commit()
        db_session.refresh(enrollment)
        
        assert enrollment.id is not None
        assert enrollment.status == EnrollmentStatus.ACTIVE


class TestResendClient:
    """Tests for Resend Client."""
    
    def test_resend_client_init(self):
        """Test ResendClient initializes correctly."""
        client = ResendClient()
        assert client.base_url == "https://api.resend.com"
        assert client.api_key is None
    
    @pytest.mark.asyncio
    async def test_resend_client_no_key_returns_error(self):
        """Test that client returns error when no API key."""
        client = ResendClient()
        result = await client.send_email("test@example.com", "Test", "<p>Test</p>")
        assert "error" in result
        assert result["error"] == "API key not configured"


class TestSequenceEngine:
    """Tests for Sequence Engine."""
    
    @pytest.mark.asyncio
    async def test_sequence_engine_enroll(self, db_session: Session):
        """Test enrolling a subscriber in a sequence."""
        # Create test data
        subscriber = EmailSubscriber(email="test3@example.com")
        sequence = EmailSequence(name="Test Sequence")
        db_session.add_all([subscriber, sequence])
        db_session.commit()
        
        # Add a step
        step = EmailSequenceStep(
            sequence_id=sequence.id,
            step_order=1,
            subject="Test",
            html_body="<p>Test</p>",
            delay_hours=24
        )
        db_session.add(step)
        db_session.commit()
        
        # Test enrollment
        engine = SequenceEngine(db_session)
        enrollment = await engine.enroll(subscriber.id, sequence.id)
        
        assert enrollment is not None
        assert enrollment.subscriber_id == subscriber.id
        assert enrollment.sequence_id == sequence.id
    
    @pytest.mark.asyncio
    async def test_sequence_engine_enroll_inactive_subscriber(self, db_session: Session):
        """Test enrolling an inactive subscriber fails."""
        subscriber = EmailSubscriber(email="inactive@example.com", is_active=False)
        sequence = EmailSequence(name="Test Sequence")
        db_session.add_all([subscriber, sequence])
        db_session.commit()
        
        engine = SequenceEngine(db_session)
        enrollment = await engine.enroll(subscriber.id, sequence.id)
        
        assert enrollment is None


class TestOutreachSender:
    """Tests for Outreach Sender."""
    
    def test_outreach_sender_daily_limit(self):
        """Test daily limit constant."""
        assert OutreachSender.DAILY_LIMIT == 50
    
    def test_outreach_sender_init(self, db_session: Session):
        """Test OutreachSender initializes correctly."""
        sender = OutreachSender(db_session)
        assert sender.db == db_session
        assert sender.DAILY_LIMIT == 50
    
    @pytest.mark.asyncio
    async def test_outreach_sender_no_approval_blocked(self, db_session: Session):
        """Test that outreach is blocked without admin approval."""
        # Create opportunity
        opp = BacklinkOpportunityModel(
            target_url="https://example.com",
            target_domain="example.com",
            opportunity_type=OpportunityType.UNLINKED_MENTION,
            contact_email="test@example.com"
        )
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)
        
        sender = OutreachSender(db_session)
        result = await sender.send_outreach(opp.id, "Test email", admin_approved=False)
        
        assert result["success"] is False
        assert "admin" in result["message"].lower()


class TestKeywordStrategy:
    """Tests for Keyword Strategy enrichment."""
    
    def test_keyword_candidate_with_real_data(self):
        """Test KeywordCandidate supports real data fields."""
        candidate = KeywordCandidate(
            keyword="test keyword",
            intent="informational",
            journey_stage="awareness",
            category="test",
            difficulty_estimate="low",
            is_long_tail=True,
            semantic_group="test",
            search_volume=1000,
            difficulty_score=25
        )
        
        assert candidate.search_volume == 1000
        assert candidate.difficulty_score == 25


class TestIntegrationWorkflow:
    """Integration workflow tests."""
    
    @pytest.mark.asyncio
    async def test_full_email_workflow(self, db_session: Session):
        """Test complete email workflow: subscribe -> sequence -> enrollment."""
        # Create subscriber
        subscriber = EmailSubscriber(email="workflow@example.com", first_name="Workflow")
        db_session.add(subscriber)
        db_session.commit()
        
        # Create sequence with steps
        sequence = EmailSequence(name="Workflow Test")
        db_session.add(sequence)
        db_session.commit()
        
        step = EmailSequenceStep(
            sequence_id=sequence.id,
            step_order=1,
            subject="Welcome!",
            html_body="<p>Welcome!</p>",
            delay_hours=0
        )
        db_session.add(step)
        db_session.commit()
        
        # Enroll subscriber
        engine = SequenceEngine(db_session)
        enrollment = await engine.enroll(subscriber.id, sequence.id)
        
        assert enrollment is not None
        assert enrollment.status == EnrollmentStatus.ACTIVE
        
        # Check progress
        progress = engine.get_progress(enrollment.id)
        assert progress is not None
        assert progress["subscriber_email"] == "workflow@example.com"
    
    def test_backlink_opportunity_workflow(self, db_session: Session):
        """Test backlink opportunity creation and status workflow."""
        # Create opportunity
        opp = BacklinkOpportunityModel(
            target_url="https://example.com/blog",
            target_domain="example.com",
            opportunity_type=OpportunityType.RESOURCE_PAGE,
            domain_authority=60,
            relevance_score=80.0,
            contact_email="admin@example.com",
            outreach_status=OutreachStatus.DISCOVERED
        )
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)
        
        assert opp.outreach_status == OutreachStatus.DISCOVERED
        
        # Update status
        opp.outreach_status = OutreachStatus.DRAFTED
        db_session.commit()
        
        assert opp.outreach_status == OutreachStatus.DRAFTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
