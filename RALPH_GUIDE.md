# Ralph Wiggum Loop Guide for This Project

## What You Have

This repository contains a **complete specification** for Claude Code to build the university tech transfer scraper autonomously using the Ralph Wiggum loop technique.

### Key Files

1. **PROMPT.md** - The main instruction file for Claude Code's Ralph loop
2. **README.md** - Project overview and documentation
3. **schema.sql** - Complete database schema
4. **requirements.txt** - All Python dependencies
5. **.env.example** - Configuration template
6. **.gitignore** - Standard Python ignore rules

## How to Use with Claude Code

### Step 1: Upload to GitHub

```bash
# Create new repository on GitHub
# Then locally:
git init
git add .
git commit -m "Initial commit: Ralph loop specifications"
git remote add origin <your-repo-url>
git push -u origin main
```

### Step 2: Clone in Claude Code Environment

```bash
# In your terminal where Claude Code is available
git clone <your-repo-url>
cd university-tech-scraper
```

### Step 3: Start the Ralph Loop

The Ralph Wiggum plugin uses the PROMPT.md file by default. Start with Phase 1:

```bash
# Start Ralph loop for Phase 1 (Stanford MVP)
claude -p "/ralph-loop:ralph-loop --max-iterations 30 --completion-promise 'PHASE_COMPLETE'"
```

**Important flags:**
- `--max-iterations 30` - Prevents infinite loops, adjust as needed
- `--completion-promise 'PHASE_COMPLETE'` - Claude will output this when phase is done

### Step 4: Monitor Progress

Claude Code will:
1. Read PROMPT.md Phase 1 requirements
2. Set up the database schema
3. Build the Stanford scraper
4. Create CLI commands
5. Write tests
6. Run tests and verify
7. Output `<promise>PHASE_COMPLETE</promise>` when done

You can monitor in real-time if using tmux:
```bash
# With monitoring
claude -p "/ralph-loop:ralph-loop --max-iterations 30 --monitor --completion-promise 'PHASE_COMPLETE'"
```

### Step 5: Proceed to Next Phases

Once Phase 1 completes:

```bash
# Phase 2: LLM Classification
# Edit PROMPT.md to uncomment Phase 2 or update completion criteria
claude -p "/ralph-loop:ralph-loop --max-iterations 25 --completion-promise 'PHASE_COMPLETE'"

# Phase 3: Multi-university
claude -p "/ralph-loop:ralph-loop --max-iterations 40 --completion-promise 'PHASE_COMPLETE'"

# Phase 4: Production ready
claude -p "/ralph-loop:ralph-loop --max-iterations 20 --completion-promise 'PROJECT_COMPLETE'"
```

## Ralph Loop Best Practices Applied Here

### ✅ Clear Success Criteria
- Each phase has explicit completion criteria
- Verification steps are testable
- Completion promise is clearly defined

### ✅ Verification-First Approach
- Tests are required for each phase
- Tests must pass before marking complete
- Coverage targets specified (>70%)

### ✅ Escape Hatches
- `--max-iterations` prevents runaway loops
- "If Stuck" sections in PROMPT.md guide alternative approaches
- Each phase is independently completable

### ✅ Incremental Building
- Phase 1: Core functionality (Stanford only)
- Phase 2: Add intelligence (classification)
- Phase 3: Scale (more universities)
- Phase 4: Production hardening

### ✅ Deterministic Failures
- Tests provide clear pass/fail
- Database constraints prevent bad data
- Error handling is explicit requirement

## Troubleshooting

### If Ralph Loop Gets Stuck

1. **Check the logs** - Claude Code logs show what it's attempting
2. **Reduce scope** - Lower max-iterations or simplify requirements
3. **Manual intervention** - Fix the blocker, commit, and resume loop
4. **Adjust PROMPT.md** - Add more specific guidance for stuck area

### If Tests Keep Failing

```bash
# Exit the Ralph loop (Ctrl+C)
# Debug manually
pytest tests/ -v --pdb
# Fix the issue
git commit -am "Fix test failures"
# Resume Ralph loop
claude -p "/ralph-loop:ralph-loop --max-iterations 15 --completion-promise 'PHASE_COMPLETE'"
```

### Cost Management

Ralph loops can consume significant API credits:
- Phase 1: Estimate ~$20-40 (30 iterations × database + scraper + tests)
- Phase 2: Estimate ~$15-30 (25 iterations + LLM integration)
- Phase 3: Estimate ~$30-50 (40 iterations × multi-university complexity)
- Phase 4: Estimate ~$10-20 (production hardening)

**Total estimate: $75-140 for complete project**

Set conservative `--max-iterations` to start. You can always resume with more iterations.

## Expected Timeline

With proper Ralph loop:
- **Phase 1**: 2-4 hours (depending on iterations needed)
- **Phase 2**: 1-2 hours
- **Phase 3**: 3-5 hours (most complex - multiple scraper formats)
- **Phase 4**: 1-2 hours

**Total: 7-13 hours of autonomous development**

## Manual Checkpoints

Even with Ralph loop, you should review after each phase:

1. **After Phase 1**: Test the Stanford scraper manually
   ```bash
   python -m src.cli scrape --university stanford
   python -m src.cli search --keyword "robotics"
   ```

2. **After Phase 2**: Verify classification quality
   ```bash
   python -m src.cli classify --batch 10
   # Check database for classification accuracy
   ```

3. **After Phase 3**: Ensure all three universities work
   ```bash
   python -m src.cli scrape --all
   ```

4. **After Phase 4**: Production smoke test
   ```bash
   python -m src.cli schedule --weekly
   # Verify cron job is set up
   ```

## Customization

### Adjust Iteration Limits by Phase

More complex phases may need more iterations:
- Simple phases (Phase 2, 4): 15-25 iterations
- Complex phases (Phase 1, 3): 30-50 iterations

### Modify Completion Criteria

Edit PROMPT.md to:
- Add/remove verification steps
- Change test coverage requirements
- Adjust technical constraints
- Simplify or expand features

### Add New Universities

After Phase 3 completes, add more universities:
1. Add university to `schema.sql` INSERT statement
2. Create new phase in PROMPT.md
3. Run Ralph loop for that phase

## Advanced: Parallel Ralph Loops

Once Phase 1 is complete, you could run multiple loops in parallel:

```bash
# Terminal 1: Classification development
cd university-tech-scraper
claude -p "/ralph-loop:ralph-loop 'Implement Phase 2: LLM Classification' --max-iterations 25"

# Terminal 2: Georgia Tech scraper
cd university-tech-scraper-gatech
claude -p "/ralph-loop:ralph-loop 'Build Georgia Tech scraper matching our schema' --max-iterations 30"
```

This requires careful git coordination but can speed up development.

## Success Indicators

You'll know the Ralph loop is working well when:
- ✅ Tests are passing consistently
- ✅ Code quality improves with each iteration
- ✅ Completion promises are output appropriately
- ✅ Each phase builds on previous successfully
- ✅ Documentation stays updated

## When to Stop and Manual Debug

Stop the Ralph loop if:
- ❌ Same error appears >5 iterations in a row
- ❌ Tests are failing without progress toward fix
- ❌ Cost exceeds your budget
- ❌ Circular behavior (repeating same actions)

Manual debugging is faster for persistent issues.

---

## Quick Reference Commands

```bash
# Standard Ralph loop
claude -p "/ralph-loop:ralph-loop --max-iterations 30 --completion-promise 'PHASE_COMPLETE'"

# With monitoring (tmux session)
claude -p "/ralph-loop:ralph-loop --max-iterations 30 --monitor --completion-promise 'PHASE_COMPLETE'"

# With verbose output
claude -p "/ralph-loop:ralph-loop --max-iterations 30 --verbose --completion-promise 'PHASE_COMPLETE'"

# Custom timeout (60 minutes)
claude -p "/ralph-loop:ralph-loop --max-iterations 30 --timeout 60 --completion-promise 'PHASE_COMPLETE'"
```

Good luck! The Ralph loop should autonomously build your scraper according to the specifications in PROMPT.md.
