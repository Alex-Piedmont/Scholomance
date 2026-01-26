#!/bin/bash
# Ralph Wiggum loop for autonomous development
# Each iteration runs Claude with fresh context

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

  # Small delay between iterations
  sleep 2
done

echo ""
echo "=== MAX ITERATIONS REACHED ==="
echo "Consider running more iterations or debugging manually."
exit 1
