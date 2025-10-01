# Result Detection Fix

## Problem
LLM was returning "unknown" for result field because the prompt didn't give enough guidance on how to infer success/failure from video titles and descriptions.

## Solution

### Enhanced Prompt (llm_extractor.py:66-70)

Added explicit result inference guidelines:

```
Result inference:
- result="success" if: "completed", "won", "beat it", "did it", "finished", "demolished"
- result="failure" if: "couldn't", "failed", "DNF", "didn't finish", "too much", "gave up",
                       title says "TRIED TO" or "ATTEMPTING"
- result="unknown" only if truly ambiguous
- IMPORTANT: "TRIED TO" in title usually means FAILURE, "DEMOLISHED" or "COMPLETED" means SUCCESS
```

### BeardMeatsFood Title Patterns

**Success indicators:**
- "I DEMOLISHED..."
- "I COMPLETED..."
- "I BEAT..."
- "I WON..."
- "SUCCESS!" in description

**Failure indicators:**
- "I TRIED TO..." (very common pattern)
- "I ATTEMPTED..."
- "COULDN'T FINISH..."
- "Too much for me" in description

**Ambiguous (truly unknown):**
- Some older videos don't clearly state outcome
- Prototype/test challenges

## Testing

Run the updated test:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key"
python test_llm_extraction.py
```

**Expected results:**
- Video 1 (TRIED TO): `result="failure"`
- Video 2 (completed): `result="success"`
- Video 3 (DEMOLISHED): `result="success"`

## For Real Videos

The LLM will now intelligently infer results from:
1. **Title keywords**: "demolished", "tried to", "completed", "failed"
2. **Description content**: "I finished it!", "couldn't complete", etc.
3. **Context clues**: "first person ever", "added to wall of fame"

Most BeardMeatsFood videos are clear about the outcome, so "unknown" should be rare (<5% of videos).
