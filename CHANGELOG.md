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
