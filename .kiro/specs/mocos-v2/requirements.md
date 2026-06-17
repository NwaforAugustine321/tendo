# Requirements Document

## Introduction

MO-COS v2 (Master-Orchestrated Conversational Option System) is an Adaptive Business Intelligence Operating System that continuously learns how a user's existing business operates and manages operations through natural text/voice conversations. The core philosophy: "The business should not learn the platform. The platform should continuously learn and adapt to how the business operates." It is NOT a general-purpose AI assistant — a Business Scope Guardian Agent (BSGA) acts as the boundary firewall ensuring only business-related requests enter the system. The system uses a multi-agent architecture built on LangGraph with Redis checkpointing, Anthropic Claude as the LLM, Supabase (PostgreSQL) for structured business data and AI Business Understanding, Mem0 for conversation memory, and FastAPI for the API layer. It supports web, mobile, and WhatsApp channels with text and voice modalities. The real-time processing flow is: User → Communication Layer → BSGA → MOA → Cache Tool Layer (BCC) → Agents → Response. The background intelligence flow is: Confirmed Business Event → BLA (Reflection + Evolution) → AI Business Understanding Updated → BCC Refreshed.

## Glossary

- **MOA (Master Orchestrator Agent) — "Tendo"**: The central routing agent that controls conversation flow, routes tasks to domain agents, and manages workflow state. Tendo is the AI business employee identity that users interact with. MOA has no direct database access.
- **BSGA (Business Scope Guardian Agent)**: A lightweight, isolated classification agent that acts as the AI boundary firewall. It evaluates every incoming request to determine if it falls within the business operations scope before any business learning or operational processing occurs. The BSGA answers one question: "Should this request enter the MO-COS business operating system?" It has no access to business data, memory, or learning context.
- **Scope_Response_Generator**: The component within BSGA that produces polite decline messages redirecting users back to business operations when a request is classified as out-of-scope.
- **BCC (Business Context Cache)**: A Redis-based fast working memory that stores business profile summaries, frequently used entities, and session context for rapid access without database queries.
- **BLA (Business Learning Agent)**: A fully asynchronous intelligence engine that maintains the AI's business understanding. It does NOT run on every user request. Instead, it is triggered by confirmed business events and a daily midnight reflection job. It analyzes evidence, discovers patterns, updates AI Business Understanding in Supabase, and regenerates the Business Context Cache in Redis. Contains four internal engines: Context Retrieval, Context Synthesis, Reflection, and Business Evolution. The BLA maintains the BCC so that MOA can use prepared working memory during real-time conversations.
- **Business_Operating_Context**: The AI-ready business knowledge available to MOA via the Business Context Cache. Maintained asynchronously by the BLA. Contains: Business Profile, Business Understanding Summary, Frequently Used Entities, Operational Awareness, and Recent Business Summary.
- **AI_Business_Understanding**: Evidence-based business hypotheses stored in Supabase via DB Oracle. Not raw transaction data and not a copy of Mem0 conversations. Each understanding contains a human-readable summary, confidence score, supporting evidence count, evidence references, user correction history, and evolution history. Represents the AI's continuously evolving understanding of how a specific business operates.
- **Context_Retrieval_Engine**: BLA internal component that collects Business Truth (via DB Oracle), Confirmed Conversation History (via DB Oracle), existing AI Business Understanding (via DB Oracle), and Mem0 data (lowest priority) during background processing.
- **Context_Synthesis_Engine**: BLA internal component that combines analyzed evidence into a compressed, AI-ready Business Context Cache payload suitable for real-time use by MOA.
- **Reflection_Engine**: BLA internal component that runs asynchronously after confirmed business operations, analyzing user intent, conversation history, confirmations, corrections, and executed actions to produce new evidence.
- **Business_Evolution_Engine**: BLA internal component that continuously evolves AI Business Understanding by increasing/decreasing confidence, creating hypotheses, merging understandings, and retiring outdated ones.
- **Operation_Checkpoint**: A record capturing the full context of a confirmed business operation including session, user message, AI understanding, before/after state, and timestamp.
- **Conversation_Session**: A named workspace session (e.g., "Morning Sales Update") containing conversation history, AI responses, confirmation history, and operation checkpoints.
- **DB_Oracle**: The only module permitted to import Supabase or execute database operations. Provides read and write tools behind a confirmation gate.
- **Tool_Planner**: An agent that converts user intent into structured tool call requests without executing them.
- **Context_Resolution**: An agent that converts raw database results into natural conversational language without direct database or Mem0 access.
- **Memory_Node**: The agent responsible for retrieving and persisting data via Mem0 with no Supabase access.
- **Domain_Agent**: Specialized agents (Sales, Payment, Inventory, Service) that handle business logic without direct database or Mem0 access.
- **Communication_Layer**: The independent module that owns the entire delivery experience. It handles: channel connection (Web, Mobile, WhatsApp), input processing (text passthrough or voice STT), response delivery decisions based on channel + user preferences + input type, and final delivery via sendText/sendVoice tools. The Communication Layer is completely independent from the business intelligence system — the same MO-COS intelligence works regardless of communication channel.
- **Google_Voice_Engine**: The centralized speech processing service for MO-COS. Responsible for all Speech-to-Text (STT) converting user voice from web microphone, mobile recordings, and WhatsApp voice notes into normalized text, and all Text-to-Speech (TTS) converting AI-generated text responses into natural voice for application playback and WhatsApp voice messages. No AI agent ever processes raw audio.
- **Channel_Connector**: The transport-level component that receives raw input from Web, Mobile, or WhatsApp channels and routes it to the Communication Layer for processing.
- **Response_Delivery_Decision_Layer**: The component within Communication_Layer that determines the final output format based on communication channel, user preferences, and original input type.
- **UnifiedUserEvent**: The standardized input payload containing event_id, thread_id, user_id, text (always normalized — never raw audio), channel (web/mobile/whatsapp), input_type (text/voice), selected_option_id, and metadata. The MOA never knows whether the original message was typed or spoken.
- **Confirmation_Gate**: A mechanism requiring explicit user confirmation before any write operation is executed against the database.
- **RLS (Row-Level Security)**: PostgreSQL security mechanism that isolates tenant data by business_id on all tables.
- **Thread_ID**: A unique session identifier used for LangGraph checkpointing and conversation continuity.
- **Structured_Options**: A response mode that presents choices, confirmations, classifications, or missing information prompts to the user in a structured format.
- **Conversation_Mode**: A response mode that delivers natural language text responses.
- **Idempotency_Key**: A unique event_id attached to write operations that prevents duplicate processing.
- **Audit_Log**: A record in the audit_logs table tracking all write operations for traceability.
- **Business_Truth**: The authoritative source of business data stored in Supabase, ranked highest in the evidence trust order.

## Requirements

### Requirement 1: Unified Event Ingress

**User Story:** As a developer, I want a single event-driven API endpoint that accepts all user interactions regardless of channel, so that the system has one consistent entry point for processing.

#### Acceptance Criteria

1. THE FastAPI_Server SHALL expose a POST /events endpoint that accepts a UnifiedUserEvent payload containing event_id (string, max 128 characters), thread_id (string, max 128 characters), user_id (string, max 128 characters), text (string, max 4096 characters — always normalized text, never raw audio), channel (enum: web/mobile/whatsapp), input_type (enum: text/voice), selected_option_id (string, optional), and metadata (object, optional) fields.
2. WHEN a UnifiedUserEvent is received at POST /events with valid required fields, THE FastAPI_Server SHALL validate that event_id, thread_id, and user_id are present and contain at least one non-whitespace character, and return an HTTP 200 response including the event_id to confirm acceptance.
3. IF a UnifiedUserEvent is missing required fields or contains required fields that are empty or whitespace-only, THEN THE FastAPI_Server SHALL return an HTTP 422 response with a validation error that identifies which fields failed validation.
4. WHEN a GET /webhook/whatsapp request is received containing the Meta verification challenge token, THE FastAPI_Server SHALL respond with HTTP 200 and echo back the challenge token to complete webhook verification.
5. THE FastAPI_Server SHALL expose a POST /webhook/whatsapp endpoint that receives WhatsApp message payloads and transforms them into UnifiedUserEvent format before dispatching through the same processing path as POST /events.
6. WHEN a WhatsApp voice message is received, THE Communication_Layer SHALL invoke Google_Voice_Engine STT to transcribe the audio into text before constructing the UnifiedUserEvent.
7. IF Google_Voice_Engine STT transcription fails or times out after 30 seconds, THEN THE Communication_Layer SHALL discard the voice event and return an error response indicating that transcription was unsuccessful.

### Requirement 2: Multi-Channel Communication Layer

**User Story:** As a user, I want to interact with the system through my preferred channel (app or WhatsApp) using text or voice, so that I can manage my business operations naturally as if talking to a human business employee, regardless of which channel I use.

#### Communication Philosophy

The user should be able to interact with MO-COS naturally like a human business employee. The communication channel is only a transport mechanism. Business intelligence remains the same regardless of where the message originates. MO-COS should behave as one AI business employee that exists everywhere — inside the web application, inside the mobile application, and inside WhatsApp. The user should never have to think about the channel.

#### Supported Channels and Modalities

| Channels | Input Modalities | Output Modalities | NOT Supported |
|----------|-----------------|-------------------|---------------|
| MO-COS Web Application | Text, Voice | Text, Voice | Images, PDFs, File uploads |
| MO-COS Mobile Application | Text, Voice | Text, Voice | Images, PDFs, File uploads |
| WhatsApp | Text, Voice Notes | Text, Voice Messages | Images, PDFs, File uploads |

#### Acceptance Criteria

##### Channel Support

1. THE Communication_Layer SHALL support two communication channels: the MO-COS Application (Web and Mobile) and WhatsApp Integration.
2. THE Communication_Layer SHALL support two input modalities: text (maximum 4,000 characters) and voice (maximum 120 seconds duration).
3. THE Communication_Layer SHALL support two output modalities: text and voice.
4. IF a user submits input that is not text or voice (including images, PDFs, and file uploads), THEN THE Communication_Layer SHALL discard the input and return an error indication to the user stating that only text and voice inputs are accepted.

##### Communication Layer Independence

5. THE Communication_Layer SHALL be architecturally independent from the business intelligence system — changes to communication channels or delivery logic SHALL NOT require changes to MOA, Domain Agents, or DB Oracle.
6. THE same MO-COS intelligence (BSGA → MOA → Agents → DB Oracle) SHALL produce identical business results regardless of whether the user communicates from Web, Mobile, or WhatsApp.

##### Google Voice Engine — Centralized Speech Processing

7. ALL speech-to-text (STT) conversion SHALL be performed exclusively by Google_Voice_Engine, supporting: web microphone recordings, mobile application voice recordings, and WhatsApp voice notes.
8. ALL text-to-speech (TTS) conversion SHALL be performed exclusively by Google_Voice_Engine, producing audio for: application voice playback and WhatsApp voice messages.
9. THE MOA and ALL AI agents SHALL NEVER process raw audio — the AI runtime receives only normalized text.

##### Incoming Communication Pipeline — Text Input

10. WHEN a text input is received from any channel (Web, Mobile, WhatsApp), THE Communication_Layer SHALL pass the text directly into a Unified Communication Event without modification.

##### Incoming Communication Pipeline — Voice Input

11. WHEN a voice input is received from any channel, THE Communication_Layer SHALL route the audio to Google_Voice_Engine STT for transcription within 10 seconds before constructing the Unified Communication Event.
12. THE Unified Communication Event SHALL contain: user_id, business_id, session_id (thread_id), communication channel (web/mobile/whatsapp), input type (text/voice), text content (always normalized text), and timestamp.
13. THE MOA SHALL NOT know whether the original message was typed or spoken — it SHALL only receive normalized text.

##### Response Generation Architecture

14. THE MOA SHALL always produce a canonical text response and/or structured options — it SHALL NEVER produce audio.
15. THE Communication_Layer SHALL decide the final output format after receiving MOA's text response, based on: communication channel, user preferences, and original input type.

##### Application Response Rules (Response Delivery Decision)

16. WHEN the response channel is the MO-COS Application, THE Communication_Layer SHALL deliver the response in the format specified by the user's configured communication preference, defaulting to Voice+Text.
17. IN Voice+Text mode (application default), THE Communication_Layer SHALL deliver both: displayed text AND audio generated by Google_Voice_Engine TTS.
18. IN Text Only mode, THE Communication_Layer SHALL deliver displayed text only — no audio generation.
19. IN Voice Only mode, THE Communication_Layer SHALL deliver audio generated by Google_Voice_Engine TTS only.
20. THE user's input method SHALL NOT determine the application response format — only the user's configured preference determines it (e.g., user types "Show today's sales" with Voice+Text preference → receives both text and voice response).

##### WhatsApp Response Rules (Response Delivery Decision)

21. WHEN the response channel is WhatsApp, THE Communication_Layer SHALL mirror the input type: a text message input receives a text message response, and a voice note input receives a voice message response generated by Google_Voice_Engine TTS.
22. THE MOA SHALL NOT manage WhatsApp delivery rules — the Communication_Layer handles them entirely.

##### Google Voice Engine Error Handling

23. IF Google_Voice_Engine STT fails or does not respond within 10 seconds, THEN THE Communication_Layer SHALL return an error indication to the user that voice processing is temporarily unavailable and prompt the user to retry or use text input instead.
24. IF Google_Voice_Engine TTS fails or does not respond within 10 seconds, THEN THE Communication_Layer SHALL deliver the response as text only and include an indication that voice output is temporarily unavailable.

##### Session Continuity Across Channels

25. Conversation sessions SHALL be independent from the communication channel — the same user accessing from different channels SHALL share the same session context.
26. WHEN a user switches channels mid-session (e.g., mobile app in the morning, WhatsApp voice note later), THE Communication_Layer SHALL identify the same user and continue using the appropriate business and session context via the shared thread_id.
27. THE Communication_Layer SHALL maintain full session continuity by preserving all prior messages, conversation context, and user preferences associated with that thread_id regardless of which channel delivers the next message.

##### MOA Isolation from Communication Concerns

28. THE MOA SHALL NEVER directly interact with: WhatsApp APIs, Google Voice Engine, audio streaming, or channel-specific delivery logic.
29. ALL channel-specific delivery logic SHALL be encapsulated within the Communication_Layer and its delivery tools (sendText, sendVoice).

### Requirement 3: Business Scope Guardian Agent

**User Story:** As a business owner, I want the system to only respond to business-related requests, so that my business memory remains uncontaminated by irrelevant interactions and the system remains a dedicated Business Operating Intelligence System.

#### Architecture Position

The BSGA is the first intelligent agent in the processing pipeline. The updated entry flow is:

```
USER → Unified Event → BSGA → (in-scope?) → MOA → Cache Tool Layer → BCC → Agent Architecture
                                (out-of-scope?) → Scope Response Generator → USER
```

The BSGA answers one question: "Should this request enter the MO-COS business operating system?"

#### Core Philosophy

MO-COS is not a general-purpose AI assistant. It is a Business Operating Intelligence System designed to: learn how a user's existing business operates, manage business operations, record financial and operational activities, provide visibility into business performance, and continuously improve Business Understanding. The BSGA protects this boundary.

#### Acceptance Criteria

##### Classification Behavior

1. WHEN a UnifiedUserEvent passes validation, THE BSGA SHALL evaluate the request and produce a classification result within 3 seconds before any other agent (BLA, MOA, Domain Agents) processes it.
2. THE BSGA SHALL classify each request into one of two categories: IN_SCOPE or OUT_OF_SCOPE.
3. THE BSGA SHALL classify as IN_SCOPE any request related to Business Understanding (e.g., "This is how I usually sell my products", "My customers normally pay at the end of the month", "I changed the way I record payments").
4. THE BSGA SHALL classify as IN_SCOPE any request related to Business Operations (e.g., "I sold 10 bags of rice", "Record a payment from Musa", "Add 20 cartons to inventory", "Create an invoice for this customer").
5. THE BSGA SHALL classify as IN_SCOPE any request related to Business Analysis and Visibility (e.g., "How much did I sell this month?", "Which customers owe me money?", "Which products are performing best?", "Show my current inventory").
6. THE BSGA SHALL classify as IN_SCOPE any request related to Business Corrections (e.g., "Musa is not a customer, he is my supplier", "This transaction was cash, not credit").
7. THE BSGA SHALL classify as OUT_OF_SCOPE any request related to new business creation ideas (e.g., "Give me a new business idea", "What business should I start?").
8. THE BSGA SHALL classify as OUT_OF_SCOPE any request related to generic content creation (e.g., "Write me a poem", "Write my school assignment", "Create a personal CV").
9. THE BSGA SHALL classify as OUT_OF_SCOPE any request related to general knowledge (e.g., "Who is the president of a country?", "What is the capital of France?", "Explain quantum physics").
10. THE BSGA SHALL classify as OUT_OF_SCOPE any request related to personal tasks (e.g., travel planning, personal advice, entertainment requests, unrelated conversations).

##### Data Access Restrictions

11. THE BSGA SHALL receive only the current user input text and the platform scope definition as context for classification.
12. THE BSGA SHALL have NO access to Business_Truth (Supabase), DB_Oracle, Mem0 conversation memory, AI Business Understanding, or BLA context.
13. THE BSGA SHALL NOT import or invoke any database client, memory client, or cache tool.

##### In-Scope Response Behavior

14. WHEN a request is classified as IN_SCOPE, THE BSGA SHALL forward the request to the Master Orchestrator (MOA), which will load business context from the Business Context Cache.

##### Out-of-Scope Response Behavior

15. IF a request is classified as OUT_OF_SCOPE, THEN THE BSGA SHALL return a polite decline message via the Scope_Response_Generator that: acknowledges the user's input, states that MO-COS is designed to understand and manage existing business operations, and lists examples of what the user can ask about (sales, customers, inventory, payments, invoices, business performance).
16. IF a request is classified as OUT_OF_SCOPE, THEN THE BSGA SHALL NOT forward the request to BLA, MOA, or any downstream agent.
17. IF a request is classified as OUT_OF_SCOPE, THEN NO Mem0 memory update, Business Learning, or Business Truth interaction SHALL occur for that request.
18. THE BSGA decline message SHALL NOT attempt to answer the out-of-scope request, not even partially.

##### Ambiguity Handling

19. IF the BSGA cannot determine whether a request is IN_SCOPE or OUT_OF_SCOPE with sufficient confidence, THEN THE BSGA SHALL classify the request as OUT_OF_SCOPE and return a decline message inviting the user to rephrase the request in terms of their business operations.

##### Pollution Prevention Principle

20. THE system SHALL ensure that out-of-scope requests never reach the BLA, preventing business understanding from being polluted with irrelevant conversational data.
21. THE system SHALL ensure that out-of-scope requests never trigger Mem0 memory persistence, preventing conversation memory from storing non-business interactions.

### Requirement 4: Business Context Cache — AI Working Memory

**User Story:** As a system architect, I want a fast in-memory cache layer that represents the AI's working memory, so that real-time conversations use prepared knowledge and never block on database queries for routine interactions.

#### Core Performance Philosophy

MO-COS should behave like an experienced employee. An experienced employee does not read every business record before responding. They already remember: what business they work for, common customers, frequent products, regular services, typical workflows, business language, and current important situations. They only check the official records when exact details are needed. The system must follow the same model.

#### Architecture Position — Cache-First Runtime Flow

```
USER → BSGA → MOA
                ↓
        Load: getBusinessContext() + getSessionContext()
                ↓
        Context Sufficiency Decision (MOA responsibility)
                ↓
        Sufficient? → Continue with agents (Intent, Context, Domain, Confirmation)
        Insufficient? → Delegate retrieval to DB Oracle
```

The BLA does NOT run on every request. The MOA loads from cache and decides sufficiency.

#### Acceptance Criteria

##### Business Context Cache Content

1. THE BCC SHALL store in Redis a compressed, AI-ready summary of the business — NOT a copy of the database.
2. THE BCC SHALL NOT store: all customers, all products, all services, all sales, all payments, all invoices, or complete conversation history. These remain in Business Truth storage.
3. THE BCC SHALL contain the following Business Profile data: business name, business category (Product/Service/Hybrid), and high-level business description.
4. THE BCC SHALL contain a Business Understanding Summary including: common business behaviors, frequently observed workflows, common payment habits, business terminology, and communication style summary.
5. THE BCC SHALL contain Frequently Used Business Entities including: most frequently referenced customers, frequently sold products, frequently performed services, and frequently involved suppliers.
6. THE BCC SHALL contain Operational Awareness data including: current alerts, important outstanding debts, inventory warnings, and active operational concerns.
7. THE BCC SHALL contain a Recent Business Summary including: recent activities, current business focus, and ongoing patterns.

##### Session Context Cache

8. THE system SHALL maintain a Session Context Cache stored separately from the Business Context Cache in Redis.
9. THE Session Context Cache SHALL contain: current conversation topic, current customer being discussed, current product or service, pending confirmation, temporary conversation decisions, and current workflow stage.
10. THE Session Context Cache SHALL help the AI continue conversations naturally without repeatedly searching for the same information.

##### Cache Tool Layer

11. ALL Redis access for business and session context SHALL happen through controlled Cache Tools — MOA and other agents SHALL NEVER access Redis directly.
12. THE Cache Tool Layer SHALL expose getBusinessContext() returning: business profile, business understanding summary, frequently used entities, operational awareness, and recent business summary.
13. THE Cache Tool Layer SHALL expose getSessionContext() returning: current business operation, current entities being discussed, pending confirmation, and current workflow state.
14. THE Cache Tool Layer SHALL expose updateBusinessContext() for updating or replacing the Business Context Cache — called ONLY by the BLA, background reflection jobs, and business profile updates — NOT during normal user conversations.
15. THE Cache Tool Layer SHALL expose updateSessionContext() for updating temporary conversation memory — called when the user changes topic, a new entity is introduced, a confirmation is waiting, or the conversation state changes.
16. EACH Cache Tool operation SHALL return results within 100 milliseconds under normal Redis availability.

##### MOA Context Sufficiency Responsibility

17. THE MOA SHALL be responsible for deciding: "Do I have enough information to understand, respond, or execute this request?" — there SHALL NOT be a separate retrieval decision agent.
18. THE MOA SHALL use the available cache before requesting deeper information from DB Oracle.
19. WHEN the cache contains sufficient context (e.g., user mentions a known frequent customer and frequent product for a routine operation), THE MOA SHALL proceed directly to intent understanding and confirmation without querying DB Oracle.
20. WHEN the request requires exact current values (balances, stock quantities, invoice status), historical records, or ambiguity resolution, THE MOA SHALL delegate data retrieval to DB Oracle.

##### Examples: Cache Sufficient (No DB Oracle Needed)

21. WHEN a user says "I sold 5 bags of rice to Musa" and the cache knows Musa is a regular customer, rice is a frequent product, and the business commonly records credit sales, THE MOA SHALL continue directly to understanding and confirmation.
22. WHEN a user says "We now offer home delivery", THE MOA SHALL understand the business evolution and process the change using cached business context.

##### Examples: DB Oracle Required

23. WHEN a user asks "How much does Musa owe me?" THE MOA SHALL always retrieve current data from Business Truth via DB Oracle.
24. WHEN a user asks "Show all invoices from January" or "Compare this month to last month", THE MOA SHALL retrieve historical records from DB Oracle.
25. WHEN ambiguity exists (multiple customers with same name, multiple similar products), THE MOA SHALL retrieve additional details through DB Oracle or ask clarification questions.

##### Scoping and Availability

26. THE BCC SHALL scope all cached data by business_id using Redis key prefixes in the format bcc:{business_id}:* and session:{business_id}:{thread_id}:* to maintain tenant isolation.
27. IF Redis is unavailable when a cache tool operation is invoked, THEN THE Cache Tool Layer SHALL return an error indication to the caller, and the MOA SHALL fall back to retrieving context from DB_Oracle for that request.
28. THE BCC business context entries SHALL have a TTL of 24 hours, after which the entry is considered stale and the BLA SHALL regenerate it on next access or next scheduled update.
29. THE Session Context Cache entries SHALL have a TTL matching the session duration (default 24 hours) and SHALL be cleared when the session ends.

### Requirement 5: Business Learning Agent — Asynchronous Intelligence Engine

**User Story:** As a business owner, I want the system to continuously learn how my business operates through evidence without slowing down my conversations, so that it becomes an increasingly accurate AI employee that adapts to my business rather than requiring my business to adapt to it.

#### Core Philosophy

The platform should continuously learn and adapt to how the business operates — similar to how Cursor learns a codebase. The system does not create rigid business rules. It develops a continuously evolving understanding of the business through evidence-based hypotheses. Learning must be separated from execution.

#### Architecture Position — Fully Asynchronous

```
Real-Time Path (fast):
  USER → BSGA → MOA → Cache Tool Layer → BCC + Session Cache → Agents → Response

Background Intelligence Path (async):
  Business Event OR Daily Midnight Reflection
    → Business Learning Agent
    → Analyze Evidence
    → Update AI Business Understanding
    → updateBusinessContext()
    → Redis BCC Updated
```

The BLA is NO LONGER part of every conversation request. It is an asynchronous intelligence engine that runs in the background. The MOA loads prepared working memory from the BCC — the BLA maintains that working memory.

#### Design Principle

Separate execution from learning. Real-time conversations use prepared working memory. Deep understanding happens asynchronously. Think of it as:
- Business Truth = The company's official records
- Conversation History = Past discussions and decisions
- Mem0 = The owner's communication preferences
- AI Business Understanding = The experience accumulated by the AI
- Business Context Cache = The AI employee's working memory
- Session Context Cache = What the AI is currently working on

The AI should think with its working memory first and only open the company archives when exact evidence is required.

#### Acceptance Criteria

##### BLA Operates Asynchronously

1. THE BLA SHALL NOT execute on every user request — it SHALL operate exclusively as a background asynchronous process triggered by confirmed business events or scheduled reflection jobs.
2. THE BLA SHALL add ZERO latency to the user request-response cycle because it does not participate in the real-time processing path.
3. THE MOA SHALL load business context from the BCC (maintained by the BLA) rather than waiting for the BLA to synthesize context on each request.

##### BLA Data Sources

4. THE BLA SHALL combine three sources of understanding when analyzing evidence: Business Truth (Supabase via DB Oracle), Human Conversation Memory (Mem0), and AI Business Understanding (Supabase via DB Oracle).
5. Business Truth SHALL answer the question "What actually happened in this business?" — sales history, payments, inventory movements, services, customer behavior, supplier activity, financial trends.
6. Human Conversation Memory SHALL answer the question "How does the owner describe business operations?" — user language, corrections, confirmed decisions, communication patterns. THE BLA SHALL NEVER create hard rules from phrases (Wrong: "Write it down = Credit sale". Correct: "The owner frequently uses informal language when describing unpaid transactions").
7. AI Business Understanding SHALL answer the question "Based on everything observed, how does the AI currently understand this business?" — current hypotheses, confidence levels, historical learning.
8. Mem0 SHALL be used ONLY for communication preferences, interaction style, and user conversation preferences — Mem0 MUST NEVER override Business Truth.

##### AI Business Understanding Model

9. EACH AI Business Understanding entry SHALL contain: a human-readable business understanding summary, confidence score (0.0 to 1.0), supporting evidence count, evidence references, user correction history, creation date, last updated date, and evolution history.
10. THE AI Business Understanding model SHALL NOT use fixed category tables (e.g., separate tables for rules, terms, workflows, patterns) because such assumptions do not generalize across all businesses.
11. THE system SHALL think in terms of "Based on evidence, what does the AI currently understand about this business?" rather than "What fixed rule has been discovered?"

##### BLA Internal Engines

12. THE BLA SHALL contain four internal engines: Context Retrieval Engine, Context Synthesis Engine, Reflection Engine, and Business Evolution Engine.

##### Context Retrieval Engine (Background Only)

13. THE Context_Retrieval_Engine SHALL collect Business Truth by retrieving business facts through DB Oracle read tools during background processing.
14. THE Context_Retrieval_Engine SHALL collect Confirmed Conversation History from the conversation database via DB Oracle.
15. THE Context_Retrieval_Engine SHALL collect existing AI Business Understanding including current hypotheses and confidence levels via DB Oracle.
16. THE Context_Retrieval_Engine SHALL collect Mem0 data (lowest priority) only for communication preferences and interaction style.

##### Context Synthesis Engine (Background Only)

17. THE Context_Synthesis_Engine SHALL combine analyzed evidence into a compressed, AI-ready Business Context Cache payload suitable for real-time use by MOA.
18. THE Context_Synthesis_Engine SHALL produce the BCC content: Business Profile, Business Understanding Summary, Frequently Used Entities, Operational Awareness, and Recent Business Summary.

##### Reflection Engine (Event-Driven)

19. THE Reflection_Engine SHALL run after every completed and confirmed business operation — NOT during the user request.
20. THE Reflection_Engine SHALL analyze: original user intent, conversation history, user confirmations, user corrections, final executed business actions, and historical business context.
21. THE Reflection_Engine SHALL produce new evidence observations — it SHALL NOT immediately create permanent rules or business understandings from a single observation.

##### Business Evolution Engine

22. THE Business_Evolution_Engine SHALL increase confidence when evidence repeatedly supports an existing understanding.
23. THE Business_Evolution_Engine SHALL decrease confidence when the owner corrects the AI or contradicts an existing understanding.
24. THE Business_Evolution_Engine SHALL create new business hypotheses when repeated evidence suggests a previously unrecognized pattern.
25. THE Business_Evolution_Engine SHALL merge similar understandings when they describe the same business behavior with different evidence.
26. THE Business_Evolution_Engine SHALL retire outdated or invalid understandings when confidence drops below 0.2 or when contradicting evidence exceeds supporting evidence.
27. THE Business_Evolution_Engine SHALL maintain historical evolution records for each understanding, tracking confidence changes, evidence additions, and corrections over time.

##### Event-Driven BLA Updates

28. THE BLA SHALL be immediately triggered after the following confirmed business events: completion of onboarding, confirmed sales, confirmed payments, inventory updates, service completion, customer or supplier updates, user corrections, and business profile changes.
29. THE event-driven BLA flow SHALL be: Business Event → BLA Reflection → Analyze new evidence → Update AI Business Understanding → updateBusinessContext() → Redis BCC updated.
30. THE BLA SHALL process event-driven updates and persist updated business understanding within 30 seconds of event occurrence.

##### Midnight Business Reflection Job

31. WHEN the scheduled daily execution time (midnight local time) is reached, THE BLA SHALL execute the Midnight Business Reflection Job to discover long-term patterns that cannot be learned from individual transactions.
32. THE Midnight Reflection SHALL analyze evidence in priority order: Business Truth (highest priority), Confirmed Conversation History (second), Existing AI Business Understanding (third), and Mem0 (lowest priority — communication preferences only).
33. THE BLA SHALL increase confidence when evidence grows during midnight reflection, reduce confidence when users have corrected the AI, and retire outdated understandings.
34. IF the Midnight Business Reflection Job does not complete within 60 minutes, THEN THE BLA SHALL terminate the job and log the incomplete execution for subsequent retry at the next scheduled interval.

##### BCC Refresh

35. WHEN the BLA completes any update (event-driven or midnight reflection), THE BLA SHALL refresh the Business Context Cache via updateBusinessContext() within 5 seconds of completion.
36. IF the BLA fails to process a confirmed business event, THEN THE BLA SHALL retain the unprocessed event for retry and SHALL NOT discard or corrupt previously persisted business data.

##### Evidence Trust Order

37. IF a conflict exists between data sources, THEN THE BLA SHALL resolve the conflict using this evidence trust order: Business_Truth ranked first, Confirmed Conversation History ranked second, AI Business Understanding ranked third, and Mem0 ranked fourth.

### Requirement 6: Four-Layer Knowledge Architecture

**User Story:** As a system architect, I want a clear separation of knowledge responsibilities across four distinct layers, so that each type of data is stored in the most appropriate system with clear purpose separation, and real-time execution is decoupled from deep learning.

#### Knowledge Layers

| Layer | Technology | Purpose | Answers | Access Pattern |
|-------|-----------|---------|---------|---------------|
| Business Truth | Supabase via DB Oracle | Factual financial and operational records | "What happened?" | Real-time (when cache insufficient) + Background (BLA) |
| Human Conversation Memory | Mem0 | Communication and conversational context | "How does the owner communicate?" | Background (BLA) only |
| AI Business Understanding | Supabase via DB Oracle | Evidence-based understanding of how the business operates | "How does the AI understand this business?" | Background (BLA) only |
| Workflow State + BCC | Redis | Real-time execution state + prepared working memory | "What is the system doing now?" + "What does the AI already know?" | Real-time (every request) |

#### Design Principle

The system separates real-time execution from deep business learning:
- Real-time path: MOA reads from Redis (BCC + Session Cache) — fast, prepared
- Background path: BLA reads from Supabase + Mem0, writes to Supabase (AI Understanding) and Redis (BCC) — thorough, async

#### Acceptance Criteria

1. THE Business_Truth layer SHALL use Supabase exclusively (via DB Oracle) for all structured business records: customers, products, services, sales, payments, inventory, invoices, financial records, and transaction history.
2. THE Human_Conversation_Memory layer SHALL use Mem0 exclusively for communication style, long-term user preferences, and relevant conversational memory.
3. THE AI_Business_Understanding layer SHALL use Supabase exclusively (via DB Oracle) for evidence-based business hypotheses, confidence scores, evidence references, corrections, and historical evolution.
4. THE Workflow_State layer SHALL use Redis exclusively for current LangGraph state, pending confirmations, candidate options, interrupt checkpoints, and session context.
5. THE Memory_Node SHALL have no access to Supabase or the DB_Oracle module.
6. THE DB_Oracle SHALL have no access to Mem0 or the Memory_Node module.
7. THE Redis_Layer SHALL store LangGraph checkpoints keyed by thread_id with a TTL of 86400 seconds for session continuity.
8. THE Redis_Layer SHALL store ephemeral workflow state (candidates, confirmations, workflow phases) with a default TTL of 3600 seconds unless explicitly overridden.
9. THE Redis_Layer SHALL have no direct access to Mem0 or Supabase, and SHALL interact with other layers only through the orchestration layer.
10. AI Business Understanding SHALL NOT be stored in Mem0 — it belongs in Supabase as structured evidence-based data accessible through DB Oracle.
11. Conversation Session History (messages, AI responses, confirmations, timestamps) SHALL be stored in Supabase via DB Oracle — NOT in Mem0. Mem0 stores only distilled communication preferences.
12. IF a module attempts to write data to a storage system outside its designated layer, THEN THE System SHALL reject the operation and return an error indicating a layer isolation violation.

### Requirement 7: Agent Architecture and Strict Separation

**User Story:** As a developer, I want strict module boundaries between agents, so that each component has a single responsibility and cannot violate data access rules.

#### Acceptance Criteria

1. THE MOA SHALL route tasks, control conversation flow, and manage workflow state without importing or invoking any database client library or database query function.
2. THE Tool_Planner SHALL convert user intent into structured tool call requests without executing any tool operations.
3. THE DB_Oracle SHALL be the only module permitted to import the Supabase client or execute database operations.
4. THE Context_Resolution agent SHALL convert DB_Oracle results into human-readable conversational responses without importing or invoking the Supabase client or Mem0 client.
5. THE Memory_Node SHALL interact exclusively with Mem0 for retrieval and persistence without importing or invoking the Supabase client.
6. EACH Domain_Agent (Sales, Payment, Inventory, Service) SHALL implement business logic and SHALL request data exclusively through the MOA routing layer, without importing or invoking DB_Oracle, the Supabase client, or the Mem0 client.
7. THE BSGA SHALL operate as the first agent in the pipeline without importing or invoking any database client, memory client, cache tool, or BLA context — receiving only user input text and platform scope definition.
8. THE BLA SHALL operate as a fully asynchronous background intelligence engine — it SHALL NOT participate in the real-time request-response path. It SHALL access Business_Truth, Conversation History, and AI Business Understanding exclusively through DB_Oracle, and Mem0 exclusively through Memory_Node, and SHALL update the BCC exclusively through the updateBusinessContext() cache tool.
9. THE project codebase SHALL enforce module boundary rules through static analysis checks that fail when any module outside `db/` contains an import statement referencing the Supabase client library.
10. IF a module outside its permitted boundary attempts to import a restricted client library, THEN THE static analysis check SHALL report a violation identifying the offending module and the unauthorized import.

### Requirement 8: DB Oracle and Supabase Tools

**User Story:** As a business owner, I want my business data to be safely read and written through controlled operations, so that data integrity is maintained.

#### Acceptance Criteria

1. THE DB_Oracle SHALL provide the following business read tools: search_customers, search_products, search_services, search_payments, search_invoices, search_inventory, get_customer_history, and get_business_context.
2. THE DB_Oracle SHALL provide the following business write tools: create_sale, create_payment, create_invoice, update_inventory, create_service_record, record_refund, and record_debt.
3. THE DB_Oracle SHALL provide the following AI Business Understanding tools: get_business_understanding (retrieve hypotheses by business_id with optional confidence threshold), add_evidence (create new evidence observation linked to an understanding), update_confidence (modify confidence score for an existing understanding), evolve_understanding (create, merge, or retire business hypotheses), and get_evolution_history (retrieve change history for an understanding).
4. THE DB_Oracle SHALL provide the following conversation session tools: create_session, get_session_history, store_message, and get_session_messages.
5. THE DB_Oracle SHALL provide the following operation checkpoint tools: create_checkpoint (store before/after state with operation context) and get_checkpoints (retrieve checkpoints for a session or business).
3. WHEN a write tool is invoked, THE DB_Oracle SHALL verify that confirmation_status equals "confirmed" before executing the database operation.
4. IF a write tool is invoked without confirmation_status equal to "confirmed", THEN THE DB_Oracle SHALL reject the operation and return an error indicating confirmation is required.
5. THE DB_Oracle SHALL attach an idempotency key (event_id) to every write operation by persisting each event_id upon successful completion and rejecting any subsequent write operation bearing an already-persisted event_id, returning a success response with an indication that the operation was previously completed.
6. WHEN a write operation is executed, THE DB_Oracle SHALL create an entry in the audit_logs table recording timestamp, user_id, business_id, operation_type, and affected_entity reference containing the entity table name and entity identifier.
7. THE DB_Oracle SHALL apply RLS filtering by business_id on every query to enforce tenant isolation.
8. IF a database operation is rejected by an RLS policy, THEN THE DB_Oracle SHALL return an error response indicating insufficient authorization for the requested business_id and SHALL NOT expose internal schema details in the error output.
9. IF a write operation fails due to a database error or constraint violation, THEN THE DB_Oracle SHALL record the failed attempt in the audit_logs table with timestamp, user_id, business_id, operation_type, and failure reason.

### Requirement 9: LangGraph Workflow

**User Story:** As a developer, I want the conversation flow managed by a LangGraph StateGraph, so that agent orchestration is deterministic, checkpointed, and resumable.

#### Acceptance Criteria

1. THE LangGraph_Workflow SHALL define a StateGraph using a GraphState TypedDict to manage conversation state.
2. THE LangGraph_Workflow SHALL include the following real-time nodes: bsga, memory, moa, tool_planner, db_oracle, context_resolution, option_generator, domain_router, confirmation, and response. The BLA operates outside the real-time graph as an asynchronous background process.
3. THE LangGraph_Workflow SHALL apply interrupt_before on the confirmation node and the option_generator node to pause execution for user input, with a maximum wait time of 300 seconds before the interrupt times out.
4. THE LangGraph_Workflow SHALL use a Redis checkpointer for persisting graph state with a checkpoint TTL of 24 hours, after which checkpoint data is eligible for expiration.
5. THE LangGraph_Workflow SHALL key all sessions by thread_id to support session resumption across interactions.
6. WHEN a user resumes a session after an interrupt and the Redis checkpoint exists, THE LangGraph_Workflow SHALL restore state from the Redis checkpoint and continue from the interruption point.
7. IF the Redis checkpoint for a given thread_id is missing or expired when a user attempts to resume a session, THEN THE LangGraph_Workflow SHALL return an error indication that the session is no longer available and initiate a new session.
8. IF Redis is unavailable during a checkpoint write or read operation, THEN THE LangGraph_Workflow SHALL return an error indication that state persistence failed and SHALL NOT proceed with an inconsistent state.

### Requirement 10: Output Model

**User Story:** As a user, I want responses in either natural conversation or structured choices, so that I can interact naturally for open discussions and efficiently for selections and confirmations.

#### Acceptance Criteria

1. THE Output_Model SHALL support two response modes: CONVERSATION mode and STRUCTURED_OPTIONS mode.
2. WHILE the response mode is CONVERSATION, THE Output_Model SHALL produce natural language text responses of no more than 2000 characters.
3. WHILE the response mode is STRUCTURED_OPTIONS, THE Output_Model SHALL produce a structured payload containing one of: questions with 2 to 10 choices, confirmation prompts with 2 to 5 options, classification options with 2 to 10 options, or missing information requests with 1 to 10 requested fields.
4. WHEN the system generates a response that requires the user to select from a discrete set of options or confirm an action, THE MOA SHALL select STRUCTURED_OPTIONS mode.
5. WHEN the system generates a response that does not require a selection or confirmation from the user, THE MOA SHALL select CONVERSATION mode.
6. IF the MOA cannot determine the required output mode, THEN THE MOA SHALL default to CONVERSATION mode.

### Requirement 11: Confirmation Gate for Write Operations

**User Story:** As a business owner, I want every data-changing operation to require my explicit confirmation, so that accidental or incorrect modifications are prevented.

#### Acceptance Criteria

1. WHEN a Domain_Agent determines that a write operation (INSERT, UPDATE, or DELETE) is needed, THE MOA SHALL present a confirmation prompt to the user within 2 seconds of the determination.
2. WHEN a write operation requires confirmation, THE Confirmation_Gate SHALL present the operation details in STRUCTURED_OPTIONS mode, including the operation type, target entity, and a summary of the data to be changed, with labeled "Confirm" and "Reject" options.
3. WHEN the user confirms a write operation, THE MOA SHALL set confirmation_status to "confirmed" and route the request to DB_Oracle for execution.
4. WHEN the user rejects a write operation, THE MOA SHALL cancel the operation and return a cancellation acknowledgment to the user without executing the write.
5. IF the user's session expires before confirmation is received, THEN THE MOA SHALL discard the pending write operation and not execute it.
6. IF the user does not respond to a confirmation prompt within 5 minutes, THEN THE MOA SHALL discard the pending write operation, not execute it, and inform the user that the operation was cancelled due to timeout.

### Requirement 12: Safety and Data Integrity

**User Story:** As a business owner, I want my data protected by multiple safety mechanisms, so that unauthorized access, data corruption, and duplicate operations are prevented.

#### Acceptance Criteria

1. THE DB_Oracle SHALL be the only runtime module that establishes connections to Supabase.
2. THE system SHALL never generate or execute raw SQL from LLM output; all database access SHALL occur through predefined tool functions.
3. THE DB_Oracle SHALL enforce idempotency on all write operations by persisting each event_id upon successful completion and rejecting any subsequent write operation bearing an already-persisted event_id, returning a success response with an indication that the operation was previously completed rather than applying the write again.
4. THE Supabase_Schema SHALL enforce RLS policies on all tables scoped by business_id.
5. THE LangGraph_Workflow SHALL not include entity database IDs in serialized graph state to prevent stale reference errors.
6. WHEN a write operation completes, THE DB_Oracle SHALL record the operation in the audit_logs table with timestamp, user_id, business_id, operation_type, and affected_entity reference containing the entity table name and entity identifier.
7. IF a database operation is rejected by an RLS policy, THEN THE DB_Oracle SHALL return an error response indicating insufficient authorization for the requested business_id and SHALL NOT expose internal schema details in the error output.
8. IF a write operation fails due to a database error or constraint violation, THEN THE DB_Oracle SHALL record the failed attempt in the audit_logs table with timestamp, user_id, business_id, operation_type, and failure reason.

### Requirement 13: Supabase Schema

**User Story:** As a developer, I want a well-defined database schema with proper relationships and security policies, so that business data is stored correctly and isolated per tenant.

#### Acceptance Criteria

1. THE Supabase_Schema SHALL include the following tables: users, customers, suppliers, products, services, invoices, invoice_line_items, payments, inventory, inventory_movements, transactions, ledger_entries, conversation_state, audit_logs, ai_business_understanding, business_evidence, conversation_sessions, conversation_messages, and operation_checkpoints.
2. THE Supabase_Schema SHALL enable the pgvector extension for vector similarity operations.
3. THE Supabase_Schema SHALL apply RLS policies on every table that enforce business_id filtering on all operations (SELECT, INSERT, UPDATE, and DELETE), matching rows against the authenticated user's business_id claim from the JWT.
4. EACH table in the Supabase_Schema except the users table SHALL include a business_id column of type UUID used as the RLS partition key, referencing the users table.
5. EACH table in the Supabase_Schema SHALL use a UUID primary key column named id, generated by default.
6. THE Supabase_Schema SHALL define foreign key constraints between related tables: invoice_line_items referencing invoices, invoices referencing customers, payments referencing invoices, inventory referencing products, inventory_movements referencing inventory, ledger_entries referencing transactions, audit_logs referencing users, business_evidence referencing ai_business_understanding, conversation_messages referencing conversation_sessions, and operation_checkpoints referencing conversation_sessions.
7. THE users table in the Supabase_Schema SHALL include a business_id column that identifies the tenant the user belongs to, and its RLS policy SHALL restrict each user to accessing only rows matching their own business_id.
8. THE ai_business_understanding table SHALL contain: id, business_id, summary (text), confidence (float 0.0-1.0), evidence_count (integer), evidence_references (JSONB), correction_history (JSONB), evolution_history (JSONB), created_at, updated_at, and status (active/retired).
9. THE business_evidence table SHALL contain: id, business_id, understanding_id (FK to ai_business_understanding), evidence_type (confirmation/correction/observation), source_reference (JSONB), description (text), and created_at.
10. THE conversation_sessions table SHALL contain: id, business_id, user_id, title (text), status (active/archived), created_at, and updated_at.
11. THE conversation_messages table SHALL contain: id, business_id, session_id (FK to conversation_sessions), role (user/assistant), content (text), message_type (text/voice/understanding_card/question_card/confirmation_card/operation_card), metadata (JSONB), and created_at.
12. THE operation_checkpoints table SHALL contain: id, business_id, session_id (FK to conversation_sessions), message_id (FK to conversation_messages), operation_type (text), user_input (text), ai_understanding_summary (text), before_state (JSONB), after_state (JSONB), status (confirmed/reverted), and created_at.

### Requirement 14: Communication Delivery Tools

**User Story:** As a user, I want to receive responses in my preferred format on any channel, so that I can read text or listen to voice as appropriate without the AI needing to know about delivery mechanics.

#### Design Principle

The MOA must never directly interact with: WhatsApp APIs, Google Voice Engine, or audio streaming. Communication delivery tools encapsulate all channel-specific and format-specific delivery logic, keeping the AI runtime completely decoupled from the communication transport.

#### Acceptance Criteria

##### sendText Tool

1. THE Communication_Layer SHALL provide a sendText() tool responsible for: web application chat responses, mobile application chat responses, and WhatsApp text messages.
2. THE sendText tool SHALL deliver text messages of up to 4096 characters to the specified channel (Web, Mobile, or WhatsApp).
3. THE sendText tool SHALL accept: text content, target channel, user_id, and thread_id as parameters.

##### sendVoice Tool

4. THE Communication_Layer SHALL provide a sendVoice() tool responsible for: converting text into speech using Google_Voice_Engine TTS, streaming audio inside the application, and sending WhatsApp voice notes.
5. THE sendVoice tool SHALL convert text of up to 3000 characters to speech via Google_Voice_Engine TTS and deliver audio to the channel specified in the invocation request.
6. WHEN sendVoice is invoked for the MO-COS Application channel, THE Communication_Layer SHALL stream the audio response to the client for real-time playback.
7. WHEN sendVoice is invoked for the WhatsApp channel, THE Communication_Layer SHALL deliver the audio as a WhatsApp voice note via the WhatsApp API.

##### Response Delivery Decision Logic

8. THE Communication_Layer SHALL implement a Response Delivery Decision component that, given the MOA's canonical text response, determines which delivery tools to invoke based on: communication channel, user preferences (for app), and original input type (for WhatsApp).
9. FOR MO-COS Application with Voice+Text preference: invoke BOTH sendText AND sendVoice.
10. FOR MO-COS Application with Text Only preference: invoke ONLY sendText.
11. FOR MO-COS Application with Voice Only preference: invoke ONLY sendVoice.
12. FOR WhatsApp with text input: invoke ONLY sendText.
13. FOR WhatsApp with voice input: invoke ONLY sendVoice.

##### Error Handling and Fallbacks

14. IF Google_Voice_Engine TTS conversion fails during a sendVoice invocation, THEN THE Communication_Layer SHALL deliver the original text content as a fallback text message to the same channel and include an indication that voice delivery was unavailable.
15. IF sendText or sendVoice delivery to a channel fails, THEN THE Communication_Layer SHALL retry delivery up to 3 times with a 2-second interval between attempts, and if all retries fail, return an error indication to the caller specifying the channel and failure reason.
16. IF a channel connector (Web, Mobile, or WhatsApp) is unreachable, THE Communication_Layer SHALL log the delivery failure and NOT retry indefinitely.

### Requirement 15: Project Structure and Naming Conventions

**User Story:** As a developer, I want a well-organized Python package structure with clean naming conventions, so that code is maintainable, module boundaries are enforced by file organization, and no redundant prefixes pollute the codebase.

#### Naming Conventions

The package/directory name provides context — file names and variable names SHALL NOT repeat it.

| Avoid | Use Instead | Reason |
|-------|-------------|--------|
| `supabase/` (folder) | `migrations/` | Don't use vendor name as folder name |
| `supabase_client.py`, `mem0_client.py`, `anthropic_client.py` | `client.py` inside each package (`db/`, `memory/`, `llm/`) | Package already provides context |
| `redis_client`, `mem0`, `supabase_client` (variables) | `client` locally, or import alias by package | e.g., `from app.memory import client as memory` |
| `tool_registry.py`, `spec_loader.py`, `session_store.py` | `registry.py`, `specs.py`, `sessions.py` | Plain names inside module folders |
| `conversation_builder.py`, `options_builder.py` | `conversation.py`, `options.py` | No builder suffix needed |
| `event_normalizer.py` | `normalizer.py` | Package provides context |
| `mocos:session:{id}` Redis keys | `session:{id}`, `candidates:{id}`, `confirmation:{id}` | No system prefix |
| `db_oracle/` (folder), `oracle.py` | `db/`, `node.py` | Short, plain module name — no vendor/concept branding |

**Import pattern:**
```python
from app.db import client as db
from app.memory import client as memory
from app.llm import client as llm
from app.redis import client as redis
```

**Function naming:** Plain verbs — `search()`, `store()`, `load_spec()`, `get_client()` — no vendor prefixes.

**Env vars (.env)** may use vendor names (`SUPABASE_URL`, `MEM0_API_KEY`) — that is standard for configuration, not code naming.

#### Project Structure

```
tendo/
├── environment.yml
├── pyproject.toml
├── .env.example
├── migrations/
│   ├── config.toml
│   └── sql/                       # SQL migrations (Supabase CLI)
├── app/
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── models/
│   │   ├── state.py              # GraphState (TypedDict)
│   │   ├── event.py              # UnifiedUserEvent
│   │   ├── output.py             # ConversationOutput | OptionsOutput
│   │   └── tools.py              # Tool request models
│   ├── db/                        # SINGLE DB ACCESS LAYER
│   │   ├── client.py             # Database singleton
│   │   ├── node.py               # DB graph node (executes tool requests)
│   │   ├── registry.py           # Tool registry
│   │   └── tools/
│   │       ├── customers.py
│   │       ├── products.py
│   │       ├── services.py
│   │       ├── payments.py
│   │       ├── invoices.py
│   │       ├── inventory.py
│   │       ├── sales.py
│   │       ├── understanding.py  # AI Business Understanding tools
│   │       ├── sessions.py       # Conversation session tools
│   │       └── checkpoints.py    # Operation checkpoint tools
│   ├── memory/
│   │   ├── client.py             # Memory singleton
│   │   ├── search.py
│   │   └── store.py
│   ├── redis/
│   │   ├── client.py
│   │   ├── sessions.py
│   │   └── checkpointer.py
│   ├── llm/
│   │   ├── client.py             # LLM singleton
│   │   └── specs.py              # Agent spec loader
│   ├── agents/
│   │   ├── specs/                 # Agent configuration (.md files)
│   │   │   ├── moa/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   ├── role.md
│   │   │   │   └── tools.md
│   │   │   ├── bsga/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   ├── role.md
│   │   │   │   └── tools.md
│   │   │   ├── bla/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   ├── role.md
│   │   │   │   └── tools.md
│   │   │   ├── tool_planner/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   ├── role.md
│   │   │   │   └── tools.md
│   │   │   ├── context_resolution/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   └── role.md
│   │   │   ├── option_generator/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   └── role.md
│   │   │   ├── response_generator/
│   │   │   │   ├── skill.md
│   │   │   │   ├── backstory.md
│   │   │   │   ├── goal.md
│   │   │   │   └── role.md
│   │   │   └── domain/
│   │   │       ├── sales/
│   │   │       │   ├── skill.md
│   │   │       │   ├── backstory.md
│   │   │       │   ├── goal.md
│   │   │       │   ├── role.md
│   │   │       │   └── tools.md
│   │   │       ├── payment/
│   │   │       │   ├── skill.md
│   │   │       │   ├── backstory.md
│   │   │       │   ├── goal.md
│   │   │       │   ├── role.md
│   │   │       │   └── tools.md
│   │   │       ├── inventory/
│   │   │       │   ├── skill.md
│   │   │       │   ├── backstory.md
│   │   │       │   ├── goal.md
│   │   │       │   ├── role.md
│   │   │       │   └── tools.md
│   │   │       └── service/
│   │   │           ├── skill.md
│   │   │           ├── backstory.md
│   │   │           ├── goal.md
│   │   │           ├── role.md
│   │   │           └── tools.md
│   │   ├── moa.py
│   │   ├── bsga.py
│   │   ├── bla.py
│   │   ├── tool_planner.py
│   │   ├── context_resolution.py
│   │   ├── option_generator.py
│   │   ├── response_generator.py
│   │   └── domain/
│   │       ├── sales.py
│   │       ├── payment.py
│   │       ├── inventory.py
│   │       └── service.py
│   ├── graph/
│   │   ├── workflow.py
│   │   └── nodes/
│   │       ├── bsga.py
│   │       ├── moa.py
│   │       ├── memory.py
│   │       ├── tool_planner.py
│   │       ├── db.py             # DB node (was oracle.py)
│   │       ├── context_resolution.py
│   │       ├── option_generator.py
│   │       ├── domain_router.py
│   │       ├── confirmation.py
│   │       └── response.py
│   ├── output/
│   │   ├── conversation.py
│   │   └── options.py
│   ├── communication/
│   │   ├── layer.py              # Response Delivery Decision
│   │   ├── voice.py              # Voice Engine integration
│   │   └── delivery.py           # sendText / sendVoice tools
│   └── integrations/
│       └── whatsapp/
│           ├── adapter.py
│           ├── meta.py
│           └── normalizer.py
├── tests/
└── README.md
```

#### Acceptance Criteria

1. THE project SHALL be structured as a Python 3.11+ package under an `app/` root directory, where `app/` and each subpackage contains an `__init__.py` file.
2. THE app/ package SHALL contain at minimum the following subpackages: `config`, `models`, `db`, `memory`, `redis`, `llm`, `agents`, `graph`, `output`, `communication`, and `integrations/whatsapp`.
3. File names within a package SHALL NOT repeat the package name (e.g., `client.py` inside `db/`, NOT `supabase_client.py`; `customers.py` inside `db/tools/`, NOT `search_customers.py`).
4. Variable names SHALL NOT include vendor or package prefixes (e.g., `client` not `supabase_client`; `user_id` not `mem0_user_id`).
5. THE `db` subpackage SHALL be the only location that contains Supabase client imports and direct database operations.
6. THE `memory` subpackage SHALL be the only location that contains Mem0 client imports and direct memory operations.
7. THE `agents` subpackage SHALL contain one Python module per agent and a `specs/` directory containing .md configuration files for each agent.
8. IF a module outside `db/` contains a Supabase client import, or a module outside `memory/` contains a Mem0 client import, THEN THE project SHALL fail a static analysis boundary check.

### Requirement 16: Agent Configuration Model — .md Spec Files

**User Story:** As a developer, I want all agent behavior controlled through external .md configuration files that are loaded and injected at runtime, so that agent prompts can be iterated without code changes and each agent's identity is clearly documented.

#### Core Philosophy

No inline system prompts in agent Python modules or graph node files. All agent instructions, personality, and constraints are defined in .md files under `app/agents/specs/{agent_name}/` and loaded by the spec loader at runtime. This enables hot-reload in development and clear separation of agent logic from agent configuration.

#### Five-Part Agent Configuration

Each agent is configured through up to five .md files that are read, parsed, and injected into the agent's system prompt at runtime:

| File | Purpose | Required |
|------|---------|----------|
| `skill.md` | Defines what the agent can do — its capabilities, allowed operations, constraints, and boundaries | Yes |
| `backstory.md` | Provides the agent's context and background — why it exists, what system it belongs to, what it should understand about the business domain | Yes |
| `goal.md` | Defines the agent's primary objective — what it is trying to achieve with each interaction | Yes |
| `role.md` | Defines the agent's identity — who it is, how it should behave, its tone and communication style | Yes |
| `tools.md` | Lists and describes the tools available to the agent — what each tool does, when to use it, input/output expectations | Conditional (only for agents with tool access) |

#### Acceptance Criteria

##### Spec File Structure

1. EACH agent SHALL have a dedicated directory under `app/agents/specs/{agent_name}/` containing its .md configuration files.
2. EACH agent SHALL have at minimum four .md files: `skill.md`, `backstory.md`, `goal.md`, and `role.md`.
3. Agents with tool access (MOA, Tool_Planner, DB Oracle node) SHALL additionally have a `tools.md` file describing available tools.
4. THE .md files SHALL contain plain text and markdown formatting — no executable code, no JSON schemas embedded in fenced blocks.

##### Spec Loader

5. THE spec loader (`app/llm/specs.py`) SHALL read all .md files for a given agent and assemble them into a single system prompt injected at agent invocation time.
6. THE spec loader SHALL combine the five parts in this order: Role → Backstory → Goal → Skill → Tools (when present).
7. THE spec loader SHALL expose a `load(agent_name: str) -> AgentConfig` function that returns the assembled prompt and any parsed metadata.
8. IN development mode (SPEC_HOT_RELOAD=true), THE spec loader SHALL re-read .md files on every invocation without caching.
9. IN production mode, THE spec loader SHALL cache assembled prompts and reload only on explicit cache invalidation or restart.

##### Content Guidelines per File

10. `role.md` SHALL define: agent identity name, communication tone, personality constraints, and how the agent presents itself (e.g., "You are the Master Orchestrator. You are direct, clear, and business-focused.").
11. `backstory.md` SHALL define: system context the agent operates within, what MO-COS is, what the business domain looks like, and what other agents exist in the system.
12. `goal.md` SHALL define: the primary objective the agent pursues on every invocation (e.g., "Your goal is to classify whether this request belongs within the MO-COS business operating system.").
13. `skill.md` SHALL define: specific capabilities, allowed operations, constraints, boundaries, decision rules, and output format expectations.
14. `tools.md` SHALL define: each available tool by name, description, when to use it, expected inputs, and expected outputs.

##### CI Guards

15. THE project SHALL enforce via CI that no inline system prompt strings exist in `app/agents/` or `app/graph/nodes/` Python files — all agent instructions originate from .md spec files.
16. THE project SHALL validate at startup that every registered agent has the required .md files present in its specs directory.

##### Agent Spec Directories

17. THE following agents SHALL each have a spec directory with .md files: `moa`, `bsga`, `bla`, `tool_planner`, `context_resolution`, `option_generator`, `response_generator`, and domain agents (`domain/sales`, `domain/payment`, `domain/inventory`, `domain/service`).

### Requirement 17: Implementation Phases

**User Story:** As a project manager, I want the implementation divided into clear sequential phases, so that the system is built incrementally with each phase delivering testable functionality.

#### Acceptance Criteria

1. THE implementation SHALL proceed through six phases in order: Phase 1 (Conda + Supabase + Mem0 Foundation), Phase 2 (DB Oracle + Mem0 Memory), Phase 3 (LangGraph Skeleton), Phase 4 (Agent Specs + Core Agents), Phase 5 (Domain Agents + Confirmation), and Phase 6 (Communication Layer + WhatsApp + Hardening).
2. EACH implementation phase SHALL produce a testable increment of functionality before the next phase begins.
3. Phase 1 SHALL deliver environment.yml with all dependencies, Supabase migrations creating all tables with RLS policies, Mem0 client singleton, Redis client singleton, FastAPI health endpoint, and passing integration tests for each client connection.
4. Phase 2 SHALL deliver all DB_Oracle read and write tool implementations with Pydantic-validated inputs and outputs, audit_logs recording, idempotency enforcement, and passing unit tests for each tool.
5. Phase 3 SHALL deliver GraphState TypedDict, StateGraph node registration for all nodes, Redis checkpointer integration, interrupt_before configuration, and a passing end-to-end test demonstrating checkpoint save and resume.
6. Phase 4 SHALL deliver BSGA, BLA, MOA, Tool_Planner, and Context_Resolution agent implementations with .md spec files (skill.md, backstory.md, goal.md, role.md, tools.md) loaded by the spec loader, CI guards verifying no inline prompts, and passing tests verifying BSGA scope classification (in-scope forwarding and out-of-scope decline with no downstream agent invocation), BLA async event processing, and agent input/output contracts.
7. Phase 5 SHALL deliver Domain_Agent implementations (Sales, Payment, Inventory, Service), Confirmation_Gate interrupt workflow, and passing tests demonstrating the full confirm/reject/timeout cycle.
8. Phase 6 SHALL deliver Communication_Layer with sendText and sendVoice tools, Google_Voice_Engine STT/TTS integration, WhatsApp webhook and normalizer, static analysis boundary check, and passing end-to-end tests for text and voice flows across all channels.

### Requirement 18: Conversation Workspace

**User Story:** As a business owner, I want the conversation layer to function as my primary Business Workspace where I perform business operations in named sessions, so that my interactions are organized, contextual, and easy to navigate.

#### Core Philosophy

The conversational experience is inspired by Cursor Chat, not a simple messaging application. The conversation layer is the primary Business Workspace where users perform business operations. Users should be able to create and manage multiple conversation sessions.

#### Acceptance Criteria

##### Session Management

1. THE system SHALL allow users to create multiple named conversation sessions (e.g., "Morning Sales Update", "Inventory Review", "Customer Debt Follow-up", "Supplier Purchases", "Weekly Financial Review").
2. EACH conversation session SHALL maintain: conversation history (user messages and AI responses), AI understanding cards, confirmation history, operation checkpoints, and temporary session context.
3. THE system SHALL store conversation session history in Supabase via DB Oracle — NOT in Mem0.
4. Mem0 SHALL store only distilled communication preferences and long-term conversational patterns — NOT full session message history.

##### Conversation Interaction Types

5. THE conversation workspace SHALL support the following interaction types: user text messages, user voice notes, AI conversational responses, AI understanding cards, question cards (with selectable options), confirmation cards, and operation history cards.
6. THE conversation workspace SHALL feel like an AI business workspace, not a chatbot interface.

##### Question and Selection Cards

7. WHEN the AI requires information or detects ambiguity, THE system SHALL display selectable options as a question card with labeled choices and a free-form input option.
8. WHEN a question card is displayed, THE user SHALL be able to: click an option, continue typing, send a voice note, or provide additional context — free-form interaction SHALL always remain available alongside structured options.

##### Confirmation Cards

9. WHEN a business operation requires confirmation, THE system SHALL display a confirmation card showing: the operation summary, affected entities, quantities, payment type, and action buttons (Confirm, Modify, Cancel).
10. NO financial or operational action SHALL be executed before the user explicitly confirms via a confirmation card.

##### Operation History Cards

11. AFTER a confirmed operation executes successfully, THE system SHALL display an operation history card showing: operation status, summary of changes (before → after values), and action buttons (Revert Change, Continue From Here).

##### Real-Time Synchronization

12. AFTER an operation is confirmed and executed, THE system SHALL emit a realtime event stream to update all connected business views (Sales Page, Inventory Page, Customer Page, Business Timeline) immediately.
13. THE conversation workspace SHALL show a success confirmation while business views update in real-time via Supabase Realtime.

### Requirement 19: Operation Checkpoint System

**User Story:** As a business owner, I want every confirmed business operation to leave a transparent, reversible footprint, so that I can always understand what happened, when it happened, and undo mistakes.

#### Core Philosophy

This is NOT a complex Git-like version control system. The purpose is simple: every confirmed business operation should leave a transparent footprint that connects the operation to the conversation that created it.

#### Acceptance Criteria

##### Checkpoint Creation

1. WHEN a business operation is confirmed and executed, THE system SHALL create an operation checkpoint recording: which conversation session created the operation, the user message that initiated it, the AI understanding before execution, the business state before the change (relevant fields as JSON), the business state after the change (relevant fields as JSON), and the operation timestamp.
2. EACH operation checkpoint SHALL be stored in the operation_checkpoints table in Supabase via DB Oracle with business_id scoping.
3. THE operation checkpoint before_state and after_state SHALL capture only the fields directly affected by the operation (e.g., inventory quantity, customer balance) — NOT a full database snapshot.

##### Checkpoint Viewing

4. THE user SHALL be able to click any previous operation in the conversation to view its checkpoint details: operation type, changes (before → after values), and available actions.
5. THE operation history card SHALL display: a success indicator, a summary of what changed (e.g., "Inventory: 100 → 95 bags", "Customer Balance: ₦20,000 → ₦40,000"), and action buttons.

##### Revert Operation

6. WHEN a user requests to revert a previous operation, THE system SHALL display a confirmation card explaining the impact: what will be restored, what will be reduced/removed, and that the original operation will be marked as reverted (not deleted).
7. WHEN a revert is confirmed, THE system SHALL: reverse the business state changes, mark the original operation checkpoint as reverted, create a new operation checkpoint for the revert action, and update all affected business views in real-time.
8. THE system SHALL NOT silently delete history during a revert — all operations (original and reversal) SHALL remain in the audit trail.

##### Continue From Here

9. WHEN a user selects "Continue From Here" on a previous operation, THE system SHALL create a new conversation session branching from that operation's context point.
10. THE new session SHALL inherit the business context as it existed at that checkpoint, allowing the user to continue from that point (e.g., "Actually, this sale was cash, not credit").
11. THE system SHALL NOT implement complex branching or Git-style history — it SHALL create a simple new session with appropriate context.

##### Traceability

12. EVERY operation checkpoint SHALL be linked to: a conversation session, a specific message within that session, the user who initiated it, and the business_id for tenant isolation.
13. THE system SHALL provide the ability to query all operation checkpoints for a given session, a given business, or a given time range via DB Oracle tools.

### Requirement 20: AI-Generated Business Onboarding

**User Story:** As a new business owner, I want the system to learn about my business through a natural conversation rather than filling forms, so that I feel like I'm training a new employee rather than configuring software.

#### Core Philosophy

Traditional software asks: "Please configure your business before you can use the system."
MO-COS asks: "Tell me about your business, and I will learn how you operate while helping you."

The onboarding is NOT a setup wizard. It is the first training conversation between a business owner and their AI employee. The AI should listen first, understand, create an initial hypothesis, ask for confirmation, and continue learning through daily operations.

#### Acceptance Criteria

##### Welcome Conversation

1. AFTER registration, THE system SHALL automatically create a new conversation session titled "Getting to Know Your Business".
2. THE AI SHALL introduce itself naturally, explaining that it will help manage the business by learning how it operates, and that the user can communicate using voice or text.

##### Business Identity Collection

3. THE AI SHALL collect the business name through natural conversation and present it as an understanding card for user confirmation before proceeding.
4. THE business name confirmation SHALL use STRUCTURED_OPTIONS mode with "Confirm" and "Change" options.
5. THE business name MUST be confirmed before creating the business profile.

##### Business Story Conversation

6. THE AI SHALL ask the owner to describe the business naturally ("Tell me about your business as if you are explaining it to a new employee").
7. THE user SHALL be able to respond with voice notes or text.
8. THE system SHALL NOT ask the user to fill forms for: products, customers, inventory, services, payment methods, business workflows, or operational rules — these SHALL be learned naturally over time through real operations.

##### AI Initial Business Understanding

9. AFTER the business story conversation, THE AI SHALL analyze the conversation and produce an initial understanding summary presented as an understanding card, listing: business name, inferred business activities, and inferred business behaviors.
10. THE understanding card SHALL state: "This is my initial understanding and I will continue learning how your business operates."

##### AI Business Classification

11. THE AI SHALL infer the business category (Product Business, Service Business, or Hybrid Business) from the conversation — NOT by asking the user to select from a dropdown.
12. THE AI SHALL present its classification hypothesis as a STRUCTURED_OPTIONS card with "Correct" and "Change Classification" options.

##### Optional Additional Information

13. AFTER core understanding is confirmed, THE AI SHALL ask whether the user wants to add additional details (location, contact, operating hours, currency, etc.) with options "Yes, add more details" and "Skip for now".
14. IF the user provides additional information, THE AI SHALL summarize and request confirmation before saving.

##### Business Profile Creation

15. ONLY after user confirmation SHALL the system create the initial Business Profile containing: business identity (name + optional profile info), initial business understanding (category + summary + initial confidence level), and metadata (source: onboarding conversation, confirmation history, created timestamp).
16. THE initial Business Profile SHALL be treated by the BLA as: an initial business understanding, a starting hypothesis, and a source of evidence — NOT as a permanent configuration.

##### Immediate Business Operations

17. AFTER profile creation, THE system SHALL take the user directly to the Business Workspace (NOT an empty dashboard) with the AI ready to accept business operations.
18. THE AI SHALL communicate readiness: "Your business profile is ready. I will continue learning how your business operates every day. You can now tell me anything that happens in your business."

##### Continuous Learning From Onboarding

19. THE onboarding profile SHALL become the first evidence processed by the BLA's Business Evolution Engine.
20. THE BLA SHALL treat onboarding data with initial low-to-medium confidence (0.5-0.7) that increases as real business operations confirm the initial understanding.
21. THE system SHALL NEVER assume the onboarding profile is permanently correct — it MUST continue evolving through: real business operations, confirmed transactions, user corrections, and new conversations.

##### Onboarding Pollution Prevention

22. THE onboarding conversation SHALL pass through BSGA like any other conversation — if a user asks irrelevant questions during onboarding, BSGA SHALL block them.
23. ONLY confirmed business understanding from onboarding SHALL be persisted to AI Business Understanding storage.

### Requirement 21: Frontend Design System — Tendo Branding

**User Story:** As a user, I want the Tendo application to have a consistent, professional dark-mode design that feels like a premium AI workspace, so that the interface communicates reliability and modern sophistication.

#### Design Source

The frontend design system is derived from the sigmoid.ai codebase (`sigmoid.ai/src/index.css` and `sigmoid.ai/src/landing-atmosphere.css`). All colors, fonts, component patterns, and layout structures SHALL match this reference exactly.

#### Design Tokens

##### Typography

| Token | Value |
|-------|-------|
| `--font-sans` | `"Inter", ui-sans-serif, system-ui, -apple-system, sans-serif` |
| `--font-mono` | `"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` |

##### Color Palette

| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-brand-bg` | `#0a0a0a` | Page background |
| `--color-brand-canvas` | `#1c1c1c` | Canvas / raised area background |
| `--color-brand-surface` | `#171717` | Card/surface background |
| `--color-brand-surface-hover` | `#1f1f1f` | Surface hover state |
| `--color-brand-accent` | `#3ecf8e` | Primary accent (mint/emerald) |
| `--color-brand-accent-hover` | `#4ddb9b` | Accent hover state |
| `--color-brand-cta-fill` | `#1c6348` | CTA button fill |
| `--color-brand-cta-fill-hover` | `#247a5c` | CTA button hover fill |
| `--color-brand-cta-border` | `#3ecf8e` | CTA button border |
| `--color-brand-muted` | `#a1a1aa` | Muted/secondary text (zinc-400) |
| `--color-brand-border` | `rgb(255 255 255 / 0.1)` | Default border |
| `--color-brand-border-hover` | `rgb(255 255 255 / 0.16)` | Border hover |
| `--color-brand-border-subtle` | `rgb(255 255 255 / 0.06)` | Subtle/divider border |

##### Dashboard Surface Colors

| Surface | Color |
|---------|-------|
| Dashboard surface | `#141414` |
| Dashboard surface hover | `#181818` |
| Console surface | `#0f0f0f` |
| Card background | `zinc-900/90` |
| Input background | `zinc-950/60` |
| Input border | `zinc-800/80` |

#### Acceptance Criteria

##### Dark Mode Foundation

1. THE application SHALL use dark color scheme exclusively (`color-scheme: dark`) with `#0a0a0a` as the page background.
2. THE body text SHALL be `zinc-100` with font-family Inter and antialiased rendering.
3. ALL interactive elements SHALL use transition durations of 200–300ms with `ease-out` timing.

##### Component Classes

4. THE design system SHALL implement the following card classes:
   - `av-card`: `rounded-2xl`, `border border-white/10`, `bg-zinc-900/90`, `p-6`, 300ms transitions
   - `av-card-interactive`: Same as av-card with hover states (`border-white/[0.14]`, `bg-[#1f1f1f]/90`)
   - `av-dashboard-surface`: `rounded-xl`, `border border-zinc-800/90`, `bg-[#141414]`, `p-3`
   - `av-dashboard-surface-interactive`: Same with hover (`border-zinc-700/90`, `bg-[#181818]`)

5. THE design system SHALL implement the following button classes:
   - Primary: `h-[38px]`, `rounded-md`, `border-[#3ecf8e]`, `bg-[#1c6348]`, with emerald shadow glow on hover
   - Secondary: `h-[38px]`, `rounded-md`, `border-zinc-700/90`, `bg-zinc-900/60`
   - Emerald solid: `bg-[#3ecf8e]`, `text-[#0a0a0a]`, for prominent CTA actions
   - Toolbar variants: `h-7`, compact versions of primary/secondary for dense UI areas

6. THE design system SHALL implement input fields as: `rounded-md`, `border-zinc-800/80`, `bg-zinc-950/60`, `text-xs`, `text-zinc-200`, with `placeholder:text-zinc-600`.

##### Dashboard Layout

7. THE dashboard layout SHALL use a console app shell pattern: full viewport height (`h-dvh`), overflow hidden, with a fixed icon rail on the left.
8. THE icon rail SHALL be 52px wide, expand to 176px on hover with labels appearing, use `bg-[#0f0f0f]` with `border-r border-zinc-800/90`.
9. THE active rail item SHALL use `border-l-2 border-[#3ecf8e]` with `bg-white/[0.06]` and white text.
10. THE main content area SHALL have `border-l border-zinc-800/60`, `bg-[#0a0a0a]`, with `px-3 py-5 sm:px-5 sm:py-6 lg:px-8` padding and `max-w-4xl` content width.

##### Dashboard Grid and Atmosphere

11. THE dashboard SHALL use a subtle background grid pattern: `linear-gradient` grid lines at `rgb(255 255 255 / 0.008)` opacity, 44px spacing.
12. THE landing/marketing pages SHALL use the atmosphere system: sparse star specks, single soft mint radial wash (`rgba(62, 207, 142, 0.055)`), fine film grain at 5.5% opacity.

##### Stat Tiles and Data Display

13. Stat tiles SHALL use: `rounded-lg`, `border-zinc-800/90`, `bg-zinc-900/60`, with label in `text-[10px] uppercase tracking-wide text-zinc-600`, value in `text-lg font-bold tabular-nums text-white`.
14. Activity feed items SHALL use: `rounded-lg`, `border-zinc-800/60`, `bg-[#0f0f0f]/80`, with colored status dots (`#3ecf8e` for active, `zinc-500` for stopped, `sky-400` for billing, `amber-400` for alerts).

##### Glass and Feature Cards

15. Glass cards SHALL use: `rounded-[1.75rem]`, `border rgba(255,255,255,0.07)`, `bg rgba(28,28,28,0.52)`, `backdrop-filter blur(18px)`, with inner micro-grid pattern at 16px spacing.

##### Typography Scale

16. THE typography system SHALL use:
   - Hero titles: `font-bold`, `tracking-[-0.03em]`, white
   - Page titles: `font-bold`, `tracking-[-0.02em]`, white
   - Kickers: `text-[11px]`, `font-semibold`, `uppercase`, `tracking-[0.22em]`, `text-zinc-500`
   - Body: `text-sm` (14px), `text-zinc-200`
   - Muted/secondary: `text-zinc-500` or `text-zinc-600`
   - Monospace: JetBrains Mono for code, terminal, and data values

##### Tendo-Specific UI Adaptations

17. THE Tendo conversation workspace SHALL adapt the dashboard layout: icon rail for navigation (Conversations, Business, Inventory, Customers, Analytics), main area as the active conversation, with `av-dashboard-surface` for message cards and confirmation cards.
18. THE AI understanding cards, confirmation cards, and operation cards SHALL use `av-card-interactive` styling with the mint accent for confirmed states and `amber-400` for pending states.
19. THE option selection buttons in structured responses SHALL use `av-btn-secondary` with `av-btn-primary` for the recommended/default option.
20. THE voice recording indicator SHALL use the mint accent color (`#3ecf8e`) with a pulsing animation at 1.5s interval.

##### Technology Stack

21. THE frontend SHALL be built with: React, TypeScript, Tailwind CSS v4 (@tailwindcss with @theme), React Router, and Vite as the build tool.
22. THE frontend SHALL use the same Tailwind @theme configuration as the sigmoid.ai reference for design token parity.
