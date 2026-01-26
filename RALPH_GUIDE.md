# Ralph Wiggum Loop Guide for This Project

## What You Have

This repository contains a **complete specification** for Claude Code to build the university tech transfer scraper autonomously using the Ralph Wiggum loop technique.

### Key Files

1. **PROMPT.md** - The main instruction file for Claude Code's Ralph loop
2. **README.md** - Project overview and documentation
3. **schema.sql** - Complete database schema
4. **requirements.txt** - All Python dependencies
5. **pyproject.toml** - Project configuration

## Understanding the Ralph Wiggum Loop

The Ralph Wiggum loop is a bash-based technique for autonomous development with Claude Code. The key insight is that **each iteration runs in a fresh context window**, preventing context bloat and allowing the agent to work on long-running tasks without degradation.

### Core Mechanism

```bash
#!/bin/bash
# ralph.sh - Ralph Wiggum loop runner

MAX_ITERATIONS=${1:-20}

for ((i=1; i<=$MAX_ITERATIONS; i++)); do
  echo "=== Iteration $i of $MAX_ITERATIONS ==="

  result=$(claude -p "$(cat PROMPT.md)" --output-format text 2>&1) || true

  # Check for completion signal
  if [[ "$result" == *"<promise>PHASE_COMPLETE</promise>"* ]]; then
    echo "Phase completed successfully!"
    exit 0
  fi

  if [[ "$result" == *"<promise>PROJECT_COMPLETE</promise>"* ]]; then
    echo "Project completed successfully!"
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
done

echo "Max iterations reached without completion signal."
exit 1
```

### Why Fresh Context Each Iteration?

- **No context bloat**: Previous iteration's reasoning doesn't accumulate
- **Consistent performance**: Each iteration has full context budget
- **State via filesystem**: Progress is tracked through files, commits, and database state
- **Cost predictable**: Each iteration uses similar token counts

## How to Use with Claude Code

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd Scholomance
```

### Step 2: Create the Ralph Loop Script

Save this as `ralph.sh` in the project root:

```bash
#!/bin/bash
# Ralph Wiggum loop for autonomous development

MAX_ITERATIONS=${1:-20}
PROMPT_FILE=${2:-PROMPT.md}

echo "Starting Ralph Wiggum loop"
echo "Max iterations: $MAX_ITERATIONS"
echo "Prompt file: $PROMPT_FILE"
echo "================================"

for ((i=1; i<=$MAX_ITERATIONS; i++)); do
  echo ""
  echo "=== Iteration $i of $MAX_ITERATIONS ==="
  echo "Started at: $(date)"

  # Run Claude with fresh context each time
  result=$(claude -p "$(cat $PROMPT_FILE)" --output-format text 2>&1) || true

  # Log the result summary (last 50 lines)
  echo "$result" | tail -50

  # Check for completion signals
  if [[ "$result" == *"<promise>PHASE_COMPLETE</promise>"* ]]; then
    echo ""
    echo "=== PHASE COMPLETED ==="
    echo "Finished at: $(date)"
    exit 0
  fi

  if [[ "$result" == *"<promise>PROJECT_COMPLETE</promise>"* ]]; then
    echo ""
    echo "=== PROJECT COMPLETED ==="
    echo "Finished at: $(date)"
    exit 0
  fi

  echo "Iteration $i complete at $(date)"

  # Optional: small delay between iterations
  sleep 2
done

echo ""
echo "=== MAX ITERATIONS REACHED ==="
echo "Consider running more iterations or debugging manually."
exit 1
```

Make it executable:
```bash
chmod +x ralph.sh
```

### Step 3: Start the Ralph Loop

```bash
# Run with default 20 iterations
./ralph.sh

# Run with custom iteration count
./ralph.sh 30

# Run with custom prompt file
./ralph.sh 30 PROMPT.md
```

### Step 4: Monitor Progress

The script outputs progress to stdout. For long-running sessions:

```bash
# Run in background with logging
./ralph.sh 30 2>&1 | tee ralph_output.log &

# Monitor the log
tail -f ralph_output.log

# Or use tmux/screen for persistent sessions
tmux new -s ralph
./ralph.sh 30
# Detach with Ctrl+B, D
# Reattach with: tmux attach -t ralph
```

### Step 5: Proceed to Next Phases

Once Phase 1 completes, update PROMPT.md to focus on Phase 2, then run again:

```bash
# Phase 2: LLM Classification
./ralph.sh 25

# Phase 3: Multi-university
./ralph.sh 40

# Phase 4: Production ready
./ralph.sh 20
```

## Ralph Loop Best Practices Applied Here

### Clear Success Criteria
- Each phase has explicit completion criteria in PROMPT.md
- Verification steps are testable
- Completion promise is clearly defined (`<promise>PHASE_COMPLETE</promise>`)

### Verification-First Approach
- Tests are required for each phase
- Tests must pass before marking complete
- Coverage targets specified (>70%)

### Escape Hatches
- Max iterations argument prevents runaway loops
- "If Stuck" sections in PROMPT.md guide alternative approaches
- Each phase is independently completable

### Incremental Building
- Phase 1: Core functionality (Stanford only)
- Phase 2: Add intelligence (classification)
- Phase 3: Scale (more universities)
- Phase 4: Production hardening

### State Persistence via Filesystem
- Code changes are committed to git
- Database stores scraped data
- Test results indicate progress
- Each fresh context reads current state from files

## Troubleshooting

### If Ralph Loop Gets Stuck

1. **Check the output log** - Look for repeated errors or patterns
2. **Reduce scope** - Lower max iterations or simplify requirements in PROMPT.md
3. **Manual intervention** - Fix the blocker, commit, and resume loop
4. **Adjust PROMPT.md** - Add more specific guidance for the stuck area

### If Tests Keep Failing

```bash
# Stop the Ralph loop (Ctrl+C)
# Debug manually
pytest tests/ -v --pdb
# Fix the issue
git commit -am "Fix test failures"
# Resume Ralph loop
./ralph.sh 15
```

### If Same Error Repeats

The fresh context means Claude doesn't remember previous failed attempts. Add guidance to PROMPT.md:

```markdown
### Known Issues
- If you encounter [specific error], the solution is [specific fix]
- Avoid approach X, use approach Y instead
```

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

## Advanced: Enhanced Ralph Script

For more control, use this enhanced version:

```bash
#!/bin/bash
# ralph_enhanced.sh - Enhanced Ralph Wiggum loop

MAX_ITERATIONS=${1:-20}
PROMPT_FILE=${2:-PROMPT.md}
LOG_DIR="ralph_logs"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/ralph_$TIMESTAMP.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting Ralph Wiggum loop"
log "Max iterations: $MAX_ITERATIONS"
log "Prompt file: $PROMPT_FILE"
log "Log file: $LOG_FILE"

for ((i=1; i<=$MAX_ITERATIONS; i++)); do
  log "=== Iteration $i of $MAX_ITERATIONS ==="

  ITER_LOG="$LOG_DIR/iteration_${i}_$TIMESTAMP.log"

  # Run Claude with fresh context
  claude -p "$(cat $PROMPT_FILE)" --output-format text > "$ITER_LOG" 2>&1 || true

  # Check result
  if grep -q "<promise>PHASE_COMPLETE</promise>" "$ITER_LOG"; then
    log "PHASE COMPLETED!"
    exit 0
  fi

  if grep -q "<promise>PROJECT_COMPLETE</promise>" "$ITER_LOG"; then
    log "PROJECT COMPLETED!"
    exit 0
  fi

  # Check for common stuck patterns
  if grep -q "I'm stuck\|cannot proceed\|need clarification" "$ITER_LOG"; then
    log "WARNING: Possible stuck state detected. Review $ITER_LOG"
  fi

  log "Iteration $i complete"
  sleep 2
done

log "Max iterations reached"
exit 1
```

## Success Indicators

You'll know the Ralph loop is working well when:
- Tests are passing consistently
- Code quality improves with each iteration
- Completion promises are output appropriately
- Each phase builds on previous successfully
- Git history shows incremental progress

## When to Stop and Debug Manually

Stop the Ralph loop if:
- Same error appears >5 iterations in a row (check logs)
- Tests are failing without progress toward fix
- Circular behavior (check git log for repeated similar commits)

Manual debugging is faster for persistent issues. Add findings to PROMPT.md to help future iterations.

---

## Quick Reference

```bash
# Basic Ralph loop
./ralph.sh 30

# With custom prompt file
./ralph.sh 30 PROMPT.md

# With logging to file
./ralph.sh 30 2>&1 | tee ralph.log

# In tmux session (recommended for long runs)
tmux new -s ralph './ralph.sh 30'
```

Good luck! The Ralph loop should autonomously build your scraper according to the specifications in PROMPT.md.
