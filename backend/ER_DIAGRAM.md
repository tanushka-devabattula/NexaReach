
# NexaReach — Entity Relationship Diagram

**Project:** AI-Powered Multilingual Public Awareness and Mass Communication Platform

## Database Entities and Relationships

```mermaid
erDiagram
    ROLES ||--o{ USERS : assigns
    USERS ||--o{ CAMPAIGNS : creates
    USERS ||--o{ TEMPLATES : creates
    SEGMENTS ||--o{ CAMPAIGNS : targets
    CAMPAIGNS ||--o{ MESSAGES : contains
    AUDIENCE_MEMBERS ||--o{ MESSAGES : receives
    TEMPLATES ||--o{ MESSAGES : formats
    MESSAGES ||--o{ DELIVERY_LOGS : tracks
    MESSAGES ||--o{ FEEDBACK : receives
    AUDIENCE_MEMBERS ||--o{ FEEDBACK : submits

    ROLES {
        int id PK
        string name
        string description
    }

    USERS {
        int id PK
        string full_name
        string email
        string hashed_password
        int role_id FK
        boolean is_active
        datetime created_at
    }

    AUDIENCE_MEMBERS {
        int id PK
        string full_name
        string email
        string phone
        string preferred_language
        datetime created_at
    }

    SEGMENTS {
        int id PK
        string name
        string description
        json criteria
        datetime created_at
    }

    CAMPAIGNS {
        int id PK
        string name
        string objective
        string status
        int created_by FK
        int segment_id FK
        datetime created_at
    }

    TEMPLATES {
        int id PK
        string name
        string channel
        string language
        string subject
        text body
        int created_by FK
        datetime created_at
    }

    MESSAGES {
        int id PK
        int campaign_id FK
        int audience_member_id FK
        int template_id FK
        string channel
        string language
        text content
        string status
        datetime created_at
    }

    DELIVERY_LOGS {
        int id PK
        int message_id FK
        string channel
        string status
        text provider_response
        datetime sent_at
        datetime created_at
    }

    FEEDBACK {
        int id PK
        int message_id FK
        int audience_member_id FK
        int rating
        text comment
        string sentiment
        datetime created_at
    }
```

## Notes

- **Roles and Users:** Each user can be assigned a role.
- **Campaigns:** Users create campaigns, and campaigns can target audience segments.
- **Templates and Messages:** Templates provide content formats for messages sent to audience members through campaigns.
- **Delivery Logs:** Track message delivery status and provider responses.
- **Feedback:** Audience members can submit feedback on messages.
- **Multilingual Support:** Templates and messages include language fields.
