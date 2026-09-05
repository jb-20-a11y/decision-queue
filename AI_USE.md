# AI use

Complete this file before submission. If a section does not apply, write `None`.

## Tools used

Repeat this section for each AI tool.

### GitHub Copilot (VS Code)

- **Tasks the tool assisted:**
  - Drafted Django REST Framework views for listing/creating queue items (status filtering, primary-key or urgency ordering, page-size-50 pagination) and for updating item status/reason.
  - Drafted a custom `IntegerChoiceField` (labels ↔ stored integers), first on `ItemSerializer`, then—on request—extended the same field to list/create/update serializers so the API consistently uses labels in JSON.
  - Drafted the `expected_impact` integer-choice field on `Item` and migration `0002_item_expected_impact.py`.
  - Drafted and repeatedly revised tests (serializer round-trips, create/update behavior, ordering, filtering, pagination) as the API contract and fixtures evolved.
  - Applied indentation fixes (tabs → four spaces) when asked.
  - Changed `date_created` to `auto_now_add=True` (with migration `0003`), dropped the custom `ItemUpdateSerializer.update()` override so `date_modified` is handled only by the model’s `auto_now=True`, and updated tests to assert created is stable and modified advances.
- Rejected AI update paths that double-saved or manually assigned `date_modified`. After correcting the model (`date_created=auto_now_add`, `date_modified=auto_now`), directed Copilot to drop the custom `update()` override entirely so Django’s field behavior alone advances modified time; confirmed tests assert created unchanged and modified advances.

- **Intermediate artifacts generated through AI use:**
  - Views that initially inlined serializer logic (before serializers lived in `serializers.py`).
  - Mixed choice contract: only `ItemSerializer` used `IntegerChoiceField`; list/create/update still used native integer fields.
- Update implementations that called `save()` twice, then that set `date_modified` manually before `super().update(...)` (later removed entirely once `auto_now` / `auto_now_add` on the model were correct).
  - `date_created` originally `auto_now=True` (advanced on every save); corrected to `auto_now_add=True` plus migration `0003`.
  - Test fixtures/assertions that assumed integer inputs/outputs for create/update while those serializers expected (or later returned) labels—and the reverse during the unification pass.
  - Invalid-status test that indexed `response.data["status"][0]` (DRF returns a plain string for that error).
  - Update test that asserted `date_created` was unchanged (false under `auto_now=True`).
  - Tab-indented `views.py` / `urls.py`.
  - Successive revisions of serializers, tests (including `api_item_payload`), `ItemPagination`, URL routes, and the migration—each built on the previous AI draft rather than written from scratch.

- **Important output checked or changed:**
  - Moved serializers into `serializers.py` myself; directed Copilot only to rewire views and drop redundant defaults.
  - Removed an explicit blank default for `status_reason` myself after confirming the model already allows it.
  - Replaced the AI’s double-`save()` update with a single `instance.date_modified = ...; return super().update(...)` myself; required four-space indentation and rejected tab-indented output.
  - After pasting failing suite output: fixed create/update fixtures when they disagreed with the then-current integer contract; fixed the invalid-status assertion to expect a plain string, not a list; dropped the invalid `date_created`-unchanged assertion.
  - Requested that list/create/update adopt the same label ↔ integer mapping as `ItemSerializer`; reviewed the resulting serializer edits, the new `api_item_payload` helper, and label-based response assertions; confirmed 13/13 green with no view logic changes needed.
  - Verified POST-only update, pagination, urgency ordering, status filtering, and Pending-on-create; re-ran the suite until clean.

### Google Search AI Response

- **Tasks the tool assisted:** [Describe the tasks.]
  - This was web search with the occasional direct Google code snippet output. As part of searching for a built-in Django feature to get the desired serializer behavior (for both read and write) going between integer rank values and strings, Google provided a snippet for a customer class for that behavior.

- **Intermediate artifacts generated through AI use:** [List generated plans, drafts, code, tests, or other artifacts.]

```
class IntegerChoiceField(serializers.IntegerField):
    def __init__(self, choices, *args, **kwargs):
        self.choice_map = {label: val for val, label in choices}
        self.inverse_map = {val: label for val, label in choices}
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        # Convert integer from DB to choice text for reading
        return self.inverse_map.get(value, value)

    def to_internal_value(self, data):
        # Convert choice text from request to integer for writing
        if data in self.choice_map:
            return self.choice_map[data]
        # Fallback if an integer is passed directly
        if data in self.inverse_map:
            return data
        raise serializers.ValidationError("Invalid choice.")
```

- **Important output checked or changed:** [Describe what you reviewed, tested, corrected, rejected, or rewrote.]
  - Removed the fallback to number inputs as that is not part of the intended API contract.

### Grok.com

- **Tasks the tool assisted:**
  - Drafting and refining `AI_USE.md` from exported VS Code chat JSON transcripts; drafting `README.md` / submission checklist wording from the exercise brief and project state.

- **Intermediate artifacts generated through AI use:**
  - Iterative `AI_USE.md` and `README.md` drafts (not application source).

- **Important output checked or changed:**
  - Reviewed and edited all suggested doc text for accuracy (attribution of code changes, env/setup commands, decisions, gaps) before committing.

## Final review

- [x] I understand the important AI-assisted work in this repository.
- [x] I checked or changed important AI output before submission.
- [x] I did not include private or proprietary information in this file.

Do not include full prompt transcripts. They can contain personal, account, private, or proprietary information.
