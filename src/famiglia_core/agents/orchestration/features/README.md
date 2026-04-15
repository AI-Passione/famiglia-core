# Agent Feature Modules

This directory contains specialized LangGraph-driven features organized by domain. These workflows are orchestrated by supervisors and executed by **Dr. Rossini**, **Riccardo**, and **Kowalski**.

## Table of Contents
1. [Model Selection & Resolution](#model-selection--resolution)
2. [Market Research Features (Rossini)](#market-research-features-rossini)
3. [Product Development Features (Rossini & Riccardo)](#product-development-features-rossini--riccardo)
4. [Analytics Features (Kowalski)](#analytics-features-kowalski)
5. [Universal Notion & Slack Formatting Standards](#universal-notion--slack-formatting-standards)

---

## Model Selection & Resolution

The orchestration layer enforces a **Proactive Model Resolution** strategy. Before a feature workflow begins, the Supervisor resolves the best available LLM based on system tiering and injects it into the agent state (`state["model_to_use"]`). This ensures all sub-nodes in a complex graph utilize a consistent, high-performance model.

### Availability Tiers
1.  **Tier 1 (Cloud - Gemini 2.0 Flash)**: Primary choice for complex reasoning and clinical analysis. Used when `GEMINI_API_KEY` is present.
2.  **Tier 2 (Local - Mistral 7B)**: Fallback for local-first environments or when cloud tokens are unavailable. Verified via Ollama service status.
3.  **Tier 3 (Local/Remote - Gemma 3)**: Global system fallback for basic orchestration and simple tasks.

---

## Market Research Features (Rossini)

Located in `market_research/`, focused on external intelligence and strategic ideation.

### 1. Market Research Workflow
Performs iterative web searches, curates insights into the **Intelligence Center**, generates innovative business proposals, and delivers results to the **Directive Terminal** (with an optional Slack notification to #Research-Insights).
- **File:** `market_research/market_research.py`
- **Tests:** `tests/agents/test_orchestration_features.py` (100% Logic Coverage)
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    perform_search(perform_search)
    refine_search_query(refine_search_query)
    curate_results(curate_results)
    save_to_intelligence(save_to_intelligence)
    generate_ideas(generate_ideas)
    deliver_results(deliver_results)
    __end__([__end__]):::last

    __start__ --> perform_search;
    perform_search -- "Error (retry < 2)" --> refine_search_query;
    refine_search_query --> perform_search;
    perform_search -- "Success / Final Attempt" --> curate_results;
    curate_results --> save_to_intelligence;
    save_to_intelligence --> generate_ideas;
    generate_ideas --> deliver_results;
    deliver_results --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

---

## Product Development Features (Rossini & Riccardo)

Located in `product_development/`, these features cover the full lifecycle from PRD to Pull Request.

### 1. PRD Drafting
Automates the creation of Product Requirement Documents by synthesizing Notion intelligence, GitHub repositories, and Web trends.
- **File:** `product_development/prd_drafting.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    understand_context(understand_context)
    gather_notion_intelligence(gather_notion_intelligence)
    gather_github_intelligence(gather_github_intelligence)
    gather_web_intelligence(gather_web_intelligence)
    summarize_notion(summarize_notion)
    summarize_github(summarize_github)
    summarize_web(summarize_web)
    synthesize(synthesize)
    draft_prd(draft_prd)
    save_to_notion(save_to_notion)
    notify_slack(notify_slack)
    __end__([__end__]):::last

    __start__ --> understand_context;
    understand_context --> gather_notion_intelligence;
    understand_context --> gather_github_intelligence;
    understand_context --> gather_web_intelligence;
    gather_notion_intelligence --> summarize_notion;
    gather_github_intelligence --> summarize_github;
    gather_web_intelligence --> summarize_web;
    summarize_notion --> synthesize;
    summarize_github --> synthesize;
    summarize_web --> synthesize;
    synthesize --> draft_prd;
    draft_prd --> save_to_notion;
    save_to_notion --> notify_slack;
    notify_slack --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

### 2. PRD Review & Iteration
Analyzes Notion comments and calibrates PRD updates using "System 2" thinking.
- **File:** `product_development/prd_review.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    discover(discover_prds)
    load_prd(load_prd_and_comments)
    summarize(summarize_feedback)
    evaluate(evaluate_feedback)
    update(update_prd)
    save(save_to_notion)
    reply(post_replies)
    notify(notify_slack)
    __end__([__end__]):::last

    __start__ -- "Scheduled" --> discover;
    __start__ -- "On-Demand" --> load_prd;
    
    discover -- "PRDs Found" --> load_prd;
    discover -- "No PRDs" --> __end__;
    
    load_prd -- "Page Not Found" --> notify;
    load_prd -- "Success" --> summarize;
    summarize --> evaluate;
    evaluate -- "Update Needed" --> update;
    evaluate -- "Skip Update (Reject/Skip)" --> reply;
    update --> save;
    save --> reply;
    
    reply -- "Next Page (Scheduled Mode)" --> load_prd;
    reply -- "Done" --> notify;
    
    notify --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

### 3. Milestone Creation
Synchronizes approved PRDs with GitHub by semantic deduplication of issues and milestones.
- **File:** `product_development/milestone_creation.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    load_prd(load_prd)
    select_repo(select_repo)
    parse_prd_into_plan(parse_prd_into_plan)
    check_existing(check_existing)
    create_items(create_items)
    mark_all_skipped(mark_all_skipped)
    notify_slack(notify_slack)
    __end__([__end__]):::last

    __start__ --> load_prd;
    load_prd -- "continue" --> select_repo;
    load_prd -- "error" --> notify_slack;
    select_repo -- "continue" --> parse_prd_into_plan;
    select_repo -- "error" --> notify_slack;
    parse_prd_into_plan -- "continue" --> check_existing;
    parse_prd_into_plan -- "error" --> notify_slack;
    
    check_existing -- "create" --> create_items;
    check_existing -- "synced" --> mark_all_skipped;
    
    create_items --> notify_slack;
    mark_all_skipped --> notify_slack;
    notify_slack --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

### 4. Grooming (Rossini ↔ Riccardo)
Facilitates collaborative grooming where Rossini sets priorities and Riccardo provides technical effort estimations (XS-XL).
- **File:** `product_development/grooming.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    load_context(load_context)
    fetch_github_state(fetch_github_state)
    rossini_review(rossini_review)
    riccardo_review(riccardo_review)
    synthesize(synthesize)
    debate_in_github(debate_in_github)
    consolidate(consolidate_and_refine)
    apply_updates(apply_updates)
    notify_slack(notify_slack)
    __end__([__end__]):::last

    __start__ --> load_context;
    load_context --> fetch_github_state;
    fetch_github_state --> rossini_review;
    fetch_github_state --> riccardo_review;
    rossini_review --> synthesize;
    riccardo_review --> synthesize;
    synthesize --> debate_in_github;
    debate_in_github --> consolidate;
    consolidate --> apply_updates;
    apply_updates --> notify_slack;
    notify_slack --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

### 5. Code Implementation & PR Review
Leverages coder models (e.g., Qwen 2.5 Coder) to implement groomed issues and address human feedback on open Pull Requests.
- **File:** `product_development/code_implementation.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    load_context(load_context)
    fetch_groomed_issues(fetch_groomed_issues)
    generate_and_create_prs(generate_and_create_prs)
    fetch_open_prs_with_comments(fetch_open_prs_with_comments)
    address_pr_comments(address_pr_comments)
    notify_slack(notify_slack)
    __end__([__end__]):::last

    __start__ --> load_context;
    load_context --> fetch_groomed_issues;
    fetch_groomed_issues --> generate_and_create_prs;
    generate_and_create_prs --> fetch_open_prs_with_comments;
    fetch_open_prs_with_comments --> address_pr_comments;
    address_pr_comments --> notify_slack;
    notify_slack --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

---

## Analytics Features (Kowalski)

Located in `analytics/`, these features focus on clinical data ingestion and Evidence-Driven Analysis.

### 1. Ad-hoc Data Ingestion & Inspection
Enables ingestion of CSV, Parquet, or JSON files provided via Slack into the persistent **DuckDB Data Warehouse**.
- **File:** `analytics/data_ingestion.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    analyze_request(analyze_request)
    perform_ingestion(perform_ingestion)
    verify_ingestion(verify_ingestion)
    final_report(final_report)
    __end__([__end__]):::last

    __start__ --> analyze_request;
    analyze_request --> perform_ingestion;
    perform_ingestion --> verify_ingestion;
    verify_ingestion --> final_report;
    final_report --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

### 2. Simple Data Analysis
Provides rapid ad-hoc insights and numerical snapshots with SCD (Slow-Changing Dimension) awareness.
- **File:** `analytics/simple_data_analysis.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    detect_intent(detect_intent)
    run_discovery(run_discovery)
    verify_data(verify_data)
    inform_missing_data(inform_missing_data)
    query_duckdb(query_duckdb)
    generate_report(generate_report)
    save_to_notion(save_to_notion)
    __end__([__end__]):::last
 
    __start__ --> detect_intent;
    detect_intent --> run_discovery;
    run_discovery --> verify_data;
    
    verify_data -- "Needs Data" --> inform_missing_data;
    verify_data -- "Has Data" --> query_duckdb;
    
    inform_missing_data --> __end__;
    query_duckdb --> generate_report;
    generate_report -- "Ad-hoc" --> __end__;
    generate_report -- "In-depth" --> save_to_notion;
    save_to_notion --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

### 3. Deep Dive Analysis
An iterative, hypothesis-driven analytical workflow for complex investigations.
- **File:** `analytics/deep_dive_analysis.py`
- **Workflow Architecture:**
```mermaid
graph TD;
    __start__([__start__]):::first
    run_discovery(run_discovery)
    form_hypotheses(form_hypotheses)
    execute_drilldown(execute_drilldown)
    synthesize_findings(synthesize_findings)
    generate_report(generate_report)
    save_to_notion(save_to_notion)
    __end__([__end__]):::last

    __start__ --> run_discovery;
    run_discovery --> form_hypotheses;
    form_hypotheses --> execute_drilldown;
    
    execute_drilldown -- "Loop < 3" --> execute_drilldown;
    execute_drilldown -- "Complete" --> synthesize_findings;
    
    synthesize_findings --> generate_report;
    generate_report --> save_to_notion;
    save_to_notion --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

---

## Universal Notion & Slack Formatting Standards

To ensure a premium and consistent experience across the Famiglia's communication channels, all agents follow these standards:

### Slack Formatting
- **Bold Headers**: Use `*Header Name*` on its own line.
- **Bullets**: Use the `• ` (bullet point symbol) for list items. This provides the best cross-platform indentation.
- **Zero-Preamble Reporting**: Reports must start directly with the header, ignoring any greetings or conversational noise.
- **Code Highlights**: Use backticks (`) for column names, table names, and specific data values.

### Notion Rendering
- **Advanced Markdown Support**: Custom parser correctly renders bolding, lists, inline code, tables, and blocks with syntax highlighting.
- **Adaptive Annotations**: Automatically translates Markdown into native Notion rich-text annotations.
