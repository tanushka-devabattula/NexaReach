import os
from app.db.session import SessionLocal, engine
from app.models import Role, User, AudienceMember, Segment, Campaign, Template, Message
import logging

# Simple placeholder for password hashing – in tests we don't need real hashing
def _hash_password(pwd: str) -> str:
    return f"hashed_{pwd}"

def seed_initial_data():
    """Insert minimal seed data required for tests and demo.
    This function is safe to run multiple times; it checks for existing records.
    """
    db = SessionLocal()
    try:
        # Roles
        admin_role = db.query(Role).filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator role")
            db.add(admin_role)
            db.commit()
        # Users (at least 4)
        pwd_hash = _hash_password("testpassword")
        for i in range(1, 5):
            email = f"user{i}@example.com"
            if not db.query(User).filter_by(email=email).first():
                user = User(
                    full_name=f"User {i}",
                    email=email,
                    hashed_password=pwd_hash,
                    role_id=admin_role.id,
                )
                db.add(user)
        db.commit()
        # Audience members (at least 4)
        languages = ["English", "Hindi", "Urdu", "Tamil"]
        for i, lang in enumerate(languages, start=1):
            email = f"aud{i}@example.com"
            if not db.query(AudienceMember).filter_by(email=email).first():
                member = AudienceMember(
                    full_name=f"Audience {i}",
                    email=email,
                    phone=f"1800-000-00{i}",
                    preferred_language=lang,
                )
                db.add(member)
        db.commit()
        # Segments (at least 4)
        for i in range(1, 5):
            name = f"Segment {i}"
            if not db.query(Segment).filter_by(name=name).first():
                segment = Segment(
                    name=name,
                    description=f"Test segment {i}",
                    criteria={},
                )
                db.add(segment)
        db.commit()
        # Campaigns (at least 2)
        first_user = db.query(User).first()
        for i in range(1, 3):
            name = f"Campaign {i}"
            if not db.query(Campaign).filter_by(name=name).first():
                campaign = Campaign(
                    name=name,
                    objective="Test objective",
                    status="draft",
                    created_by=first_user.id if first_user else None,
                    segment_id=1,
                )
                db.add(campaign)
        db.commit()
        # Templates (at least 2)
        for i in range(1, 3):
            name = f"Template {i}"
            if not db.query(Template).filter_by(name=name).first():
                template = Template(
                    name=name,
                    channel="SMS",
                    language="English",
                    subject=None,
                    body="Test message body",
                )
                db.add(template)
        db.commit()
        # Ensure at least one Message exists
        if db.query(Message).count() == 0:
            campaign = db.query(Campaign).first()
            audience = db.query(AudienceMember).first()
            template = db.query(Template).first()
            if campaign and audience and template:
                message = Message(
                    campaign_id=campaign.id,
                    audience_member_id=audience.id,
                    template_id=template.id,
                    channel="SMS",
                    language=audience.preferred_language,
                    content="Test message content",
                    status="pending",
                )
                db.add(message)
                db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    # Allow manual execution
    seed_initial_data()

