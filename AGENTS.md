# OmniForge agent context policy

For coding agents working on this repository. These rules do not override user
consent or security decisions.

1. **No redundant questions.** Read the current task, repo documentation and
   relevant code before asking. Ask only when a missing decision is truly
   blocking, high-risk, or requires authorization. Do not request information
   the user has already provided. State a reasonable assumption for low-risk
   ambiguity and proceed.
2. **Minimal discovery.** Start with filenames, symbols or targeted searches.
   Open only the narrow code range needed to complete the task. Do not
   recursively dump the repository or repeatedly reread unchanged files.
3. **Conditional reads.** Prefer `omniforge context path/to/code.py --project .`
   for local source excerpts. Record its SHA-256 in the agent's existing
   context. On a later read, pass `--known-sha256 <digest>`; an unchanged
   file returns no body. Use `--start-line`, `--max-lines` and `--max-chars`.
   For skills, `omniforge load SKILL --known-sha256 <digest>` behaves similarly.
4. **Bounded outputs.** Default to at most 100 lines / 6,000 characters per
   local file read. Read more only for a clearly identified reason. Summarize
   decisions and relevant symbols rather than copying entire files into prompts.
5. **No large content cache.** Keep only digest references and short task
   summaries in agent context, not duplicated source bodies or entire skill
   catalogs. Refresh content when hashes change; do not reuse stale content.
6. **Safety.** Never skip explicit permission for writes, deployments,
   secrets, billing or destructive actions. Never send secret-bearing files to
   external models. Check diff and run targeted tests after edits.
7. **Accuracy.** Cached input tokens may be cheaper on a provider; lower cache
   usage is not itself proof of lower cost. Measure actual input, output and
   cached-token billing separately when model usage metadata is available.

This is an agent operating policy, not a technical mechanism that can intercept
file reads made independently by external assistants.
