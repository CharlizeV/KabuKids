# System Architecture Overview

## 1. Introduction

KabuKids is a desktop application designed to facilitate engaging meal-time interactions for children through an AI-powered conversational companion. The system integrates multiple artificial intelligence and machine learning components to provide real-time conversation, emotion recognition, and personalized meal tracking. This document presents a comprehensive overview of the system architecture, detailing the layered design, component interactions, and data flow patterns.

## 2. Architectural Overview

The system follows a layered architecture pattern, organized into four primary layers: the Presentation Layer, Business Logic Layer, AI/ML Processing Layer, and Data Persistence Layer. This separation of concerns enables modularity, maintainability, and scalability of the system components.

### 2.1 System Layers

The architecture is structured as follows:

**Presentation Layer**: Handles all user interface interactions through Kivy-based screens and widgets, implementing a screen-based navigation model with state management.

**Business Logic Layer**: Manages application state, orchestrates meal flow workflows, and coordinates between UI components and backend services.

**AI/ML Processing Layer**: Integrates multiple machine learning models for speech recognition, natural language processing, text-to-speech synthesis, and facial expression recognition, operating in a parallel processing paradigm.

**Data Persistence Layer**: Provides database operations through MongoDB Atlas, managing user profiles, meal records, and conversation histories.

## 3. Presentation Layer Architecture

### 3.1 User Interface Framework

The presentation layer is built using Kivy 2.0+, a cross-platform Python framework that enables rapid UI development with declarative layout definitions. The application employs a ScreenManager pattern for navigation, where each functional unit is represented as a discrete Screen class.

### 3.2 Screen Hierarchy and Navigation

The application implements a state machine-based navigation model with the following screen hierarchy:

- **Authentication Screens**: `SplashScreen`, `LoginPage`, `MakeAccountPage`
- **Main Application Screens**: `DashboardPage`, `ProfilePage`, `EditProfilePage`
- **Meal Flow Screens**: `InputIngredientsBMPage`, `PortionSizeBeforePage`, `SessionPage`, `PortionSizeAfterPage`, `InputIngredientsAMPage`
- **Reporting Screens**: `ReportPage`, `TranscriptPage`

Navigation between screens is managed by the `WindowManager` (ScreenManager), which maintains the current screen state and handles transitions. Each screen implements lifecycle hooks (`on_pre_enter`, `on_enter`, `on_leave`) for state initialization and cleanup operations.

### 3.3 UI Component Architecture

The UI follows a widget-based composition model where complex screens are constructed from reusable components:

- **Custom Widgets**: `MealItem` (meal list entries), `ColoredCheckBox` (custom checkbox styling)
- **Layout Containers**: BoxLayout, GridLayout for organizing child widgets
- **Data Binding**: Kivy Properties (StringProperty, ListProperty) enable automatic UI updates when underlying data changes

### 3.4 State Management in Presentation Layer

The presentation layer maintains application state through:

- **Application-level State**: `App.current_user` stores the authenticated user document
- **Global Meal State**: `CURRENT_MEAL` dictionary tracks the current meal session data
- **Report Cache**: `SAMPLE_REPORTS` dictionary caches fetched meal reports for efficient UI updates

State synchronization between screens is achieved through property bindings and event-driven updates, ensuring consistent data representation across the application.

## 4. Business Logic Layer Architecture

### 4.1 State Management Services

The business logic layer provides centralized state management through the `services/models.py` module, which defines:

- **Meal State Functions**: `init_current_meal()`, `clear_current_meal()` for managing meal session lifecycle
- **Data Fetching Functions**: `fetch_reports_for_user()` for asynchronous retrieval of user meal reports
- **Global State Variables**: `CURRENT_MEAL`, `SAMPLE_REPORTS` for cross-module state sharing

### 4.2 Meal Flow Orchestration

The meal tracking workflow is orchestrated through a sequential state machine pattern:

1. **Pre-Meal Phase**: 
   - Ingredient input collection (`InputIngredientsBMPage`)
   - Portion size image capture before meal (`PortionSizeBeforePage`)

2. **During-Meal Phase**:
   - Interactive conversation session (`SessionPage`)
   - Real-time transcript recording
   - Emotion tracking and display

3. **Post-Meal Phase**:
   - Portion size image capture after meal (`PortionSizeAfterPage`)
   - Food completion tracking (`InputIngredientsAMPage`)
   - Meal document assembly and persistence

Each phase updates the global `CURRENT_MEAL` state, which is ultimately merged and persisted to the database upon meal completion.

### 4.3 Data Flow Patterns

The business logic layer implements several data flow patterns:

- **Unidirectional Data Flow**: UI events trigger state updates, which propagate to dependent components
- **Asynchronous Operations**: Database queries execute in background threads to prevent UI blocking
- **Callback-based Communication**: Asynchronous operations use callback functions to update UI upon completion

## 5. AI/ML Processing Layer Architecture

### 5.1 Component Architecture

The AI/ML layer consists of four primary processing components, each implemented as an independent module:

1. **Speech-to-Text (STT) Module** (`mainsession/stt.py`)
2. **Large Language Model (LLM) Module** (`mainsession/llm.py`)
3. **Text-to-Speech (TTS) Module** (`mainsession/tts.py`)
4. **Facial Expression Recognition (FER) Module** (`mainsession/fer.py`)

### 5.2 Parallel Processing Architecture

The conversation session implements a parallel processing architecture where audio capture and facial expression analysis execute concurrently:

```
┌─────────────────────────────────────────┐
│         Main Session Loop               │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Audio Thread │  │  FER Thread  │   │
│  │              │  │              │   │
│  │ - Record     │  │ - Capture    │   │
│  │ - Transcribe │  │ - Analyze    │   │
│  │ (30s timeout)│  │ (5s duration)│   │
│  └──────┬───────┘  └──────┬───────┘   │
│         │                  │           │
│         └────────┬─────────┘           │
│                  │                     │
│         ┌────────▼─────────┐          │
│         │  Combine Inputs  │          │
│         │  (text + emotion)│          │
│         └────────┬─────────┘          │
│                  │                     │
│         ┌────────▼─────────┐          │
│         │  LLM Generation   │          │
│         └────────┬─────────┘          │
│                  │                     │
│         ┌────────▼─────────┐          │
│         │  TTS Synthesis    │          │
│         └───────────────────┘          │
└─────────────────────────────────────────┘
```

This architecture enables real-time responsiveness by processing audio and video inputs simultaneously, reducing overall latency in the conversation loop.

### 5.3 Speech-to-Text Component

The STT module utilizes OpenAI's Whisper model (Base variant) through the Hugging Face Transformers library. The implementation features:

- **Voice Activity Detection (VAD)**: RMS-based energy thresholding to detect speech onset
- **Adaptive Recording**: Continuous audio capture with silence detection (2-second silence threshold)
- **Timeout Handling**: 30-second maximum wait time for speech detection
- **Streaming Processing**: Chunk-based audio processing (0.2-second chunks) for real-time responsiveness

The module initializes the ASR pipeline on import, enabling fast inference during conversation sessions.

### 5.4 Large Language Model Integration

The LLM module integrates with Ollama, a local LLM inference server, using the `qwen2.5:7b` model. Key architectural features include:

- **Conversation History Management**: JSON-based persistence with automatic history trimming (6000 character limit)
- **Context Injection**: System messages containing child profile data, preferences, and conversation guidelines
- **Response Parsing**: Structured extraction of response text and emotion labels from LLM output
- **Fallback Mechanism**: Predefined question bank for graceful degradation when LLM inference fails

The conversation context is dynamically constructed from:
- Child profile data (name, age, gender, likes, dislikes, goals)
- Current meal ingredients
- Conversation history
- System-defined behavior guidelines

### 5.5 Text-to-Speech Component

The TTS module employs the Kokoro TTS pipeline with the `af_sky` voice profile, designed for child-friendly interactions. The implementation:

- **Streaming Synthesis**: Generator-based audio production for low-latency playback
- **Real-time Playback**: Direct audio output via sounddevice library
- **Sample Rate**: 24kHz audio output for high-quality speech

### 5.6 Facial Expression Recognition Component

The FER module implements emotion detection using the `trpakov/vit-face-expression` Vision Transformer model. The architecture includes:

- **Face Detection**: OpenCV Haar Cascade classifier for face localization
- **Temporal Sampling**: Frame capture over 5-second intervals (0.1-second sampling rate)
- **Emotion Aggregation**: Top-2 most common emotions from sampled frames
- **Robustness**: Handles cases where no face is detected or FER pipeline fails

The module processes video frames in real-time, extracting facial regions and classifying emotions to provide contextual information for the LLM's response generation.

### 5.7 Conversation Engine Architecture

The conversation engine (`SessionPage` in `screens/meal_flow.py`) orchestrates all AI/ML components within a threaded execution model:

**Initialization Phase**:
1. Load child profile from MongoDB
2. Initialize TTS pipeline
3. Initialize camera capture
4. Reset conversation history with personalized system context
5. Start main conversation loop in background thread

**Main Loop Execution**:
1. Spawn parallel threads for audio capture and FER analysis
2. Wait for thread completion with timeout mechanisms
3. Combine transcribed text and detected emotions
4. Generate LLM response with combined context
5. Parse response for text and emotion labels
6. Synthesize speech output
7. Update transcript and UI emotion display
8. Repeat until session termination

**Cleanup Phase**:
1. Generate conversation analysis (recommendations, disliked foods)
2. Generate meal summary
3. Assemble final meal document
4. Release camera resources
5. Store meal data in global state for persistence

### 5.8 Context Management

The system maintains conversation context through a hierarchical context injection strategy:

1. **System-level Context**: Core Kabu personality and behavior guidelines
2. **User-level Context**: Child-specific information (demographics, preferences, goals)
3. **Session-level Context**: Current meal ingredients and conversation history
4. **Turn-level Context**: Current user input and detected emotions

This multi-level context enables personalized, contextually-aware responses while maintaining conversation coherence.

## 6. Data Persistence Layer Architecture

### 6.1 Database Architecture

The system employs MongoDB Atlas, a cloud-hosted NoSQL database, for data persistence. The database connection is established using PyMongo with TLS/SSL encryption and server API version 1.

### 6.2 Data Model

The database schema consists of two primary collections:

**Children Collection**:
- Stores user profile information
- Fields: `_id`, `name`, `username`, `password`, `birthday`, `gender`, `likes`, `dislikes`, `goals`, `profile_picture`, `created_at`
- Indexed on `username` for authentication queries

**Meals Collection**:
- Stores meal session records
- Fields: `_id`, `user_id`, `date`, `start_time`, `end_time`, `transcript`, `summary`, `conversation_suggestions`, `ingredient_suggestions`, `food_before_meal`, `food_not_finished`, `portion_before_image`, `portion_after_image`, `created_at`
- Indexed on `user_id` for user-specific queries

### 6.3 Data Access Patterns

The system implements several data access patterns:

- **Synchronous Queries**: User authentication, profile retrieval
- **Asynchronous Queries**: Meal report fetching (executed in background threads)
- **Batch Operations**: Bulk meal retrieval for dashboard display
- **Document Updates**: Incremental updates to user preferences (e.g., dislikes array)

### 6.4 Conversation History Persistence

Conversation history is maintained in two forms:

1. **Session History**: JSON file (`conversation_history.json`) for LLM context during active sessions
2. **Persistent History**: Embedded within meal documents in MongoDB for long-term storage

This dual-persistence model enables efficient context management during sessions while maintaining historical records for analysis and reporting.

## 7. Inter-Layer Communication Patterns

### 7.1 Presentation-to-Business Logic Communication

Communication occurs through:
- **Direct Function Calls**: Screen classes invoke business logic functions
- **State Sharing**: Global variables (`CURRENT_MEAL`, `SAMPLE_REPORTS`) accessed by both layers
- **Event Callbacks**: Asynchronous operations use callback functions to update UI

### 7.2 Business Logic-to-AI/ML Communication

The business logic layer coordinates AI/ML components through:
- **Module Imports**: Direct import of AI/ML modules
- **Function Invocation**: Sequential calls to STT, LLM, TTS, FER functions
- **State Passing**: Meal state and user context passed to AI/ML components

### 7.3 AI/ML-to-Data Layer Communication

AI/ML components interact with the data layer through:
- **MongoDB Module**: `mainsession/mongodb.py` provides database operations
- **Profile Loading**: Child profile retrieved at session start
- **Meal Persistence**: Final meal document assembled and stored post-session

### 7.4 Data Layer Communication

The data layer provides:
- **Connection Pooling**: Single MongoDB client instance shared across modules
- **Collection Access**: Direct collection references for query operations
- **Error Handling**: Try-except blocks with fallback behaviors

## 8. Threading and Concurrency Architecture

### 8.1 Threading Model

The system employs a multi-threaded architecture with the following thread types:

1. **Main UI Thread**: Kivy's main event loop for UI rendering and user interaction
2. **Session Thread**: Background thread for conversation loop execution
3. **Audio Thread**: Parallel thread for speech recording and transcription
4. **FER Thread**: Parallel thread for facial expression analysis
5. **Database Thread**: Background threads for non-blocking database operations

### 8.2 Thread Synchronization

Thread synchronization is achieved through:

- **Thread Events**: `threading.Event` for session termination signaling
- **Thread Joins**: Timeout-based joins to prevent indefinite blocking
- **Shared State**: Thread-safe access to global state variables (with appropriate locking considerations)
- **Daemon Threads**: Background threads marked as daemon for automatic cleanup

### 8.3 Concurrency Patterns

The system implements several concurrency patterns:

- **Producer-Consumer**: Audio/FER threads produce data consumed by main session loop
- **Parallel Processing**: Audio and FER analysis execute concurrently
- **Asynchronous I/O**: Database operations in background threads prevent UI blocking

## 9. Error Handling and Resilience

### 9.1 Error Handling Strategy

The architecture implements a multi-level error handling strategy:

- **Component-level**: Try-except blocks in each module with fallback behaviors
- **Layer-level**: Error propagation with graceful degradation
- **Application-level**: User-facing error messages via popup dialogs

### 9.2 Resilience Mechanisms

Key resilience features include:

- **Model Fallbacks**: Predefined questions when LLM inference fails
- **Empty Result Handling**: Graceful handling of no speech, no face detection
- **Timeout Mechanisms**: Prevents indefinite blocking on audio/video operations
- **Resource Cleanup**: Guaranteed camera release and thread termination

## 10. Performance Considerations

### 10.1 Optimization Strategies

The architecture incorporates several performance optimizations:

- **Model Selection**: Lightweight models (Whisper Base, tiny variants) for faster inference
- **History Trimming**: Conversation history limited to 6000 characters to reduce LLM context size
- **Caching**: In-memory report cache (`SAMPLE_REPORTS`) for fast UI updates
- **Parallel Processing**: Concurrent audio/video processing reduces overall latency
- **Lazy Initialization**: ML models loaded on first use, not at application start

### 10.2 Performance Bottlenecks

Potential performance constraints include:

- **LLM Inference**: Local Ollama model requires sufficient RAM/CPU resources
- **Real-time Processing**: Audio transcription and FER analysis may lag on slower hardware
- **UI Thread Blocking**: Long-running operations must remain in background threads
- **Database Latency**: Network latency to MongoDB Atlas may affect query performance

## 11. Security Architecture

### 11.1 Authentication Mechanism

The system implements a simple username/password authentication model:
- Credentials stored in MongoDB Children collection
- Plaintext password storage (security improvement recommended)
- Session-based authentication via `App.current_user` state

### 11.2 Data Security

Security measures include:
- **TLS/SSL**: Encrypted connections to MongoDB Atlas
- **Certificate Validation**: Certifi library for SSL certificate management
- **Connection Timeouts**: 5-second timeout prevents indefinite connection attempts

### 11.3 Security Considerations

Areas for security enhancement:
- Password hashing (bcrypt or similar)
- Environment variable management for sensitive credentials
- Input validation and sanitization
- Session timeout mechanisms

## 12. Conclusion

The KabuKids system architecture demonstrates a well-structured, layered design that effectively integrates multiple AI/ML components with a user-friendly interface. The parallel processing architecture enables real-time conversational interactions, while the modular component design facilitates maintainability and extensibility. The separation of concerns across presentation, business logic, AI/ML, and data layers provides a solid foundation for future enhancements and scalability improvements.




