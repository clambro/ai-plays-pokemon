# Project Architecture

## Modular, Async, and Type-Safe

- **Async Design Patterns**: How the entire system operates asynchronously with asyncio
- **Type Safety with Pydantic**: Model validation, serialization, and state management
- **Modular Component Design**: Separation of concerns between agent, emulator, memory, and streaming
- **Dependency Injection**: How services are injected and managed throughout the workflow. Issues with init files. Always messier than I expect.

## Pyboy Emulator Integration

- **PyBoy Wrapper Architecture**: Custom YellowLegacyEmulator class and async integration
- **Game State Parsing**: Memory address mapping and real-time state extraction
- **Save State Management**: Loading and saving game states for testing and recovery

## Junjo Workflow and State Management

- [Link to workflow document](docs/workflow.md)
- Link to Junjo
- Why Junjo is great: Async and type safe, unopinionated
- **State Flow**: AgentState, AgentStore, and subflow state relationships
- **State Persistence**: How state is maintained across workflow iterations

## Database Design and Storage

- DB logic is extremely basic, and a lot of this could really be in memory, but it didn't feel complete without a DB. It makes auditing a lot easier though.
- Repository pattern
- **SQLAlchemy Integration**: Async database operations and model definitions
- Purpose of the DB is for long term storage of AI memory objects, as well as tracking and auditing LLM outputs and costs

## Backup and Restore Logic

- **Automatic Backup Strategy**: Periodic backups every 100 iterations
- **Backup Contents**: Agent state, game state, and complete database snapshots
- **Restore Mechanisms**: Loading from specific backups or latest available
- **Disaster Recovery**: Handling crashes and manual exits with automatic backups
- **Backup Organization**: Timestamped folders and iteration tracking
- **Storage Management**: Backup cleanup and disk space considerations. Pretty inefficient

## LLM Integration

- **Gemini Service Architecture**: Async API wrapper with retry logic
- **Model Selection**: Flash vs Pro models and cost optimization
- **Prompt Engineering**: System prompts, user prompts, and structured outputs
- **Response Parsing**: Pydantic schema validation and structured data extraction
- Why Gemini? Pydanic integration and free money.

## AI Memory Architecture

- **Three-Tier Memory Design**: Raw, summary, and long-term memory relationships
- **RAG Implementation**: Embedding generation, cosine similarity, and retrieval

## Live Game State Visualization

- **Web Server Architecture**: aiohttp-based real-time server implementation
- **State Synchronization**: How agent and game state are pushed to the frontend
- **Asset Management**: Static file serving for images, CSS, and JavaScript
- **Frontend Design**: HTML, CSS, and JavaScript for the streaming interface

## Testing Strategy

- Junjo Server
- **Test Organization**: Unit vs integration test separation and naming conventions, and meta testing.
- **Save State Management**: How game states are captured and used for testing
- Could be better, but evals are hard for this
