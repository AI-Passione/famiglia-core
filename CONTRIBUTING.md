# Contributing to the Famiglia

Welcome to the **Famiglia Core**. If you are here, it means you have a vision for the future of AI and want to help us build the most elite, autonomous, and beautiful multi-agent ecosystem in the world: **"AI Passione."**

In this house, we value loyalty, precision, and a "Vibe First" approach to coding. Contributing is a path of respect—follow it, and you'll become part of the Core.

## 🤝 The Rule of the House: Talk First

Before you lift a finger to code, we must be in agreement. The Core does not like surprises.

1.  **GitHub Discussions**: If you have a new idea, a "Vision," or just want to discuss a potential feature, start a thread in the [Discussions](https://github.com/AI-Passione/famiglia-core/discussions) tab.
2.  **GitHub Issues**: For bug reports or specific, actionable tasks, please open an [Issue](https://github.com/AI-Passione/famiglia-core/issues). 

**Do not open a Pull Request without an associated Issue or a Discussion that has been blessed by the Core.**

---

## 🛠 How to Contribute

### 1. Reporting Bugs
If something is broken, report it with the respect it deserves.
- Check existing issues to see if the bug has already been reported.
- Provide a clear, concise description of the problem.
- Include steps to reproduce, expected vs. actual behavior, and relevant logs.

### 2. Suggesting Visions (Enhancements)
The Famiglia is always looking for better ways to operate.
- Start a Discussion to pitch your vision. 
- Once the Core approves the direction, an Issue will be created for tracking.

---

## 🚀 The Path of a Pull Request

The Core moves with purpose. To ensure your contribution is accepted, follow this path:

### 1. The Fork
**Mandatory**: You must [fork](https://github.com/AI-Passione/famiglia-core/fork) the repository to your own GitHub account. We do not work directly on the core branches.

### 2. The Branch
Create a branch for your work using the following naming convention:
- `feat/description-of-feature`
- `fix/description-of-fix`
- `docs/description-of-change`

### 3. The Commit
Keep your commits clean and descriptive. One commit per logical change is the way of the Famiglia.

### 4. The Pull Request
Once your work is ready:
- Open a PR from your fork into our `main` branch.
- Link the PR to the relevant Issue (e.g., `Closes #123`).
- Use the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md) provided.

### 5. The Review (The Consigliere)
A member of the Core (a Consigliere) will review your work. Be prepared for feedback. We aim for perfection; if something doesn't "WOW" us, we'll ask for adjustments.

---

## 🚀 Releases & Docker Images

The **Famiglia Core** uses a single-branch approach for all builds and releases.

### 1. Staging (the `main` branch)
- Every merge into `main` automatically triggers a Docker build with the `:staging` tag.

### 2. Production (the `main` branch)
- Production releases are manually triggered from the `main` branch via the **Actions** tab.
- This process uses **Semantic Release** to automate versioning and changelog updates.
- A versioned Docker image (e.g., `:1.2.3`), `:production`, and `:latest` tags are pushed to GHCR.

For more details on the release process and how to trigger it, see [RELEASE.md](RELEASE.md).

---

## 🎨 Development Standards: "AI Passione" Code

To maintain the elite status of the Famiglia, we adhere to strict standards.

### Python Engine
- **Manager**: We use `uv` for package management.
- **Style**: Follow PEP 8. Use `ruff` for linting and formatting.
- **Documentation**: All public functions and classes must have clear, professional docstrings.

### 🌊 Vibe Compliance: The "Silent Concierge" Standards

The Famiglia Core is not just a tool; it is a premium, cinematic experience. All UI contributions must adhere to the **Modern Italian Noir** aesthetic.

*   **Tonal Layering**: Avoid 1px solid borders. Use background color shifts and "stacking" to define boundaries.
*   **Glassmorphism**: Use floating modules with `60%` opacity and `20px` backdrop-blur for agent-specific data.
*   **Typography**: 
    *   **Noto Serif** for high-level storytelling and headers.
    *   **Manrope** for status reports and logs.
    *   **Space Grotesk** for technical metadata and timestamps.
*   **Colors**: Use the Charcoal and Burgundy palette (`#131313`, `#1c1b1b`, `#4c000f`) with Gold (`#eac34a`) accents for high-tech precision.
*   **Micro-Animations**: Every interactive element must have a smooth transition and a hover state that feels responsive and alive.

---

## ⚖️ Code of Conduct

Remember: You are representing the Famiglia. All contributors are bound by our [Code of Conduct](CODE_OF_CONDUCT.md). Respect is non-negotiable.

## 🏆 Joining the Core

Long-term contributors who demonstrate loyalty, skill, and a deep understanding of the "La Passione" vision may be invited to join **The Core** as maintainers. Your work is your currency.

---

Built with ❤️ by **AI Passione.**
