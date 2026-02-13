"""Pydantic models for Y-Connect WhatsApp Bot"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


# Enums
class MessageType(str, Enum):
    """Message type enumeration"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    TEMPLATE = "template"


class MessageRole(str, Enum):
    """Message role in conversation"""
    USER = "user"
    ASSISTANT = "assistant"


class IntentType(str, Enum):
    """Query intent types"""
    SEARCH_SCHEMES = "search_schemes"
    GET_DETAILS = "get_details"
    HELP = "help"
    FEEDBACK = "feedback"
    CATEGORY_BROWSE = "category_browse"
    UNKNOWN = "unknown"


# Message Models
class IncomingMessage(BaseModel):
    """Model for incoming WhatsApp messages"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    message_id: str = Field(..., description="Unique message identifier from WhatsApp")
    from_phone: str = Field(..., description="Sender's phone number in international format")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    text_content: str = Field(default="", description="Text content of the message")
    media_url: Optional[str] = Field(None, description="URL for media content if applicable")
    
    @field_validator("from_phone")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format (international format with +)"""
        # Remove any whitespace
        v = v.strip()
        
        # Check if it starts with + and contains only digits after that
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError(
                "Phone number must be in international format: +[country_code][number] "
                "(10-15 digits total)"
            )
        return v
    
    @field_validator("text_content")
    @classmethod
    def validate_text_content(cls, v: str, info) -> str:
        """Ensure text content is present for text messages"""
        message_type = info.data.get("message_type")
        if message_type == MessageType.TEXT and not v.strip():
            raise ValueError("Text content cannot be empty for text messages")
        return v


class OutgoingMessage(BaseModel):
    """Model for outgoing WhatsApp messages"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    to_phone: str = Field(..., description="Recipient's phone number in international format")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    text_content: str = Field(..., description="Text content to send")
    reply_to_message_id: Optional[str] = Field(None, description="Message ID to reply to")
    
    @field_validator("to_phone")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format (international format with +)"""
        v = v.strip()
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError(
                "Phone number must be in international format: +[country_code][number] "
                "(10-15 digits total)"
            )
        return v
    
    @field_validator("text_content")
    @classmethod
    def validate_text_length(cls, v: str) -> str:
        """Validate text content is not empty and within reasonable limits"""
        if not v.strip():
            raise ValueError("Text content cannot be empty")
        if len(v) > 4096:  # WhatsApp limit
            raise ValueError("Text content exceeds WhatsApp maximum length of 4096 characters")
        return v


class Message(BaseModel):
    """Model for conversation messages"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    language: str = Field(default="en", description="Language code of the message")
    
    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code format (ISO 639-1)"""
        v = v.lower().strip()
        # Supported languages: hi, en, ta, te, bn, mr, gu, kn, ml, pa
        supported_languages = {"hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"}
        if v not in supported_languages:
            raise ValueError(
                f"Language code must be one of: {', '.join(sorted(supported_languages))}"
            )
        return v


# Language Detection Models
class LanguageResult(BaseModel):
    """Model for language detection results"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    language_code: str = Field(..., description="ISO 639-1 language code")
    language_name: str = Field(..., description="Full language name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    
    @field_validator("language_code")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code format"""
        v = v.lower().strip()
        if not re.match(r'^[a-z]{2}$', v):
            raise ValueError("Language code must be a 2-letter ISO 639-1 code")
        return v
    
    @field_validator("language_name")
    @classmethod
    def validate_language_name(cls, v: str) -> str:
        """Ensure language name is not empty"""
        if not v.strip():
            raise ValueError("Language name cannot be empty")
        return v.strip()


# Session Models
class UserSession(BaseModel):
    """Model for user conversation sessions"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    session_id: str = Field(..., description="Unique session identifier")
    phone_number: str = Field(..., description="User's phone number")
    language: str = Field(default="en", description="User's preferred language")
    conversation_history: List[Message] = Field(
        default_factory=list,
        description="List of messages in the conversation"
    )
    user_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted user context (age, location, occupation, etc.)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    last_active: datetime = Field(default_factory=datetime.utcnow, description="Last activity time")
    is_new_user: bool = Field(default=True, description="Whether this is a new user")
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format"""
        v = v.strip()
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError(
                "Phone number must be in international format: +[country_code][number]"
            )
        return v
    
    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code"""
        v = v.lower().strip()
        supported_languages = {"hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"}
        if v not in supported_languages:
            raise ValueError(
                f"Language code must be one of: {', '.join(sorted(supported_languages))}"
            )
        return v
    
    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Ensure session ID is not empty"""
        if not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()
    
    def add_message(self, message: Message) -> None:
        """Add a message to conversation history"""
        self.conversation_history.append(message)
        self.last_active = datetime.utcnow()
    
    def update_context(self, context_updates: Dict[str, Any]) -> None:
        """Update user context with new information"""
        self.user_context.update(context_updates)
        self.last_active = datetime.utcnow()
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get the most recent messages from conversation history"""
        return self.conversation_history[-count:] if self.conversation_history else []



# Scheme Models
class SchemeStatus(str, Enum):
    """Scheme status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    UPCOMING = "upcoming"


class SchemeCategory(str, Enum):
    """Scheme category enumeration"""
    AGRICULTURE = "agriculture"
    EDUCATION = "education"
    HEALTH = "health"
    HOUSING = "housing"
    WOMEN = "women"
    SENIOR_CITIZENS = "senior_citizens"
    EMPLOYMENT = "employment"
    FINANCIAL_INCLUSION = "financial_inclusion"
    SOCIAL_WELFARE = "social_welfare"
    SKILL_DEVELOPMENT = "skill_development"
    OTHER = "other"


class SchemeAuthority(str, Enum):
    """Scheme authority enumeration"""
    CENTRAL = "central"
    STATE = "state"


class Scheme(BaseModel):
    """Model for government schemes"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    scheme_id: str = Field(..., description="Unique scheme identifier")
    scheme_name: str = Field(..., description="Scheme name in English")
    scheme_name_translations: Dict[str, str] = Field(
        default_factory=dict,
        description="Scheme name translations {lang_code: translated_name}"
    )
    description: str = Field(..., description="Scheme description in English")
    description_translations: Dict[str, str] = Field(
        default_factory=dict,
        description="Description translations {lang_code: translated_description}"
    )
    category: SchemeCategory = Field(..., description="Scheme category")
    authority: SchemeAuthority = Field(..., description="Governing authority")
    applicable_states: List[str] = Field(
        default_factory=list,
        description="List of applicable state codes or ['ALL'] for all India"
    )
    eligibility_criteria: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured eligibility criteria"
    )
    benefits: str = Field(..., description="Scheme benefits in English")
    benefits_translations: Dict[str, str] = Field(
        default_factory=dict,
        description="Benefits translations {lang_code: translated_benefits}"
    )
    application_process: str = Field(..., description="Application process in English")
    application_process_translations: Dict[str, str] = Field(
        default_factory=dict,
        description="Application process translations {lang_code: translated_process}"
    )
    official_url: str = Field(..., description="Official scheme website URL")
    helpline_numbers: List[str] = Field(
        default_factory=list,
        description="List of helpline phone numbers"
    )
    status: SchemeStatus = Field(default=SchemeStatus.ACTIVE, description="Current scheme status")
    start_date: Optional[datetime] = Field(None, description="Scheme start date")
    end_date: Optional[datetime] = Field(None, description="Scheme end date")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    @field_validator("scheme_id")
    @classmethod
    def validate_scheme_id(cls, v: str) -> str:
        """Ensure scheme ID is not empty"""
        if not v.strip():
            raise ValueError("Scheme ID cannot be empty")
        return v.strip()
    
    @field_validator("scheme_name", "description", "benefits", "application_process")
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        """Ensure required text fields are not empty"""
        if not v.strip():
            raise ValueError("Required text field cannot be empty")
        return v.strip()
    
    @field_validator("official_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        v = v.strip()
        if not re.match(r'^https?://', v):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @field_validator("applicable_states")
    @classmethod
    def validate_states(cls, v: List[str]) -> List[str]:
        """Ensure at least one state is specified"""
        if not v:
            raise ValueError("At least one applicable state must be specified")
        return [state.strip().upper() for state in v]
    
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure end date is after start date if both are provided"""
        if v is not None:
            start_date = info.data.get("start_date")
            if start_date is not None and v <= start_date:
                raise ValueError("End date must be after start date")
        return v
    
    def get_translation(self, field: str, language: str) -> str:
        """Get translated field value or fall back to English"""
        translation_field = f"{field}_translations"
        if hasattr(self, translation_field):
            translations = getattr(self, translation_field)
            return translations.get(language, getattr(self, field))
        return getattr(self, field, "")


class SchemeDocument(BaseModel):
    """Model for scheme documents used in RAG retrieval"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    document_id: str = Field(..., description="Unique document identifier")
    scheme_id: str = Field(..., description="Associated scheme ID")
    scheme: Scheme = Field(..., description="Full scheme object")
    language: str = Field(default="en", description="Document language")
    content: str = Field(..., description="Document text content")
    document_type: str = Field(
        default="overview",
        description="Document type: overview, eligibility, benefits, application"
    )
    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Similarity score from vector search"
    )
    
    @field_validator("document_id", "scheme_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Ensure IDs are not empty"""
        if not v.strip():
            raise ValueError("ID cannot be empty")
        return v.strip()
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not empty"""
        if not v.strip():
            raise ValueError("Document content cannot be empty")
        return v.strip()
    
    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code"""
        v = v.lower().strip()
        supported_languages = {"hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"}
        if v not in supported_languages:
            raise ValueError(
                f"Language code must be one of: {', '.join(sorted(supported_languages))}"
            )
        return v
    
    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        """Validate document type"""
        v = v.lower().strip()
        valid_types = {"overview", "eligibility", "benefits", "application"}
        if v not in valid_types:
            raise ValueError(
                f"Document type must be one of: {', '.join(sorted(valid_types))}"
            )
        return v


# Query Processing Models
class ProcessedQuery(BaseModel):
    """Model for processed user queries"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    original_text: str = Field(..., description="Original query text")
    language: str = Field(default="en", description="Detected language code")
    intent: IntentType = Field(default=IntentType.UNKNOWN, description="Detected intent")
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities (age, location, occupation, income, category, gender)"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether query needs clarification"
    )
    clarification_questions: List[str] = Field(
        default_factory=list,
        description="List of clarification questions to ask user"
    )
    search_vector: List[float] = Field(
        default_factory=list,
        description="Embedding vector for semantic search"
    )
    
    @field_validator("original_text")
    @classmethod
    def validate_original_text(cls, v: str) -> str:
        """Ensure original text is not empty"""
        if not v.strip():
            raise ValueError("Original text cannot be empty")
        return v.strip()
    
    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code"""
        v = v.lower().strip()
        supported_languages = {"hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"}
        if v not in supported_languages:
            raise ValueError(
                f"Language code must be one of: {', '.join(sorted(supported_languages))}"
            )
        return v
    
    @field_validator("search_vector")
    @classmethod
    def validate_search_vector(cls, v: List[float]) -> List[float]:
        """Validate search vector dimensions if present"""
        if v and len(v) not in [384, 768, 1024]:  # Common embedding dimensions
            raise ValueError(
                "Search vector must be empty or have standard embedding dimensions "
                "(384, 768, or 1024)"
            )
        return v
    
    def add_entity(self, entity_type: str, entity_value: Any) -> None:
        """Add an extracted entity to the query"""
        self.entities[entity_type] = entity_value
    
    def has_entity(self, entity_type: str) -> bool:
        """Check if a specific entity type was extracted"""
        return entity_type in self.entities
    
    def get_entity(self, entity_type: str, default: Any = None) -> Any:
        """Get an entity value with optional default"""
        return self.entities.get(entity_type, default)
