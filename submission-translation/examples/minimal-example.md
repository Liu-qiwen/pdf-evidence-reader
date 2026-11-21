# Minimal invocation example (illustrative only)

This example is synthetic. It is not a source from any fixed platform case and is not a test result.

## Input

Request: Translate the following scientific sentence into Simplified Chinese. Return bilingual alignment and a source locator.

Source file: `synthetic-paper.txt`, section `Example`, paragraph 1, sentence 1.

> The samples were heated to 40 °C for 2 h.

## Invocation

Invoke `scholarly-translation-evidence` with the source text, requested target language, and source locator. In a case run, use the case's actual `case_id` and preserve every required `output_contract` field.

## Illustrative alignment output

```json
{
  "segments": [
    {
      "id": "P0001.S01",
      "source_text": "The samples were heated to 40 °C for 2 h.",
      "target_text": "将样品加热至 40 °C，持续 2 h。",
      "locator": {
        "file": "synthetic-paper.txt",
        "section": "Example",
        "paragraph_id": "P0001",
        "sentence_id": "S01"
      }
    }
  ],
  "glossary": [
    {
      "source_term": "sample",
      "preferred_translation": "样品",
      "context": "experimental specimen",
      "decision": "locked",
      "evidence": "synthetic-paper.txt, Example, P0001.S01"
    }
  ],
  "uncertainties": []
}
```

The example preserves both numeric values and units and links the translation to the synthetic source unit. Real case output must follow that case's contract instead of copying this schema blindly.
