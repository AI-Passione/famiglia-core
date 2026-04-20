# [1.15.0](https://github.com/AI-Passione/famiglia-core/compare/v1.14.0...v1.15.0) (2026-04-20)


### Bug Fixes

* add sleep delay between manifest operations to prevent Slack internal errors ([8862d50](https://github.com/AI-Passione/famiglia-core/commit/8862d509bb52427566be947b6f3869e85f835f9d))
* correct spelling of Riccardo in Slack app manifest display names ([9f48237](https://github.com/AI-Passione/famiglia-core/commit/9f48237691f47bed7de36067e93d2ac121bba75d))
* fix breaking connection between frontend and PostgreSQL DB ([fe647e1](https://github.com/AI-Passione/famiglia-core/commit/fe647e1595ffd4e261ac770c7043a81f74ac874e))
* handle stale Slack app IDs by purging local references and falling back to re-creation ([ee45a49](https://github.com/AI-Passione/famiglia-core/commit/ee45a49d93ff780f96e2984c513b847701dfcad7))
* update default Slack OAuth callback base URL from port 3000 to 8000 ([8b00c9b](https://github.com/AI-Passione/famiglia-core/commit/8b00c9b9a41fcd8f29021f74bfa49a2226d20ff6))


### Features

* add app_id support to Slack connection storage and enable ngrok service in docker-compose ([1803452](https://github.com/AI-Passione/famiglia-core/commit/1803452d43951cc4ad162cded53d7cfed3edc81e))
* add channels:join scope to Slack provisioning configuration ([ab54791](https://github.com/AI-Passione/famiglia-core/commit/ab54791194b7765d7dc941de6a5e219c6c7ac137))
* add close and hard reset controls to SlackFamigliaWizard component ([3ac080a](https://github.com/AI-Passione/famiglia-core/commit/3ac080adca0de4f11f32ed364c05a072ee825806))
* add connection testing functionality for Ollama integration ([0a33953](https://github.com/AI-Passione/famiglia-core/commit/0a3395389ec9c1e27243a7bfb225b41cbde2bdbc))
* add console logging when skipping existing greeting provisioning in Slack ([1aeebdb](https://github.com/AI-Passione/famiglia-core/commit/1aeebdb3a45b8f64294ec4fd6d870efeb04350cf))
* add customizable full name field to user profile and update UI references ([e171d5c](https://github.com/AI-Passione/famiglia-core/commit/e171d5ce95cc7f76196ebc57cd973a69790b0d59))
* add fallback to stored bootstrap token in Slack provisioning route ([4d5d197](https://github.com/AI-Passione/famiglia-core/commit/4d5d197351a8a7f4f21ad976ab6764ce1240b035))
* add Giuseppina agent and update Slack app manifests and connection UI ([a106f54](https://github.com/AI-Passione/famiglia-core/commit/a106f5427aad3b3fbde512c25df363001c1811b4))
* add hard purge endpoint to delete all Slack-related credentials and update frontend UI accordingly ([b5b42bf](https://github.com/AI-Passione/famiglia-core/commit/b5b42bf4df9e9b86c84921979388e7f12d657266))
* add instructional UI for app installation and credential configuration in Connections module ([399e071](https://github.com/AI-Passione/famiglia-core/commit/399e071272995e195d81f8ce9b7435ddd0c15140))
* add market research workflow tests and improve task string cleaning logic ([05203b6](https://github.com/AI-Passione/famiglia-core/commit/05203b65bf37ea2410c9fd3068489d5139d1ba4b))
* add ngrok service for Slack HTTP mode and implement automated agent authentication routing ([1370b6f](https://github.com/AI-Passione/famiglia-core/commit/1370b6ff9d30c5a1c0d3702760908236a78f864f))
* add Ollama integration section to Connections component ([46f01a4](https://github.com/AI-Passione/famiglia-core/commit/46f01a44494684d01f3c095fac00910b63ed89d0))
* add refresh_token to connection schema and support explicit app_id in slack provisioning ([3706914](https://github.com/AI-Passione/famiglia-core/commit/37069149390cabd72b2819791e7321f5db77b973))
* add Slack authentication test and improve logging for channel provisioning operations ([abfeacf](https://github.com/AI-Passione/famiglia-core/commit/abfeacf9f5136ace640018f07bdcb206b0c4c8a3))
* add Slack success notification and redirect flow to connection settings ([762fcad](https://github.com/AI-Passione/famiglia-core/commit/762fcadb32035f2e4ce503cb5867a2b2559503f8))
* add Slack webhook support with HTTP event listener, transport configuration, and channel auto-join logic ([f7fafd4](https://github.com/AI-Passione/famiglia-core/commit/f7fafd436d0846fa5b71e8c175598aa62b130444))
* add Slack workspace synchronization feature with expanded app permissions and registry management ([52820a6](https://github.com/AI-Passione/famiglia-core/commit/52820a62881ed010bc9542ec14bc386d521e1e62))
* add support for reusing existing Slack bootstrap token from database ([4bc3de2](https://github.com/AI-Passione/famiglia-core/commit/4bc3de264d4d8eac9efbf9779c70e48df9092197))
* add support for Slack HTTP transport mode and update connection status UI ([a41e01c](https://github.com/AI-Passione/famiglia-core/commit/a41e01c15860c8f9ee4c4b67648ae34407d6dd1d))
* add support for static ngrok domains in docker-compose and update provisioning logic to resolve public URLs ([0cd1ff8](https://github.com/AI-Passione/famiglia-core/commit/0cd1ff8e94ffc36d2994f130f7f01cba7e9452f7))
* add unit tests for Ollama integration and user connections store ([69b2804](https://github.com/AI-Passione/famiglia-core/commit/69b280435b92ec6c6b31c29edd4f4f29931130c0))
* add validation check for NGROK_AUTHTOKEN in ngrok service startup ([5d47cae](https://github.com/AI-Passione/famiglia-core/commit/5d47cae5f298b0e8f6cf0210caa10a2b12abbd0d))
* configure frontend proxy, improve public URL detection for Slack provisioning, and add diagnostic scratch scripts ([1c455a1](https://github.com/AI-Passione/famiglia-core/commit/1c455a1d85bb8853fa7700fbcb393cbc8cfdde48))
* decouple connection authorization from socket status and update unique constraint on service connections ([8961cea](https://github.com/AI-Passione/famiglia-core/commit/8961cea28ce1bb884b34840e23fe0d1fe7998b49))
* enhance market research workflow with result delivery and web search API key handling ([2ac7791](https://github.com/AI-Passione/famiglia-core/commit/2ac7791576901a836cea0ac449e76d45ebbf166e))
* enhance Ollama API key resolution and improve web search error handling ([38d9f64](https://github.com/AI-Passione/famiglia-core/commit/38d9f64a44dca013c47930b337b4149e84f7dea7))
* enhance Ollama connection testing and update UI comment for clarity ([019edd9](https://github.com/AI-Passione/famiglia-core/commit/019edd9508f0bf88b7e2f03cb05ca2a088b1a623))
* enhance Slack client with Block Kit support, file uploads, and interactive action handling ([894e364](https://github.com/AI-Passione/famiglia-core/commit/894e3645e3887ccea23e0b2d8bd15ef2719934a2))
* enrich agent roster with Slack connectivity status and redesign assembly UI for improved onboarding flow ([0c6fb92](https://github.com/AI-Passione/famiglia-core/commit/0c6fb92497423b8834284e5033fada6dbe40d602))
* ensure Alfredo joins Slack channels before inviting agents and improve error handling for invitations ([bac21d4](https://github.com/AI-Passione/famiglia-core/commit/bac21d4de43ea3c83249943a7b980821833c5cfa))
* implement automated agent greeting workflow with scheduling and channel-specific provisioning logic ([1b98c3d](https://github.com/AI-Passione/famiglia-core/commit/1b98c3d6fa3d6b3a8a0446fd3cafe0cae4fc56e4))
* implement automated cleanup for deprecated Slack channels and update channel registry configuration ([1297108](https://github.com/AI-Passione/famiglia-core/commit/12971083a435c723552f869764ab4e852500697a))
* implement automated Slack App Configuration Token rotation with refresh token support ([cc19547](https://github.com/AI-Passione/famiglia-core/commit/cc195476838e7bcc804a06ca9b022dec23760f29))
* implement automated Slack onboarding redirect and enhanced progress UI for agent synchronization ([8375113](https://github.com/AI-Passione/famiglia-core/commit/837511328816a9bd30dfa2e6b138b6e7b50a24f3))
* implement automatic Slack workspace owner discovery and ensure owner is invited to new channels ([a94afe4](https://github.com/AI-Passione/famiglia-core/commit/a94afe43a6e1a3c10297904bf43efc799f4ef5c2))
* implement lazy client refresh and improve logging for Slack connection management and database decryption errors ([d37300e](https://github.com/AI-Passione/famiglia-core/commit/d37300e362c9c287708b4e82af84db5e498b4f7b))
* implement manual bot_id refresh and improve Slack event logging and handling logic ([9e96b99](https://github.com/AI-Passione/famiglia-core/commit/9e96b990050c3ef67b044230a57b1e0a1bd3be83))
* implement Ollama API key management in Connections component ([7bd6152](https://github.com/AI-Passione/famiglia-core/commit/7bd615202653690c6790c8621cb316a5c332f232))
* implement onboarding path selection for Slack integration and update honorific handling in UI components ([b05d78c](https://github.com/AI-Passione/famiglia-core/commit/b05d78c9e60f69cf9ebe23547a2e7818f5f60ea4))
* implement Slack channel consolidation and update provisioning logic for product strategy channel ([d355880](https://github.com/AI-Passione/famiglia-core/commit/d3558800dec2773638fdf1997810e93d68ecc30e))
* implement Slack multi-bot provisioning wizard and backend API endpoints ([9fb8f7f](https://github.com/AI-Passione/famiglia-core/commit/9fb8f7f56ff319f99a3159ddeab1d4f4272ad786))
* implement Slack provisioning transport mode detection and persist transport metadata in user connections store ([330c42e](https://github.com/AI-Passione/famiglia-core/commit/330c42e5ae9634e6b89342a995a03253fd7a6bd1))
* include public_url in connection status response ([ac64727](https://github.com/AI-Passione/famiglia-core/commit/ac64727c7360a372d1d3b6bbe1dc78d7c4e9f9fc))
* integrate Caddy as a reverse proxy with automatic SSL and update backend to support proxy headers ([b5bf6c5](https://github.com/AI-Passione/famiglia-core/commit/b5bf6c55fda5a5b6fc0edaac7bb7daa09d1b17e3))
* migrate Slack event handling to legacy bridge and update connection event URLs ([9fdc447](https://github.com/AI-Passione/famiglia-core/commit/9fdc447e239b1ccbdeb9aee3d45c0db604b2db4b))
* overhaul onboarding UI with step-by-step setup guide and copyable Slack manifest component ([dc746dc](https://github.com/AI-Passione/famiglia-core/commit/dc746dcf4c64442e2196965f8177f4da82288845))
* persist resolved Slack channel ID to database during provisioning if not already stored ([89834d6](https://github.com/AI-Passione/famiglia-core/commit/89834d678200426ed8eb7d3e985e1a4f5fb274b6))
* persist Slack bootstrap token to database and add provisioning fallback logic with improved error logging ([bf39e78](https://github.com/AI-Passione/famiglia-core/commit/bf39e783eee6bed83aa0751a39a26c61ce40f9ae))
* reorder and restore get_connection_status endpoint in Connections API ([d796b43](https://github.com/AI-Passione/famiglia-core/commit/d796b438369daf965b64be472e7f908f57f34f62))
* replace Ollama icon with SVG image in Connections component ([39a47d8](https://github.com/AI-Passione/famiglia-core/commit/39a47d84dd459ca446495d34d52c6ca83c9a38f2))
* replace static handshake description with dynamic agent initialization progress bar and status indicator ([e61b647](https://github.com/AI-Passione/famiglia-core/commit/e61b647498e131746e8ac4662f4d01e8aa298ee0))
* standardize Slack OAuth installation URLs and add utility script for agent credential retrieval ([373111e](https://github.com/AI-Passione/famiglia-core/commit/373111e993b5734ac9dd211937e5172609f6feb2))
* standardize Slack OAuth redirect URIs and update connection status UI in dashboard ([45bce97](https://github.com/AI-Passione/famiglia-core/commit/45bce97d979ad86e48792f46dfc89257e4bd0be3))
* update Fernet key management and improve key generation logic ([2b8b85f](https://github.com/AI-Passione/famiglia-core/commit/2b8b85fe2b3f717e8c91a3b5b789de6f6920d696))
* update market research workflow to deliver results to Directive Terminal and optional Slack notification ([4905c9f](https://github.com/AI-Passione/famiglia-core/commit/4905c9f25936e6c6986c82a974a0b0812441cf6b))
* update Ollama integration to use Gemma 3 (4B) model across agents and configurations ([d773bcf](https://github.com/AI-Passione/famiglia-core/commit/d773bcf1a832c0a6e017ab378246f968a09ddb63))
* update Slack token format documentation and add auth verification with manifest sanitization during provisioning ([695a2ea](https://github.com/AI-Passione/famiglia-core/commit/695a2ea879a30188b2f4a3bd523650173951aa06))

# [1.16.0](https://github.com/AI-Passione/famiglia-core/compare/v1.15.0...v1.16.0) (2026-04-20)

### UI/UX Enhancements
* **Automated Slack Onboarding**: Implemented auto-refresh logic in the Slack provisioner. The page now automatically redirects once all 8 agents are successfully authorized, streamlining the "Assembly" process.
* **Premium Feedback**: Added visual states to the progress bar and status text ("All Agents Secured!", "Redirecting...") to provide a smooth, premium transition experience.

# [1.15.0](https://github.com/AI-Passione/famiglia-core/compare/v1.14.0...v1.15.0) (2026-04-17)

### Slack Workspace Organization 2.0
* **Channel Consolidation**: Simplified the agent-specialized roster by merging Tech (DevOps, Code Reviews, Data Engineering), Analytics (Data Science), and Operations (Logistics) into focused channels.
* **Automatic Provisioning**: 
    * Implemented programmatic **Owner Discovery** to identify and invite the Primary Workspace Owner to all managed channels.
    * Added **Automatic Archiving** to purge deprecated channels from the workspace sidebar and database.
    * Renamed `#alfredo-command` to `#command-center` and standardizing agent assignments.
* **Specialized Roster**: Introduced dedicated `#admin`, `#alerts`, and `#incidents` channels for core Famiglia operations.

# [1.14.0](https://github.com/AI-Passione/famiglia-core/compare/v1.13.1...v1.14.0) (2026-04-14)


### Features

* enable allowedHosts in Vite development server configuration ([f118342](https://github.com/AI-Passione/famiglia-core/commit/f118342578e3842b40c75745b469284906c7a288))

## [1.13.1](https://github.com/AI-Passione/famiglia-core/compare/v1.13.0...v1.13.1) (2026-04-14)

# [1.13.0](https://github.com/AI-Passione/famiglia-core/compare/v1.12.0...v1.13.0) (2026-04-14)


### Bug Fixes

* update API_BASE to use relative path instead of window.location.origin for fallback ([9008162](https://github.com/AI-Passione/famiglia-core/commit/900816229a9c08d72e399f1b7ff585a25cc6ac9c))


### Features

* enhance terminal debugging with comprehensive logging and global config exposure ([a78f6bd](https://github.com/AI-Passione/famiglia-core/commit/a78f6bdaaa68802bd395adcf92b3997584c87b2a))

# [1.12.0](https://github.com/AI-Passione/famiglia-core/compare/v1.11.0...v1.12.0) (2026-04-14)


### Features

* allow overriding default model configuration via FAMIGLIA_MODELS_CONFIG environment variable ([71ddc6d](https://github.com/AI-Passione/famiglia-core/commit/71ddc6d53ef4e99598dd10b5fc59486d4c9cc47f))
* expose port 8000 in Dockerfile and update integrity tests to support backend-only configurations ([2329510](https://github.com/AI-Passione/famiglia-core/commit/2329510893b5996cabc93f9fa828f6b17daded9c))
* install Node.js and frontend dependencies in Dockerfile ([1a018c4](https://github.com/AI-Passione/famiglia-core/commit/1a018c4fd1180e186e6e68d20df2eda171de1d15))

# [1.11.0](https://github.com/AI-Passione/famiglia-core/compare/v1.10.0...v1.11.0) (2026-04-14)


### Features

* start Nginx in the background within entrypoint script ([8411352](https://github.com/AI-Passione/famiglia-core/commit/8411352c8d6b3206ec2816e929a0e0978a8883cc))
* update Dockerfile to include multi-stage frontend build and Nginx integration ([5fceedf](https://github.com/AI-Passione/famiglia-core/commit/5fceedf1e64bb33619e7469c60e5de1b4079975b))

# [1.10.0](https://github.com/AI-Passione/famiglia-core/compare/v1.9.0...v1.10.0) (2026-04-14)


### Features

* update engine room service to display available Ollama models in runtime detail ([7432b2e](https://github.com/AI-Passione/famiglia-core/commit/7432b2e2ba07502b11145ba29c081cd58afc2d8c))

# [1.9.0](https://github.com/AI-Passione/famiglia-core/compare/v1.8.0...v1.9.0) (2026-04-14)


### Features

* add health check aliases and refactor agent roster retrieval to use context store method ([d1c5ff9](https://github.com/AI-Passione/famiglia-core/commit/d1c5ff9be8675e1a7cd8f60e84faeb04003d8bb3))
* add Ollama service readiness check, improve model pull reliability, and add gemma4 support ([a042d25](https://github.com/AI-Passione/famiglia-core/commit/a042d25f46899415218f0b37d37bfadfe7d40e2a))
* implement Gemma 4 reasoning support with automated thought-block stripping and dynamic routing mode overrides. ([56cd98c](https://github.com/AI-Passione/famiglia-core/commit/56cd98ce67b4338216654322eb6fd6e945f660fc))
* implement readiness sentinel to synchronize Command Center API startup with engine initialization ([c969f6f](https://github.com/AI-Passione/famiglia-core/commit/c969f6f61ef24913199739da3dd274ae0b5fbf6d))
* upgrade base local LLM from Gemma 3 (4B) to Gemma 4 (E2B) across all agents and configurations ([0624728](https://github.com/AI-Passione/famiglia-core/commit/062472894c39b87a2870aebd417832f1a2347593))

# [1.7.2](https://github.com/AI-Passione/famiglia-core/compare/v1.7.1...v1.7.2) (2026-04-13)

### Core Intelligence
* **Model Upgrade**: Switched the base local LLM from `Gemma 3 (4B)` to `Gemma 4 (E2B)` across the entire ecosystem. This includes updates to the model registry, task routing (CHAT and SEARCH), and individual agent configurations for Tommy, Bella, Rossini, and Alfredo.
* **Environment Defaults**: Updated `docker-compose.yml` and `.env.example` to ensure new deployments utilize the upgraded model by default.
# [1.8.0](https://github.com/AI-Passione/famiglia-core/compare/v1.7.0...v1.8.0) (2026-04-10)


### Bug Fixes

* add array validation and fallback empty states to API data fetching across frontend components ([1d93009](https://github.com/AI-Passione/famiglia-core/commit/1d930098d258eb528cebc7d028c973b26b247aa2))
* add null checks and default values to UI components to prevent runtime errors with undefined data ([c189774](https://github.com/AI-Passione/famiglia-core/commit/c18977489b804dfa99940a952e067bb1a7f8bafc))
* update agent keyword matching to use word boundaries and add database keyword to riccardo map ([93ffcc0](https://github.com/AI-Passione/famiglia-core/commit/93ffcc07f30a590d5dcf50ab9929c3203570da94))
* update features directory path and correct API endpoint for graph retrieval ([64ed728](https://github.com/AI-Passione/famiglia-core/commit/64ed72826af0605e16547c20d78f884b03787564))


### Features

* add famigliaName support to settings and update backend API tests ([4c095b9](https://github.com/AI-Passione/famiglia-core/commit/4c095b944dc3c94836ba57384a3820785a58ff9d))
* add LatestMissions and OperationsHub UI modules to SituationRoom for enhanced mission tracking and directive execution. ([ae46ecc](https://github.com/AI-Passione/famiglia-core/commit/ae46ecc46c6d7a2053a59ff526d600987ad24ca7))
* add logo asset and refactor OpsPulse heartbeat animation to use motion.circle for better alignment ([d7259c3](https://github.com/AI-Passione/famiglia-core/commit/d7259c3f97c3360e9c5f3d05bca4ff96d34cf3c7))
* add metadata to agent state and update scheduling supervisor to handle serialized task records ([98fe07c](https://github.com/AI-Passione/famiglia-core/commit/98fe07c58c1428ca52a07257fb272c66b8d13aa7))
* add pending action approval UI and polling to OperationsHub ([baec8cd](https://github.com/AI-Passione/famiglia-core/commit/baec8cda895565c365d030f1669bd29c05bb691e))
* add specification field to DirectiveModal and collapse manual prompt section ([d5a91a9](https://github.com/AI-Passione/famiglia-core/commit/d5a91a995794a790b9aba02bb114107e45fe76f7))
* add support for URL-based intelligence filtering and enhance OpsPulse heartbeat animation ([54721d1](https://github.com/AI-Passione/famiglia-core/commit/54721d1a1e5974a005ab621a72834ee3c7abc948))
* broadcast mission dispatch logs to both command center and coordination channels with improved message deduplication in terminal context ([cb1524a](https://github.com/AI-Passione/famiglia-core/commit/cb1524a8da63b1294df4397c0b9698b7baa56b53))
* enable GitHub Sponsors for [@davnnis2003](https://github.com/davnnis2003) and update changelog for v1.7.1 ([54d469e](https://github.com/AI-Passione/famiglia-core/commit/54d469e10d15f4a1a86b55dfb73ace35ae417066))
* implement category-based tabbed navigation and compact layout for DirectiveModal ([a3e1fc9](https://github.com/AI-Passione/famiglia-core/commit/a3e1fc9122e93944efd4c48a65337f3eeb0aa914))
* implement directive execution API, add DirectivesTerminal UI component, and include comprehensive backend and frontend tests. ([c8e06dd](https://github.com/AI-Passione/famiglia-core/commit/c8e06dd96718646cf1670c32617610ebdc0ef623))
* implement DirectiveModal for manual and graph-based mission execution with global Toast notifications ([9d2c255](https://github.com/AI-Passione/famiglia-core/commit/9d2c255b1c0743b8b68ef003f0cb5fc69ec83a1a))
* implement global error boundary and add null-safety checks to UI components to prevent runtime crashes ([97715f3](https://github.com/AI-Passione/famiglia-core/commit/97715f33e1a45dd4845e02e0596128c780267da3))
* implement graph-based agent resolution and update task dispatch logging to the coordination channel ([26870e3](https://github.com/AI-Passione/famiglia-core/commit/26870e3b2e1af244d885d0473d0e41273d7c454e))
* implement notification system with backend API, database storage, and frontend provider integration ([9706ff5](https://github.com/AI-Passione/famiglia-core/commit/9706ff53e9754682c3998e0fade9c5e4a078d174))
* implement react-router-dom for navigation and add famigliaName setting to database and UI ([60b2ef6](https://github.com/AI-Passione/famiglia-core/commit/60b2ef619c24f13871e39a2598ac738da30ad7dd))
* implement real-time mission completion notifications and background polling for agent status updates. ([0eb8526](https://github.com/AI-Passione/famiglia-core/commit/0eb852641aae01c0696eee17f0282ac204c7bca5))
* implement terminal agent acknowledgement and remove redundant OperationsHub component ([7989dc2](https://github.com/AI-Passione/famiglia-core/commit/7989dc26645dc4e3d42a43a1e06d3098a5cce77c))
* implement unified app_notifications system with dedicated database table and frontend integration ([49afccd](https://github.com/AI-Passione/famiglia-core/commit/49afccd1c70be976783fe5bf97da22e09f12d30a))
* improve research topic extraction, fix pathing, and integrate Postgres checkpointer with thread-aware graph execution ([01364bc](https://github.com/AI-Passione/famiglia-core/commit/01364bccf3100c1b0cd15efe238d006b3f6b22a8))
* include message metadata in database queries and implement mission dispatch notifications in the terminal context ([9e1f45f](https://github.com/AI-Passione/famiglia-core/commit/9e1f45f90c655d99f59646854f4801022988f5e5))
* replace InsightsTicker with global agent notification polling in TerminalContext and backend ([5e75845](https://github.com/AI-Passione/famiglia-core/commit/5e75845c607e8cba9a0c0711a14f232a61980512))
* set active chat to command-center and update button label in DirectiveModal ([f799108](https://github.com/AI-Passione/famiglia-core/commit/f799108e4467df02e6accd6bae6ba31bc655c009))

# [1.7.1](https://github.com/AI-Passione/famiglia-core/compare/v1.7.0...v1.7.1) (2026-04-10)

### Operational
* **Sponsorship Enabled**: Officially launched the GitHub Sponsors integration specifically for Don Jimmy (@davnnis2003). Added `FUNDING.yml` to the `.github` directory to enable the "Sponsor" button on the repository.

# [1.7.0](https://github.com/AI-Passione/famiglia-core/compare/v1.6.0...v1.7.0) (2026-04-09)

### Architecture & Routing
* **Unified URL Routing**: Transitioned the Command Center from state-based tab switching to a robust URL-based routing system using `HashRouter`. This enables deep linking, browser navigation history (Back/Forward), and tab persistence across page refreshes.
* **Component Refactoring**: Decoupled the sidebar and main navigation from the local state, utilizing `NavLink` for automatic active state management.

### Features
* **Famiglia Personalization**: Introduced a user-configurable "Famiglia Name" setting. Users can now brand their ecosystem via the Personalization dashboard, with the name persisting across the Sidebar and top navigation.
* **Extended Multi-Agent UI**: Improved the "Intelligences" and "Terminal" access by standardizing their launch patterns from the unified sidebar.

### Stabilization
* **Settings Persistence**: Integrated the `famigliaName` field into the backend PostgreSQL schema and `UserService` logic, ensuring personalized branding is synchronized across the stack.
* **Test Suite Alignment**: Resolved regressions in the backend API tests caused by the settings schema expansion, restoring 100% CI pass rate.
# [1.7.0](https://github.com/AI-Passione/famiglia-core/compare/v1.6.0...v1.7.0) (2026-04-08)


### Bug Fixes

* add scrollTo fallback for JSDOM and update motion props filter in test environment ([6ca530a](https://github.com/AI-Passione/famiglia-core/commit/6ca530a2c8b432d09079a37bb9c9c77a9ee643e5))


### Features

* add intelligence-hub channel with dynamic agent routing and support for initial chat configuration ([18f9e19](https://github.com/AI-Passione/famiglia-core/commit/18f9e19d2b4e82dfd34132c183f365f9f22f1b65))
* add metadata and reference_id fields to intelligence model and update serialization logic for nested attributes ([9891cdd](https://github.com/AI-Passione/famiglia-core/commit/9891cddbe3a8830f0ffafd247f65e4a9dbce0276))
* expand intelligence categorization to include market research, prds, and projects with updated UI grouping and iconography ([f908c3e](https://github.com/AI-Passione/famiglia-core/commit/f908c3e26950ce2c86383e7096f679a1b51f6e36))
* expand intelligence items schema to support full Notion page metadata and rich UI rendering ([fd489e5](https://github.com/AI-Passione/famiglia-core/commit/fd489e57d6dc95a7c9dd64fd2c426261807d58f8))
* implement chat message persistence and history retrieval for web dashboard channels ([c1c1547](https://github.com/AI-Passione/famiglia-core/commit/c1c15477913afc78e1dda3bc8a6ed1485a3abddc))
* implement intelligence dashboard with Notion sync, real-time search, and markdown rendering ([8366f4c](https://github.com/AI-Passione/famiglia-core/commit/8366f4cb8348af15bb37c77288448137503a8abd))
* implement intelligence module with CRUD API, database schema, and service layer ([a8b9291](https://github.com/AI-Passione/famiglia-core/commit/a8b9291721df9035dce105e8e462dad88724d577))
* implement message threading support with backend persistence and frontend side panel UI ([72f39ec](https://github.com/AI-Passione/famiglia-core/commit/72f39ec36ef86493210c26026c9d3ddd81030b44))
* implement threading UI, scroll-to-bottom notifications, and associated component tests ([2013404](https://github.com/AI-Passione/famiglia-core/commit/2013404ec87a92fc2ad60983efe428c52ff083d0))
* integrate TerminalProvider and DirectivesTerminal into the Intelligence Center layout ([6550c5f](https://github.com/AI-Passione/famiglia-core/commit/6550c5f4c2801e688f2dce973b2a8d3905a03433))
* migrate Intelligences module to a standalone window and update build configuration ([c0ac005](https://github.com/AI-Passione/famiglia-core/commit/c0ac00527305376ba695a6627b779ef4ba647e4d))

# [1.6.0](https://github.com/AI-Passione/famiglia-core/compare/v1.5.0...v1.6.0) (2026-04-07)


### Bug Fixes

* rename riccado to riccardo, clean up unused assets, and implement terminal interface ([780750e](https://github.com/AI-Passione/famiglia-core/commit/780750e81f693eac7d881663c3b2e5d1e1111fd4))


### Features

* add personal directive and system prompt fields to user settings with souls.md integration ([c8301c0](https://github.com/AI-Passione/famiglia-core/commit/c8301c02371971003e66ee5627e88e843bfb5bf6))
* implement framer-motion transitions and layout animations for settings tab navigation ([a19dcdf](https://github.com/AI-Passione/famiglia-core/commit/a19dcdfc32a0a215c0b340e796d2d2d9f349434c))
* implement streaming response support in agents and update terminal UI to handle real-time chat updates via refs ([0148d43](https://github.com/AI-Passione/famiglia-core/commit/0148d434e8318b2e7435825f39afe09d35ab3f23))
* implement Terminal module with multi-channel chat and agent communication support ([7361d8f](https://github.com/AI-Passione/famiglia-core/commit/7361d8f251b1fecc4332ca9541f13e67fb30e480))
* implement TerminalContext to manage chat state, agent messaging, and real-time data synchronization ([7ea89d8](https://github.com/AI-Passione/famiglia-core/commit/7ea89d8fb200994c06c93704e21d6ae5208586f6))
* improve startup logging and move environment loading to main entry point to resolve initialization race conditions ([6036a44](https://github.com/AI-Passione/famiglia-core/commit/6036a4499bacf11d7b9434d3c9c71ef45be0d56b))
* propagate metadata through agent task completion and update response distributor logging ([bc78724](https://github.com/AI-Passione/famiglia-core/commit/bc7872427d0f81f5fed24aec09477ad6c7994e58))
* support recurring task creation in orchestration tools and reorganize sidebar navigation layout ([1fa5f24](https://github.com/AI-Passione/famiglia-core/commit/1fa5f241c58680f23c580065608cab0fe042b775))

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
