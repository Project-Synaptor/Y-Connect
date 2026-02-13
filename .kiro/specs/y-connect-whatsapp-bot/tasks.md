# Implementation Plan: Y-Connect WhatsApp Bot

## Overview

This implementation plan breaks down the Y-Connect WhatsApp bot into discrete coding tasks. The system will be built using Python with FastAPI for the webhook server, Hypothesis for property-based testing, and integrations with WhatsApp Business API, vector databases, and LLM APIs.

The implementation follows a bottom-up approach: core data models → individual components → integration → testing.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create Python project with virtual environment
  - Set up FastAPI application structure
  - Configure environment variables for API keys (WhatsApp, LLM, Vector DB)
  - Create requirements.txt with dependencies: fastapi, uvicorn, pydantic, hypothesis, pytest, redis, psycopg2, httpx
  - Set up logging configuration
  - Create configuration management module for environment-specific settings
  - _Requirements: All requirements (foundational)_

- [x] 2. Implement core data models
  - [x] 2.1 Create Pydantic models for messages and sessions
    - Define IncomingMessage, OutgoingMessage, Message models
    - Define UserSession model with conversation history
    - Define LanguageResult model for language detection
    - Add validation rules for phone numbers and message types
    - _Requirements: 1.1, 1.4, 2.2_
  
  - [x] 2.2 Write property test for message models
    - **Property 20: Message Length Constraint**
    - **Validates: Requirements 6.4**
  
  - [x] 2.3 Create Pydantic models for schemes
    - Define Scheme model with all required fields
    - Define SchemeDocument model for RAG retrieval
    - Define ProcessedQuery model with intent and entities
    - Add translation field support (JSONB-like dict structure)
    - _Requirements: 5.1, 5.4, 3.1_
  
  - [x] 2.4 Write unit tests for scheme model validation
    - Test required fields validation
    - Test date field validation (start_date, end_date)
    - Test status enum validation
    - _Requirements: 5.1_

- [-] 3. Implement database layer
  - [x] 3.1 Set up PostgreSQL connection and schema
    - Create database connection pool using psycopg2
    - Implement schemes table schema with migrations
    - Implement scheme_documents table schema
    - Create indexes for category, status, and states
    - _Requirements: 5.1, 5.4, 5.5_
  
  - [x] 3.2 Implement Scheme database operations
    - Write get_scheme_by_id() function
    - Write search_schemes() with filtering support
    - Write get_scheme_translations() for localized content
    - Write update_scheme() for scheme updates
    - Write insert_scheme() for adding new schemes
    - _Requirements: 5.1, 5.3_
  
  - [ ] 3.3 Write unit tests for database operations
    - Test CRUD operations with sample schemes
    - Test filtering by category, state, status
    - Test translation retrieval
    - _Requirements: 5.1, 5.3_
  
  - [x] 3.4 Set up Redis connection for session management
    - Create Redis connection pool
    - Implement session storage with 24-hour TTL
    - Implement session retrieval and update operations
    - _Requirements: 1.4, 1.5_
  
  - [ ] 3.5 Write property test for session expiration
    - **Property 5: Session Expiration and Privacy**
    - **Validates: Requirements 1.5, 8.2**

- [x] 4. Implement Language Detector component
  - [x] 4.1 Create LanguageDetector class
    - Integrate fastText language identification model
    - Implement detect_language() method
    - Implement is_supported_language() method
    - Support 10 Indian languages: hi, en, ta, te, bn, mr, gu, kn, ml, pa
    - Handle edge cases: very short text, mixed languages
    - _Requirements: 2.1, 2.2_
  
  - [x] 4.2 Write property test for language detection accuracy
    - **Property 6: Language Detection Accuracy**
    - **Validates: Requirements 2.2**
  
  - [x] 4.3 Write unit tests for language detection edge cases
    - Test very short messages (1-3 words)
    - Test mixed language messages
    - Test unsupported languages
    - _Requirements: 2.2, 9.1_

- [x] 5. Implement Session Manager component
  - [x] 5.1 Create SessionManager class
    - Implement get_or_create_session() using Redis
    - Implement update_session() to append messages
    - Implement clear_expired_sessions() background task
    - Track is_new_user flag for welcome messages
    - Store detected language in session
    - _Requirements: 1.4, 1.5, 8.1, 8.2_
  
  - [x] 5.2 Write property test for session isolation
    - **Property 4: Session Isolation**
    - **Validates: Requirements 1.4**
  
  - [x] 5.3 Write property test for PII deletion
    - **Property 24: PII Deletion After Session Expiry**
    - **Validates: Requirements 8.1, 8.2**

- [x] 6. Implement Query Processor component
  - [x] 6.1 Create QueryProcessor class
    - Implement process_query() method
    - Implement extract_entities() using regex and NLP
    - Extract age, location, occupation, income, category, gender
    - Detect ambiguous queries and generate clarification questions
    - Maintain conversation context from session
    - _Requirements: 3.1, 3.2, 3.3, 3.5_
  
  - [x] 6.2 Write property test for entity extraction
    - **Property 8: Entity Extraction Completeness**
    - **Validates: Requirements 3.1**
  
  - [x] 6.3 Write property test for context persistence
    - **Property 12: Conversation Context Persistence**
    - **Validates: Requirements 3.5**
  
  - [x] 6.4 Write property test for spelling error robustness
    - **Property 11: Spelling Error Robustness**
    - **Validates: Requirements 3.4**
  
  - [x] 6.5 Write unit tests for ambiguity detection
    - Test queries matching multiple categories
    - Test queries with missing required information
    - _Requirements: 3.2_

- [x] 7. Implement Vector Store integration
  - [x] 7.1 Set up vector database client
    - Choose and configure vector DB (Pinecone/Weaviate/Qdrant)
    - Create VectorDocument model
    - Implement connection and authentication
    - _Requirements: 4.1, 5.2_
  
  - [x] 7.2 Implement embedding generation
    - Integrate multilingual-e5-large or sentence-transformers
    - Implement generate_embedding() for queries
    - Implement batch_generate_embeddings() for schemes
    - Handle text chunking for long documents (512 tokens, 50 overlap)
    - _Requirements: 4.1, 5.2_
  
  - [x] 7.3 Implement vector store operations
    - Implement upsert_documents() for adding/updating embeddings
    - Implement search() with metadata filtering
    - Implement delete_by_id() for removing schemes
    - Support filtering by state, category, status
    - _Requirements: 4.1, 5.2, 5.3_
  
  - [x] 7.4 Write property test for retrieval result count
    - **Property 13: Retrieval Result Count**
    - **Validates: Requirements 4.1**
  
  - [x] 7.5 Write property test for embedding update propagation
    - **Property 17: Embedding Update Propagation**
    - **Validates: Requirements 5.2, 5.3**

- [x] 8. Checkpoint - Ensure core components work independently
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement RAG Engine component
  - [x] 9.1 Create RAGEngine class
    - Implement retrieve_schemes() using vector search
    - Implement rerank_results() based on user context
    - Filter by eligibility criteria (age, location, etc.)
    - Prioritize active schemes over expired ones
    - _Requirements: 4.1, 4.3, 4.5, 3.3_
  
  - [x] 9.2 Write property test for context-aware retrieval
    - **Property 10: Context-Aware Retrieval**
    - **Validates: Requirements 3.3**
  
  - [x] 9.3 Write property test for active scheme prioritization
    - **Property 16: Active Scheme Prioritization**
    - **Validates: Requirements 4.5**
  
  - [x] 9.4 Write property test for low confidence handling
    - **Property 15: Low Confidence Handling**
    - **Validates: Requirements 4.3**
  
  - [x] 9.5 Implement LLM integration for response generation
    - Integrate OpenAI/Anthropic/SARVAM/open-source LLM API
    - Implement generate_response() with prompt template
    - Include retrieved documents in context
    - Request response in target language
    - Handle API errors and timeouts
    - _Requirements: 4.2, 2.3, 6.1_
  
  - [ ]* 9.6 Write property test for response grounding
    - **Property 14: Response Grounding**
    - **Validates: Requirements 4.2**
  
  - [ ]* 9.7 Write unit tests for LLM error handling
    - Test timeout handling
    - Test API failure retry logic
    - Test token limit exceeded
    - _Requirements: 9.3, 9.5_

- [x] 10. Implement Response Generator component
  - [x] 10.1 Create ResponseGenerator class
    - Implement format_response() for WhatsApp formatting
    - Implement create_scheme_summary() for multiple results
    - Implement create_welcome_message() in all languages
    - Implement create_help_message() in all languages
    - Add emoji and structure formatting
    - _Requirements: 6.1, 6.2, 7.1, 7.2_
  
  - [ ]* 10.2 Write property test for response structure
    - **Property 18: Response Structure Completeness**
    - **Validates: Requirements 6.1, 6.3, 4.4**
  
  - [ ]* 10.3 Write property test for multi-scheme summary
    - **Property 19: Multi-Scheme Summary Format**
    - **Validates: Requirements 6.2**
  
  - [x] 10.4 Implement message splitting logic
    - Implement split_message() to handle >1600 characters
    - Split at logical boundaries (sections, sentences)
    - Preserve formatting and structure
    - _Requirements: 6.4, 6.5_
  
  - [ ]* 10.5 Write property test for message length constraint
    - **Property 20: Message Length Constraint**
    - **Validates: Requirements 6.4**
  
  - [ ]* 10.6 Write property test for logical message splitting
    - **Property 21: Logical Message Splitting**
    - **Validates: Requirements 6.5**
  
  - [ ]* 10.7 Write property test for response language consistency
    - **Property 7: Response Language Consistency**
    - **Validates: Requirements 2.3, 2.4, 2.5**

- [x] 11. Implement WhatsApp Business API integration
  - [x] 11.1 Create WhatsAppClient class
    - Implement send_message() to WhatsApp Cloud API
    - Implement send_template_message() for structured messages
    - Handle authentication with access token
    - Add request/response logging
    - _Requirements: 1.2_
  
  - [x] 11.2 Implement retry logic for API failures
    - Implement exponential backoff (1s, 2s, 4s)
    - Retry up to 3 times
    - Queue failed messages for later retry
    - _Requirements: 9.4_
  
  - [x] 11.3 Write property test for API retry logic
    - **Property 27: API Retry Logic**
    - **Validates: Requirements 9.4**
  
  - [ ]* 11.4 Write property test for WhatsApp API integration
    - **Property 2: WhatsApp API Integration**
    - **Validates: Requirements 1.2**

- [x] 12. Implement Webhook Handler
  - [x] 12.1 Create FastAPI webhook endpoints
    - Implement POST /webhook for incoming messages
    - Implement GET /webhook for verification
    - Validate webhook signature using app secret
    - Extract message content and sender info
    - _Requirements: 1.1_
  
  - [x] 12.2 Implement message routing logic
    - Route text messages to main processing pipeline
    - Handle multimedia messages with acknowledgment
    - Detect help commands and route to help handler
    - Detect category selection and route to category handler
    - _Requirements: 1.3, 7.2, 7.4_
  
  - [x] 12.3 Write property test for multimedia handling
    - **Property 3: Multimedia Message Handling**
    - **Validates: Requirements 1.3**
  
  - [x] 12.4 Write unit tests for webhook verification
    - Test valid signature verification
    - Test invalid signature rejection
    - Test verification challenge response
    - _Requirements: 1.1_

- [x] 13. Implement main message processing pipeline
  - [x] 13.1 Create MessageProcessor orchestrator
    - Wire together: SessionManager → LanguageDetector → QueryProcessor → RAGEngine → ResponseGenerator
    - Implement process_incoming_message() end-to-end flow
    - Handle new user welcome messages
    - Handle help commands
    - Handle category browsing
    - Handle scheme detail requests
    - _Requirements: 1.1, 7.1, 7.2, 7.3, 7.4_
  
  - [x] 13.2 Implement special command handlers
    - Handle "help" command in all languages
    - Handle category menu display
    - Handle category selection (e.g., "1" for agriculture)
    - Handle scheme detail requests (e.g., "details 2")
    - _Requirements: 7.2, 7.3, 7.4_
  
  - [x] 13.3 Write property test for help command multi-language
    - **Property 22: Help Command Multi-Language**
    - **Validates: Requirements 7.2**
  
  - [x] 13.4 Write property test for category filtering
    - **Property 23: Category Filtering**
    - **Validates: Requirements 7.4**
  
  - [x] 13.5 Write integration tests for end-to-end flow
    - Test complete flow: webhook → processing → response
    - Test new user onboarding flow
    - Test multi-turn conversation flow
    - _Requirements: 1.1, 7.1, 3.5_

- [x] 14. Checkpoint - Ensure integration works correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Implement error handling and logging
  - [x] 15.1 Create error handling middleware
    - Catch all exceptions in webhook handler
    - Generate user-friendly error messages
    - Log errors with request context
    - Anonymize phone numbers in logs
    - _Requirements: 9.5, 8.5_
  
  - [x] 15.2 Write property test for error message sanitization
    - **Property 28: Error Message Sanitization**
    - **Validates: Requirements 9.5**
  
  - [x] 15.3 Write property test for log anonymization
    - **Property 26: Log Anonymization**
    - **Validates: Requirements 8.5**
  
  - [x] 15.4 Implement fallback handlers
    - Language detection fallback (default to English)
    - Intent extraction fallback (ask to rephrase)
    - RAG retrieval fallback (keyword search)
    - LLM generation fallback (pre-formatted responses)
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [x] 15.5 Write unit tests for fallback scenarios
    - Test language detection failure
    - Test intent extraction failure
    - Test vector store unavailability
    - Test LLM API failure
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 16. Implement privacy and security features
  - [x] 16.1 Implement data anonymization
    - Hash phone numbers in logs
    - Redact PII from analytics data
    - Implement session data cleanup on expiry
    - _Requirements: 8.1, 8.5, 8.2_
  
  - [ ]* 16.2 Write property test for third-party data isolation
    - **Property 25: Third-Party Data Isolation**
    - **Validates: Requirements 8.4**
  
  - [x] 16.3 Implement HTTPS enforcement
    - Configure FastAPI to require HTTPS
    - Validate WhatsApp webhook signatures
    - Use secure environment variable storage
    - _Requirements: 8.3_
  
  - [x] 16.4 Write unit tests for security features
    - Test webhook signature validation
    - Test HTTPS enforcement
    - Test environment variable encryption
    - _Requirements: 8.3_

- [x] 17. Implement performance optimizations
  - [x] 17.1 Add caching layer
    - Cache frequently accessed schemes in Redis
    - Cache language detection results for common phrases
    - Cache embeddings for common queries
    - Set appropriate TTLs (1 hour for schemes, 24 hours for embeddings)
    - _Requirements: 10.1, 10.2_
  
  - [x] 17.2 Implement async processing
    - Make all I/O operations async (database, API calls)
    - Use asyncio for concurrent processing
    - Implement connection pooling for databases
    - _Requirements: 10.1, 10.4_
  
  - [x] 17.3 Write property test for response time SLA
    - **Property 29: Response Time SLA**
    - **Validates: Requirements 10.1, 10.2**
  
  - [x] 17.4 Write property test for concurrent session handling
    - **Property 30: Concurrent Session Handling**
    - **Validates: Requirements 10.4**

- [x] 18. Implement queue management for overload
  - [x] 18.1 Create message queue system
    - Integrate RabbitMQ or AWS SQS
    - Implement queue_message() for overload scenarios
    - Implement process_queued_messages() worker
    - Track queue depth and estimated wait time
    - _Requirements: 10.5_
  
  - [x] 18.2 Implement load detection
    - Monitor active request count
    - Monitor response time percentiles
    - Trigger queuing when load exceeds threshold
    - Send wait time notifications to users
    - _Requirements: 10.5_
  
  - [x] 18.3 Write property test for overload queue management
    - **Property 31: Overload Queue Management**
    - **Validates: Requirements 10.5**

- [x] 19. Create database seeding and management scripts
  - [x] 19.1 Create scheme import script
    - Parse scheme data from JSON/CSV files
    - Generate embeddings for all scheme documents
    - Insert into PostgreSQL and vector store
    - Support bulk import and updates
    - _Requirements: 5.1, 5.2_
  
  - [x] 19.2 Create scheme update script
    - Update existing scheme information
    - Regenerate embeddings for updated content
    - Update vector store
    - Track last_updated timestamp
    - _Requirements: 5.3_
  
  - [x] 19.3 Create sample data for testing
    - Create 100+ sample schemes across all categories
    - Include schemes in all supported languages
    - Cover all Indian states and central schemes
    - Include active and expired schemes
    - _Requirements: 5.1, 5.5, 10.3_

- [x] 20. Implement monitoring and observability
  - [x] 20.1 Add application metrics
    - Track request count, response time, error rate
    - Track language distribution of queries
    - Track scheme retrieval success rate
    - Track LLM API usage and costs
    - Use Prometheus or similar metrics system
    - _Requirements: 10.1, 10.2_
  
  - [x] 20.2 Set up alerting
    - Alert on error rate >5% over 5 minutes
    - Alert on response time >10s for >10% of requests
    - Alert on database/vector store unavailability
    - Alert on LLM API failures
    - _Requirements: 10.1_
  
  - [x] 20.3 Implement health check endpoints
    - Create GET /health endpoint
    - Check database connectivity
    - Check Redis connectivity
    - Check vector store connectivity
    - Return 200 if all healthy, 503 otherwise
    - _Requirements: 10.1, 10.4_

- [x] 21. Create deployment configuration
  - [x] 21.1 Create Docker configuration
    - Write Dockerfile for FastAPI application
    - Create docker-compose.yml for local development
    - Include PostgreSQL, Redis, and vector store services
    - Configure environment variables
    - _Requirements: All (deployment)_
  
  - [x] 21.2 Create deployment documentation
    - Document environment variable requirements
    - Document WhatsApp Business API setup
    - Document vector store setup and configuration
    - Document LLM API setup
    - Create deployment checklist
    - _Requirements: All (deployment)_

- [ ] 22. Final checkpoint - Run full test suite
  - Run all unit tests and property tests
  - Run integration tests with mocked services
  - Run performance tests with load simulation
  - Verify all 31 correctness properties pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based and unit tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across random inputs
- Unit tests validate specific examples, edge cases, and error conditions
- The implementation uses Python with FastAPI, Hypothesis for property testing, and standard libraries for WhatsApp/LLM/Vector DB integration
- All 31 correctness properties from the design document have corresponding test tasks
