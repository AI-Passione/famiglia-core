# [1.6.0](https://github.com/AI-Passione/famiglia-core/compare/v1.5.0...v1.6.0) (2026-04-07)

### Structural Reorganization
* **Comms Module Refactor**: Flattened the `comms` directory by moving `queue.py` to the root and removing the redundant `common/` directory.
* **Script Optimization**: Moved `migrate_sop_to_ops.py` from `scripts/` to `src/famiglia_core/db/` for better cohesion with database operations.

### Features
* **Enhanced Communication Logging**: Implemented descriptive startup logs and summary reports for Slack and Mattermost agents, providing clear visibility into active vs. mock modes.
* **Early Environment Loading**: Relocated `load_dotenv()` in `main.py` to guarantee that all singleton services correctly ingest configuration on startup.

### Bug Fixes
* **Slack Enablement**: Fixed a race condition where Slack clients were initialized before environment variables were available in Docker environments.
* **Import Stabilization**: Systematically resolved `ModuleNotFoundError` exceptions across the entire codebase following the `comms` directory reorganization.
* **Test Suite Alignment**: Updated mock targets and import paths in the test suite to ensure 100% CI compliance with the new structure.

# [1.5.0](https://github.com/AI-Passione/famiglia-core/compare/v1.4.0...v1.5.0) (2026-04-02)


### Features

* add date column to operations table display ([71d9308](https://github.com/AI-Passione/famiglia-core/commit/71d9308cc736830f780d405cb85601afc42a79aa))
* add display_name field to SOP workflows with auto-generated ID support ([a851d47](https://github.com/AI-Passione/famiglia-core/commit/a851d4767dac279319c82de0ee9df1a4472cde90))
* add global operational view and intelligent polling for mission logs ([058a784](https://github.com/AI-Passione/famiglia-core/commit/058a78411f54f62198f112b94051f31e4aa18e64))
* add healthcheck to app service and update dependency conditions in docker-compose files ([afb6fb5](https://github.com/AI-Passione/famiglia-core/commit/afb6fb562c756328e295f44589063ca201d78720))
* add ID column to operations table and update associated tests to verify action rendering ([7f4585e](https://github.com/AI-Passione/famiglia-core/commit/7f4585ef8559fd027e16a2f7063434b13eab00d2))
* add support for creating new SOP categories via initialized protocol menu in SOPBuilder ([024de54](https://github.com/AI-Passione/famiglia-core/commit/024de5467744865afc881ce7e17392632ff2071a))
* implement animated premium tab navigation with icons and layout indicators in Operations module ([359cf60](https://github.com/AI-Passione/famiglia-core/commit/359cf60eae4e5535f0bf279ab1ef716f17b17ff4))
* implement conversation history API and integrate strategic dialogue feed into operations dashboard ([b69691f](https://github.com/AI-Passione/famiglia-core/commit/b69691fb566fcfb3d976d64ce3b620f005503d7e))
* implement dashboard data fetching with auto-refresh for mission logs and agent conversations ([d12d26c](https://github.com/AI-Passione/famiglia-core/commit/d12d26c7f07733658afbe717fad86f474dd136f8))
* implement paginated agent action ledger with filtering and backend API support ([4080fe0](https://github.com/AI-Passione/famiglia-core/commit/4080fe0453f13f45436cf0c07d70fa4f7e60b071))
* implement paginated system task feed in Operations module with auto-refresh functionality ([894df36](https://github.com/AI-Passione/famiglia-core/commit/894df36e5569462c939b7dcda3657c98ed552af2))
* implement SOP builder and manager modules with backend API support for workflow orchestration ([d1bd94d](https://github.com/AI-Passione/famiglia-core/commit/d1bd94d9b0225e794b526627168f422d69003bcf))
* implement SOP category management and backend API support for workflow execution ([adda26d](https://github.com/AI-Passione/famiglia-core/commit/adda26da04f90ff78ba3f10a0979a688ea8b408b))
* implement SOP execution route and update graph parser to support recursive directory traversal ([d33a70e](https://github.com/AI-Passione/famiglia-core/commit/d33a70edd7236f9dd0b42ce320f9690fd44e00f7))
* namespace operations API under /api/v1/operations and expand task query to include SOP executions ([781b2fc](https://github.com/AI-Passione/famiglia-core/commit/781b2fc93a84593340f0f74d9165274582fd618b))
* replace global view placeholder with operational metrics dashboard and remove ID prefixes from table rows ([f095fb4](https://github.com/AI-Passione/famiglia-core/commit/f095fb4269f1c64fb98dc2642a6101b58d911dec))

# [1.5.0](https://github.com/AI-Passione/famiglia-core/compare/v1.4.0...v1.5.0) (2026-04-02)

### Features

* **SOP Hub 1.0**: Implement structural tier persistence with `workflow_categories` database support and a category-driven UI rendering architecture.
* **Mission Command 2.0**: Overhaul the Operations dashboard into a tripartite command center featuring real-time Mission logs, Strategic Dialogue, and a Tool Action Ledger.
* **Operational Stability**: Implement a comprehensive frontend test suite with Vitest and React Testing Library, utilizing `data-testid` targeting and global animation mocking for 100% CI reliability.
* **Initialize Protocol**: Introduce a unified multi-action interaction menu for rapid SOP drafting and structural category expansion.



### Features

* activate all AI agents by updating the souls normalization migration script ([283d2c5](https://github.com/AI-Passione/famiglia-core/commit/283d2c5ad11a7673f2b9aa47d632d853f2845003))
* add avatar support for agents with static image serving and database integration ([5ff2936](https://github.com/AI-Passione/famiglia-core/commit/5ff29363d405f1d6c9631725a04edb9e1d7f66cf))
* add is_active toggle to agent configuration and update UI status display ([bdcef81](https://github.com/AI-Passione/famiglia-core/commit/bdcef81594d7bc22073c476f7d7f30f170aa6500))
* implement agent management API routes and frontend editing modal with avatar upload and capability syncing ([5a496c8](https://github.com/AI-Passione/famiglia-core/commit/5a496c80ce123d2d172475d078445ee139331eb1))
* implement AgentEditModal component and add comprehensive backend and frontend test suites ([821579f](https://github.com/AI-Passione/famiglia-core/commit/821579f12fd93d27bbc696c680836d95bb182933))

# [1.3.0](https://github.com/AI-Passione/famiglia-core/compare/v1.2.0...v1.3.0) (2026-04-01)


### Features

* add 'Settings' button to Sidebar component for improved navigation ([c2780a3](https://github.com/AI-Passione/famiglia-core/commit/c2780a3afc5dba4b806d0e20a3f3b351edfbad1f))
* add comprehensive unit tests for Slack and Mattermost clients and update test documentation ([d1ec024](https://github.com/AI-Passione/famiglia-core/commit/d1ec02487dc51b753be3af61ab0d32c0d9b344d4))
* add database migration script to initialize core user and agent management tables ([bb733f6](https://github.com/AI-Passione/famiglia-core/commit/bb733f63e27fcf2a919785a23dd7f5dcc539c382))
* add GitHub Pages deployment workflow and implement configurable CORS origins and API base URLs ([bd59957](https://github.com/AI-Passione/famiglia-core/commit/bd59957a7a2e7ad6aa683592a623eab1b81baba3))
* add localStorage support for app settings and implement settings management in the UI ([2ab5592](https://github.com/AI-Passione/famiglia-core/commit/2ab5592d78d267ffdc3e5e3cf874019ab6c8043a))
* add test for settings hydration from backend and synchronization with updates ([561be50](https://github.com/AI-Passione/famiglia-core/commit/561be5063eec1de5429f795014f74afdcea4e700))
* add unit tests for user settings retrieval and update endpoints in the backend API ([8a30575](https://github.com/AI-Passione/famiglia-core/commit/8a3057555462d34064720fa102a55d60f66d1c9c))
* change agent_id parameter from Query to Form in upload_file endpoint and update test client fixture ([a12a38f](https://github.com/AI-Passione/famiglia-core/commit/a12a38f9868a2e3a81ef9da2ad14050280a26a08))
* implement Agenda module with task and recurring task management views ([02861a9](https://github.com/AI-Passione/famiglia-core/commit/02861a959c6b2f42592392ba31511d75df4211d7))
* implement centralized user identity and platform-specific mapping tables ([77568ab](https://github.com/AI-Passione/famiglia-core/commit/77568ab4219e4c047b1a01966cf5dc10965635d6))
* implement direct streaming for file uploads and update test suite accordingly ([7c3851c](https://github.com/AI-Passione/famiglia-core/commit/7c3851cadd7cfc436deff992d9cb9840133d02bb))
* implement Engine Room dashboard for system telemetry and service monitoring ([5a14cd2](https://github.com/AI-Passione/famiglia-core/commit/5a14cd23a04eb1eec63322694f2d92fc54efe46f))
* implement Famiglia agent profile retrieval and UI integration ([e99dbd2](https://github.com/AI-Passione/famiglia-core/commit/e99dbd2fd39c3e3f2f62428259dfd2c7d524bd21))
* implement FastAPI-based command center backend with modular routing and user seeding utilities ([1d179a8](https://github.com/AI-Passione/famiglia-core/commit/1d179a84c7eec92c625ddc3bbb0c0443601e5036))
* implement interactive chat terminal with SSE streaming and add backend chat API test suite ([4e14119](https://github.com/AI-Passione/famiglia-core/commit/4e14119d285995f0ebd4df1f22424de46fe0e033))
* implement Lounge module to visualize agent activity and recent actions ([8078b93](https://github.com/AI-Passione/famiglia-core/commit/8078b935dc4497f57e7bad25f277fac44fcd657c))
* implement settings synchronization with backend API and enhance local storage management ([81958ca](https://github.com/AI-Passione/famiglia-core/commit/81958ca3ef849d0a9dc8edd0d51aa7c5fa611df0))
* implement Vitest testing suite for frontend modules with React Testing Library and JSDOM configuration ([b954dc8](https://github.com/AI-Passione/famiglia-core/commit/b954dc8d4652f9b0107c68fe7e733dbade3e2963))
* migrate issue templates to YAML format and add discovery and foundation templates ([bf87211](https://github.com/AI-Passione/famiglia-core/commit/bf87211920865a1bf431bd2d5e0fbaf072499440))
* refactor settings management to utilize user_service for loading and updating settings ([c657018](https://github.com/AI-Passione/famiglia-core/commit/c657018809e9e52befee211da03a151325aa82fd))
* reintroduce 'Settings' button in Sidebar component for enhanced user navigation ([c642fee](https://github.com/AI-Passione/famiglia-core/commit/c642fee6bfe0c2c76bbcada4adbb96f1d1ae71d5))
* set the default active tab to situation_room and update corresponding test case ([1a1bfad](https://github.com/AI-Passione/famiglia-core/commit/1a1bfadb82ee41745277d1e066840396114e35d9))
* update frontend test configuration and add CI pipeline for frontend validation ([c229568](https://github.com/AI-Passione/famiglia-core/commit/c22956836bc59cd2340534c1764ac3a119f7f053))
* update user settings management to utilize dedicated user_settings table for improved data handling ([331966f](https://github.com/AI-Passione/famiglia-core/commit/331966fce24fff11642e602f12883b69f2d27577))

# [1.2.0](https://github.com/AI-Passione/famiglia-core/compare/v1.1.0...v1.2.0) (2026-03-31)


### Features

* activate all AI agents in the Famiglia roster and update the database migration script ([f8a2c1d](https://github.com/AI-Passione/famiglia-core/commit/f8a2c1d))
* add CLI for backend management and testing, and update project to editable install mode ([5a15a89](https://github.com/AI-Passione/famiglia-core/commit/5a15a898c8361dd1d45d0092e0e99853b20ab4f4))

# [1.1.0](https://github.com/AI-Passione/famiglia-core/compare/v1.0.2...v1.1.0) (2026-03-31)


### Bug Fixes

* specify postgres database for psql connection in initialization scripts ([536c2a1](https://github.com/AI-Passione/famiglia-core/commit/536c2a132f68102e786095d2a2b2f453db578d3a))


### Features

* add Giuseppina agent, update documentation, and remove redundant vision file ([7130e8a](https://github.com/AI-Passione/famiglia-core/commit/7130e8a757547dcfa87d871f5969146794fe12a9))
* add step to create dummy .env file in test workflow ([4bd6190](https://github.com/AI-Passione/famiglia-core/commit/4bd619031ff6802a89b297dc112d85042d0bd1fe))
* uncomment and configure CI workflow for unit tests ([1b7b009](https://github.com/AI-Passione/famiglia-core/commit/1b7b009da996d39a9bb1ecf38316a75cb181f739))

## [1.0.2](https://github.com/AI-Passione/famiglia-core/compare/v1.0.1...v1.0.2) (2026-03-31)

## [1.0.1](https://github.com/AI-Passione/famiglia-core/compare/v1.0.0...v1.0.1) (2026-03-31)

# 1.0.0 (2026-03-31)


### Bug Fixes

* update command center backend path in entrypoint script ([0df60e9](https://github.com/AI-Passione/famiglia-core/commit/0df60e9a2ac3618c5dbf8d0d9d29a923162f67ae))


### Features

* add comprehensive test suite for agents, workflows, and integrations ([fe20fd7](https://github.com/AI-Passione/famiglia-core/commit/fe20fd7e56d0dbc09c5f75573f86b67eebba0c8b))
* add GitHub Actions workflow for Python testing and update test script in package.json ([7687ecb](https://github.com/AI-Passione/famiglia-core/commit/7687ecbbb148e2d1340700d067817256631482d0))
* add openai dependency and initialize project source directory ([d770991](https://github.com/AI-Passione/famiglia-core/commit/d77099135f8c23696fa09e2a92db081f7c7189fa))
* add pull request template to .github directory ([17b1ecf](https://github.com/AI-Passione/famiglia-core/commit/17b1ecf40090238c7ef61d3033aa8b3126ce485c))
* enable multi-platform builds and GitHub Actions caching in Docker workflows ([54cbc1a](https://github.com/AI-Passione/famiglia-core/commit/54cbc1a90b59f1e9675938aaad36521f0fdb33c9))
* implement agent orchestration framework with multi-agent support, LangGraph workflows, and integrated tooling for research, development, and analytics. ([d7522db](https://github.com/AI-Passione/famiglia-core/commit/d7522dbe187d3c7b7aafc928260ed0ddd28870d9))
* implement automated CI/CD pipeline with semantic-release and Docker staging/production workflows ([17e526f](https://github.com/AI-Passione/famiglia-core/commit/17e526f5f50d453f62b6443087b7fd917969f396))
* implement core agent orchestration, multi-platform messaging, and containerized deployment infrastructure ([4afb605](https://github.com/AI-Passione/famiglia-core/commit/4afb6057056c4fab6c9eb4030d4b8d2057f20ad5))
* implement observability stack with Prometheus, Loki, Promtail, Grafana, and Langfuse integration ([4986e55](https://github.com/AI-Passione/famiglia-core/commit/4986e553995f92b8db79137d850871508b265a89))
* initialize command center backend architecture with Slack and Mattermost integration support ([0edaa04](https://github.com/AI-Passione/famiglia-core/commit/0edaa040db3773259a28aaa9acb456063d721dda))
* initialize command center frontend with React, Tailwind CSS, and core UI modules ([0929da2](https://github.com/AI-Passione/famiglia-core/commit/0929da20296d74889ddc2bd150528e0d69d50b58))
* migrate db files from La Passione ([d9b6f22](https://github.com/AI-Passione/famiglia-core/commit/d9b6f22be99832e5d30a8711f8b2ce928ce0fd05))
